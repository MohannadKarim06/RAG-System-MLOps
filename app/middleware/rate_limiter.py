import redis
import time
from typing import Dict

from app.config import settings
from app.utils.logger import logger

class RateLimiter:
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
    
    async def check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """
        Check if request is within rate limit
        key: unique identifier for the rate limit
        limit: number of requests allowed
        window: time window in seconds
        """
        try:
            current_time = int(time.time())
            pipe = self.redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, current_time - window)
            
            # Count current entries
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiry
            pipe.expire(key, window)
            
            results = pipe.execute()
            request_count = results[1]
            
            return request_count < limit
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True  # Allow request if Redis fails
