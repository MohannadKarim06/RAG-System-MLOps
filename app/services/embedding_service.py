import pinecone
from typing import List, Dict, Tuple
import boto3
import json

from app.config import settings
from app.utils.logger import logger

class EmbeddingService:
    def __init__(self):
        # Initialize Pinecone
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index = pc.Index(settings.PINECONE_INDEX_NAME)
        
        # Initialize Bedrock for embeddings
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using AWS Bedrock Titan"""
        try:
            response = self.bedrock_client.invoke_model(
                modelId="amazon.titan-embed-text-v1",
                body=json.dumps({"inputText": text})
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['embedding']
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise e
    
    async def store_chunks(self, chunks: List[Dict], user_id: str):
        """Store document chunks in Pinecone"""
        vectors = []
        
        for chunk in chunks:
            # Generate embedding
            embedding = self._generate_embedding(chunk['content'])
            
            # Create vector with metadata
            vector = {
                'id': f"{user_id}_{chunk['id']}",
                'values': embedding,
                'metadata': {
                    'user_id': user_id,
                    'file_id': chunk['file_id'],
                    'filename': chunk['filename'],
                    'content': chunk['content'][:1000],  # Truncate for metadata
                    'full_content': chunk['content']
                }
            }
            vectors.append(vector)
        
        # Batch upsert to Pinecone
        self.index.upsert(vectors)
        logger.info(f"Stored {len(vectors)} vectors for user {user_id}")
    
    async def search_similar_chunks(self, query: str, user_id: str, top_k: int = None) -> List[Dict]:
        """Search for similar chunks for a specific user"""
        if top_k is None:
            top_k = settings.MAX_CHUNKS_PER_QUERY
        
        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        
        # Search in Pinecone with user filter
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter={'user_id': user_id}
        )
        
        chunks = []
        for match in results['matches']:
            chunks.append({
                'content': match['metadata']['full_content'],
                'filename': match['metadata']['filename'],
                'score': match['score']
            })
        
        logger.info(f"Found {len(chunks)} similar chunks for user {user_id}")
        return chunks
    
    async def delete_file_chunks(self, file_id: str, user_id: str):
        """Delete all chunks for a specific file"""
        # Query to get all vector IDs for this file
        results = self.index.query(
            vector=[0.0] * 1536,  # Dummy vector
            top_k=10000,  # Large number to get all
            include_metadata=True,
            filter={'user_id': user_id, 'file_id': file_id}
        )
        
        vector_ids = [match['id'] for match in results['matches']]
        
        if vector_ids:
            self.index.delete(ids=vector_ids)
            logger.info(f"Deleted {len(vector_ids)} vectors for file {file_id}")
    
    async def delete_all_user_chunks(self, user_id: str):
        """Delete all chunks for a user"""
        self.index.delete(filter={'user_id': user_id})
        logger.info(f"Deleted all vectors for user {user_id}")
