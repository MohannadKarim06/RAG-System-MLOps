import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:password@postgres:5432/ragdb"
    
    # AWS
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"
    S3_BUCKET: str
    
    # Pinecone
    PINECONE_API_KEY: str
    PINECONE_ENVIRONMENT: str
    PINECONE_INDEX_NAME: str = "rag-documents"
    
    # LLM (AWS Bedrock)
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379"
    REDIS_TTL: int = 3600
    
    # File processing
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_CHUNKS_PER_QUERY: int = 5
    
    # Query limits
    MAX_QUERY_LENGTH: int = 1000
    MAX_RESPONSE_LENGTH: int = 4000
    MAX_SYSTEM_PROMPT_LENGTH: int = 2000
    
    # Rate limiting
    UPLOAD_RATE_LIMIT: int = 5  # per hour
    QUERY_RATE_LIMIT: int = 100  # per hour
    
    # Default prompts
    DEFAULT_SYSTEM_PROMPT: str = "You are a helpful assistant that answers questions based on the provided documents. Be concise and accurate."
    
    # Streamlit
    STREAMLIT_SECRET_KEY: str
    
    class Config:
        env_file = ".env"

settings = Settings()