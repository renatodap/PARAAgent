import redis.asyncio as aioredis
from typing import Optional, Any
import json
from datetime import timedelta
from config import settings

class RedisCache:
    def __init__(self):
        self.client: Optional[aioredis.Redis] = None

    async def connect(self):
        """Connect to Redis"""
        self.client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.client:
            await self.client.close()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.client:
            return None

        value = await self.client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[timedelta] = None
    ) -> bool:
        """Set value in cache"""
        if not self.client:
            return False

        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        if expire:
            await self.client.setex(key, int(expire.total_seconds()), value)
        else:
            await self.client.set(key, value)

        return True

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.client:
            return False

        await self.client.delete(key)
        return True

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.client:
            return False

        return await self.client.exists(key) > 0

    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern"""
        if not self.client:
            return

        keys = []
        async for key in self.client.scan_iter(match=pattern):
            keys.append(key)

        if keys:
            await self.client.delete(*keys)

# Global instance
cache = RedisCache()

# Cache key generators
class CacheKeys:
    @staticmethod
    def user_items(user_id: str, para_type: Optional[str] = None) -> str:
        if para_type:
            return f"user:{user_id}:items:{para_type}"
        return f"user:{user_id}:items:*"

    @staticmethod
    def user_tasks(user_id: str) -> str:
        return f"user:{user_id}:tasks"

    @staticmethod
    def user_reviews(user_id: str) -> str:
        return f"user:{user_id}:reviews"

    @staticmethod
    def classification(item_id: str) -> str:
        return f"classification:{item_id}"

    @staticmethod
    def schedule(user_id: str, date: str) -> str:
        return f"schedule:{user_id}:{date}"

# Cache durations
class CacheDuration:
    SHORT = timedelta(minutes=5)
    MEDIUM = timedelta(minutes=15)
    LONG = timedelta(hours=1)
    DAY = timedelta(days=1)
