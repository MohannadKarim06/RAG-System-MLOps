import boto3
import json
from typing import Dict, List
import redis

from app.config import settings
from app.services.embedding_service import EmbeddingService
from app.utils.logger import logger

class RAGService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.redis_client = redis.from_url(settings.REDIS_URL)
    
    async def generate_response(self, question: str, user_id: str, system_prompt: str) -> Dict:
        """Generate response using RAG"""
        
        # Check cache first
        cache_key = f"rag:{user_id}:{hash(question + system_prompt)}"
        cached_response = self.redis_client.get(cache_key)
        
        if cached_response:
            logger.info(f"Cache hit for user {user_id}")
            return json.loads(cached_response)
        
        # Search for relevant chunks
        similar_chunks = await self.embedding_service.search_similar_chunks(
            query=question,
            user_id=user_id,
            top_k=settings.MAX_CHUNKS_PER_QUERY
        )
        
        if not similar_chunks:
            response_data = {
                "answer": "I don't have any relevant documents to answer your question. Please upload some documents first.",
                "sources": [],
                "chunk_count": 0
            }
            return response_data
        
        # Prepare context from chunks
        context = "\n\n".join([
            f"Source: {chunk['filename']}\nContent: {chunk['content']}"
            for chunk in similar_chunks
        ])
        
        # Prepare prompt
        full_prompt = f"""{system_prompt}

Context from uploaded documents:
{context}

Question: {question}

Please provide a comprehensive answer based on the context above. If the context doesn't contain enough information to answer the question, say so clearly."""
        
        # Generate response using Claude
        try:
            response = self._call_bedrock_claude(full_prompt)
            
            response_data = {
                "answer": response,
                "sources": [{"filename": chunk['filename'], "score": chunk['score']} for chunk in similar_chunks],
                "chunk_count": len(similar_chunks)
            }
            
            # Cache the response
            self.redis_client.setex(
                cache_key,
                settings.REDIS_TTL,
                json.dumps(response_data)
            )
            
            return response_data
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise e
    
    def _call_bedrock_claude(self, prompt: str) -> str:
        """Call Claude via AWS Bedrock"""
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": settings.MAX_RESPONSE_LENGTH,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=settings.BEDROCK_MODEL_ID,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            logger.error(f"Bedrock API call failed: {e}")
            raise e
