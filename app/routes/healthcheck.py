from fastapi import APIRouter, status
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as async_redis
from app.database import init_db
from app.redis_client import get_redis
from sqlalchemy import text
router = APIRouter()

@router.get('/')
async def healthcheck(db: AsyncSession = Depends(init_db),
                      redis_cl: async_redis.Redis = Depends(get_redis)):
    db_result = await db.execute(text("SELECT 1"))
    db_status = "conneted" if db_result.scalar() == 1 else "error"
    redis_pings = await redis_cl.incr("healthcheck_pings")
    return {
        "status_code": status.HTTP_200_OK,
        "detail": "ok",
        "result": "working",
        "db_postgres": db_status,
        "redis_pings_count": redis_pings
        }