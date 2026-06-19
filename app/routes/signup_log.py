from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as async_redis
from app.database import init_db
from app.redis_client import get_redis
from sqlalchemy import text
from ..logger import logger
from app.schemas.user import UserSignUp

router = APIRouter()

@router.post("/signup_log")
async def signup_log(user_data: UserSignUp):
    logger.info(
        f"User {user_data.username} successfully registered"
    )

    return {"message": "Log created"}