from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_auth0_token
from app.database import init_db
from app.services.user import UserService
from ..models.user import User


async def get_user_service(db: AsyncSession = Depends(init_db)) -> UserService:
    return UserService(db)

async def get_current_user(payload: dict = Depends(verify_auth0_token), service: UserService = Depends(get_user_service)) -> User:
    email = payload.get('email')

    if not email:
        email = f'{payload.get("sub")}@auth0.io'

    user = await service.get_or_create_auth0_user(email=email)
    return user
