from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import init_db
from app.services.user import UserService


async def get_user_service(db: AsyncSession = Depends(init_db())) -> UserService:
    return UserService(db)
