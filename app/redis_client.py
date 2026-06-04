import redis.asyncio as async_redis
from app.schemas.config import settings

redis_pool = async_redis.ConnectionPool(
    host = settings.REDIS_HOST,
    port = settings.REDIS_PORT,
    decode_responses=True #bytes -> str
)

async def get_redis():
    async with async_redis.Redis(connection_pool=redis_pool) as client:
        yield client