import asyncpg
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

from app.config import settings
from app.utils.logger import logger

@dataclass
class User:
    id: str
    api_key: str
    created_at: datetime
    file_count: int = 0
    config: Dict = None

class Database:
    _pool = None
    
    @classmethod
    async def initialize(cls):
        cls._pool = await asyncpg.create_pool(settings.DATABASE_URL)
        await cls._create_tables()
        logger.info("Database initialized")
    
    @classmethod
    async def close(cls):
        if cls._pool:
            await cls._pool.close()
    
    @classmethod
    async def _create_tables(cls):
        async with cls._pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR PRIMARY KEY,
                    api_key VARCHAR UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    file_count INTEGER DEFAULT 0,
                    config JSONB DEFAULT '{}'
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id VARCHAR PRIMARY KEY,
                    user_id VARCHAR REFERENCES users(id),
                    filename VARCHAR NOT NULL,
                    s3_key VARCHAR NOT NULL,
                    chunk_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);
                CREATE INDEX IF NOT EXISTS idx_files_user_id ON files(user_id);
            ''')
    
    @classmethod
    async def create_user(cls, user_id: str, api_key: str) -> User:
        async with cls._pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO users (id, api_key, config)
                VALUES ($1, $2, $3)
            ''', user_id, api_key, json.dumps({"system_prompt": settings.DEFAULT_SYSTEM_PROMPT}))
            
            return User(
                id=user_id,
                api_key=api_key,
                created_at=datetime.utcnow(),
                config={"system_prompt": settings.DEFAULT_SYSTEM_PROMPT}
            )
    
    @classmethod
    async def get_user_by_api_key(cls, api_key: str) -> Optional[User]:
        async with cls._pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT id, api_key, created_at, file_count, config
                FROM users WHERE api_key = $1
            ''', api_key)
            
            if row:
                return User(
                    id=row['id'],
                    api_key=row['api_key'],
                    created_at=row['created_at'],
                    file_count=row['file_count'],
                    config=row['config']
                )
            return None
    
    @classmethod
    async def get_user_config(cls, user_id: str) -> Dict:
        async with cls._pool.acquire() as conn:
            row = await conn.fetchrow('SELECT config FROM users WHERE id = $1', user_id)
            return row['config'] if row else {}
    
    @classmethod
    async def update_user_config(cls, user_id: str, updates: Dict):
        async with cls._pool.acquire() as conn:
            current_config = await cls.get_user_config(user_id)
            current_config.update(updates)
            
            await conn.execute('''
                UPDATE users SET config = $1 WHERE id = $2
            ''', json.dumps(current_config), user_id)
    
    @classmethod
    async def increment_user_file_count(cls, user_id: str):
        async with cls._pool.acquire() as conn:
            await conn.execute('''
                UPDATE users SET file_count = file_count + 1 WHERE id = $1
            ''', user_id)
    
    @classmethod
    async def decrement_user_file_count(cls, user_id: str):
        async with cls._pool.acquire() as conn:
            await conn.execute('''
                UPDATE users SET file_count = GREATEST(file_count - 1, 0) WHERE id = $1
            ''', user_id)
    
    @classmethod
    async def reset_user_file_count(cls, user_id: str):
        async with cls._pool.acquire() as conn:
            await conn.execute('''
                UPDATE users SET file_count = 0 WHERE id = $1
            ''', user_id)
    
    @classmethod
    async def add_file_record(cls, file_id: str, user_id: str, filename: str, s3_key: str, chunk_count: int):
        async with cls._pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO files (id, user_id, filename, s3_key, chunk_count)
                VALUES ($1, $2, $3, $4, $5)
            ''', file_id, user_id, filename, s3_key, chunk_count)
    
    @classmethod
    async def get_user_files(cls, user_id: str) -> List[Dict]:
        async with cls._pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT id, filename, chunk_count, created_at
                FROM files WHERE user_id = $1
                ORDER BY created_at DESC
            ''', user_id)
            
            return [dict(row) for row in rows]
    
    @classmethod
    async def delete_file_record(cls, file_id: str, user_id: str):
        async with cls._pool.acquire() as conn:
            await conn.execute('''
                DELETE FROM files WHERE id = $1 AND user_id = $2
            ''', file_id, user_id)
    
    @classmethod
    async def delete_all_user_files(cls, user_id: str):
        async with cls._pool.acquire() as conn:
            await conn.execute('DELETE FROM files WHERE user_id = $1', user_id)