from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
import time
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.database import Database, User
from app.services.file_service import FileService
from app.services.rag_service import RAGService
from app.utils.logger import logger
from app.utils.exceptions import UserNotFoundException

# Initialize services
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await Database.initialize()
    yield
    # Shutdown
    await Database.close()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="RAG Document QA API",
    description="Document upload and question answering with RAG",
    version="1.0.0",
    lifespan=lifespan
)

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Services
file_service = FileService()
rag_service = RAGService()

# Models
class QueryRequest(BaseModel):
    question: str

class ConfigUpdateRequest(BaseModel):
    system_prompt: Optional[str] = None

class UserResponse(BaseModel):
    user_id: str
    api_key: str
    created_at: datetime
    file_count: int

# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    api_key = credentials.credentials
    user = await Database.get_user_by_api_key(api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user

# Routes
@app.post("/users", response_model=UserResponse)
async def create_user():
    """Create a new user and return API key"""
    user_id = str(uuid.uuid4())
    api_key = str(uuid.uuid4())
    
    user = await Database.create_user(user_id, api_key)
    
    return UserResponse(
        user_id=user.id,
        api_key=user.api_key,
        created_at=user.created_at,
        file_count=0
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0"
    }

@app.post("/upload")
@limiter.limit("5/hour")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user)
):
    """Upload and process a document"""
    
    # Validate file
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    await file.seek(0)  # Reset file pointer    
    
    try:
        # Process file
        result = await file_service.process_file(file, user.id)
        
        # Update user file count
        await Database.increment_user_file_count(user.id)
        
        logger.info(f"File uploaded successfully for user {user.id}: {result['filename']}")
        
        return {
            "message": "File uploaded and processed successfully",
            "filename": result['filename'],
            "chunk_count": result['chunk_count'],
            "file_id": result['file_id']
        }
        
    except Exception as e:
        logger.error(f"Upload failed for user {user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/ask")
@limiter.limit("100/hour")
async def ask_question(
    request: Request,
    request_body: QueryRequest,
    user: User = Depends(get_current_user)
):
    """Ask a question about uploaded documents"""
    
    if len(request_body.question) > settings.MAX_QUERY_LENGTH:
        raise HTTPException(status_code=400, detail="Query too long")
    
    try:
        # Get user's system prompt
        config = await Database.get_user_config(user.id)
        system_prompt = config.get('system_prompt', settings.DEFAULT_SYSTEM_PROMPT)
        
        # Generate response
        response = await rag_service.generate_response(
            question=request_body.question,
            user_id=user.id,
            system_prompt=system_prompt
        )
        
        logger.info(f"Question answered for user {user.id}")
        
        return {
            "answer": response['answer'],
            "sources": response['sources'],
            "chunk_count": response['chunk_count']
        }
        
    except Exception as e:
        logger.error(f"Query failed for user {user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/files")
async def list_files(user: User = Depends(get_current_user)):
    """List user's uploaded files"""
    try:
        files = await file_service.list_user_files(user.id)
        return {"files": files}
    except Exception as e:
        logger.error(f"Failed to list files for user {user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list files")

@app.delete("/files/{file_id}")
async def delete_file(file_id: str, user: User = Depends(get_current_user)):
    """Delete a specific file and its data"""
    try:
        await file_service.delete_file(file_id, user.id)
        await Database.decrement_user_file_count(user.id)
        
        logger.info(f"File deleted successfully for user {user.id}: {file_id}")
        return {"message": "File deleted successfully"}
        
    except Exception as e:
        logger.error(f"Failed to delete file for user {user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete file")

@app.delete("/user/data")
async def delete_all_user_data(user: User = Depends(get_current_user)):
    """Delete all user data"""
    try:
        await file_service.delete_all_user_data(user.id)
        await Database.reset_user_file_count(user.id)
        
        logger.info(f"All data deleted for user {user.id}")
        return {"message": "All user data deleted successfully"}
        
    except Exception as e:
        logger.error(f"Failed to delete user data {user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete user data")

@app.get("/config")
async def get_config(user: User = Depends(get_current_user)):
    """Get user configuration"""
    config = await Database.get_user_config(user.id)
    return config

@app.put("/config")
async def update_config(
    request: ConfigUpdateRequest,
    user: User = Depends(get_current_user)
):
    """Update user configuration"""
    try:
        updates = {}
        if request.system_prompt is not None:
            if len(request.system_prompt) > settings.MAX_SYSTEM_PROMPT_LENGTH:
                raise HTTPException(status_code=400, detail="System prompt too long")
            updates['system_prompt'] = request.system_prompt
        
        if updates:
            await Database.update_user_config(user.id, updates)
        
        logger.info(f"Config updated for user {user.id}")
        return {"message": "Configuration updated successfully"}
        
    except Exception as e:
        logger.error(f"Failed to update config for user {user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update configuration")

# Exception handlers
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    response = JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": f"Rate limit exceeded: {exc.detail}"}
    )
    response = request.app.state.limiter._inject_headers(
        response, request.state.view_rate_limit
    )
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)