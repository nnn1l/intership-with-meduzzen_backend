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

@router.get('/signup_log')
async def signup_log(user_data: UserSignUp):
    try:
        logger.info(f'User {user_data.username} succesfully registered')

    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        raise