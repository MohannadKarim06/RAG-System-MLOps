import boto3
import uuid
from typing import Dict, List
from io import BytesIO
import PyMuPDF as fitz
from fastapi import UploadFile

from app.config import settings
from app.database import Database
from app.services.embedding_service import EmbeddingService
from app.utils.text_processor import TextProcessor
from app.utils.logger import logger

class FileService:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.embedding_service = EmbeddingService()
        self.text_processor = TextProcessor()
    
    async def process_file(self, file: UploadFile, user_id: str) -> Dict:
        """Process uploaded file: extract text, chunk, embed, and store"""
        
        file_id = str(uuid.uuid4())
        filename = file.filename
        s3_key = f"users/{user_id}/files/{file_id}_{filename}"
        
        # Read file content
        content = await file.read()
        
        # Upload to S3
        self.s3_client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=s3_key,
            Body=content,
            ContentType='application/pdf'
        )
        
        # Extract text from PDF
        text = self._extract_text_from_pdf(content)
        
        # Chunk text
        chunks = self.text_processor.chunk_text(text, file_id, filename)
        
        # Generate embeddings and store in Pinecone
        await self.embedding_service.store_chunks(chunks, user_id)
        
        # Store file record in database
        await Database.add_file_record(file_id, user_id, filename, s3_key, len(chunks))
        
        logger.info(f"Processed file {filename} for user {user_id}: {len(chunks)} chunks")
        
        return {
            "file_id": file_id,
            "filename": filename,
            "chunk_count": len(chunks)
        }
    
    def _extract_text_from_pdf(self, content: bytes) -> str:
        """Extract text from PDF content"""
        text = ""
        with fitz.open(stream=content, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text() + "\n"
        return text
    
    async def list_user_files(self, user_id: str) -> List[Dict]:
        """List all files for a user"""
        return await Database.get_user_files(user_id)
    
    async def delete_file(self, file_id: str, user_id: str):
        """Delete a specific file and its data"""
        # Get file info
        files = await Database.get_user_files(user_id)
        file_info = next((f for f in files if f['id'] == file_id), None)
        
        if not file_info:
            raise ValueError("File not found")
        
        # Delete from S3
        s3_key = f"users/{user_id}/files/{file_id}_{file_info['filename']}"
        try:
            self.s3_client.delete_object(Bucket=settings.S3_BUCKET, Key=s3_key)
        except Exception as e:
            logger.warning(f"Failed to delete S3 object {s3_key}: {e}")
        
        # Delete from Pinecone
        await self.embedding_service.delete_file_chunks(file_id, user_id)
        
        # Delete from database
        await Database.delete_file_record(file_id, user_id)
    
    async def delete_all_user_data(self, user_id: str):
        """Delete all data for a user"""
        # Get all user files
        files = await Database.get_user_files(user_id)
        
        # Delete from S3
        try:
            objects = [{'Key': f"users/{user_id}/files/{f['id']}_{f['filename']}"} for f in files]
            if objects:
                self.s3_client.delete_objects(
                    Bucket=settings.S3_BUCKET,
                    Delete={'Objects': objects}
                )
        except Exception as e:
            logger.warning(f"Failed to delete S3 objects for user {user_id}: {e}")
        
        # Delete from Pinecone
        await self.embedding_service.delete_all_user_chunks(user_id)
        
        # Delete from database
        await Database.delete_all_user_files(user_id)
