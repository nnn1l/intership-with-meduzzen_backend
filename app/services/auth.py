from datetime import datetime, timezone, timedelta

import bcrypt
from fastapi.params import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from fastapi import HTTPException, status

from ..logger import logger
from ..schemas.config import settings
from ..models.user import User

class AuthService:
    def __init__(self,db_session: AsyncSession):
        self.db = db_session

    @staticmethod
    async def hash_password(password: str):
        password_byte = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_byte, salt)
        return hashed.decode('utf-8')

    @staticmethod
    async def verify_password(plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )

    @staticmethod
    async def create_access_token(data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})

        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    # GET USER BY TOKEN
    async def get_current_user_by_token(self, token: str) -> User:
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )

            email: str = payload.get("email")

            if not email:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )

            from .user import UserService
            user_service = UserService(self.db)
            return await user_service.get_user_by_email(email)

        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )


    async def get_or_create_auth0_user(self, email: str) -> User:
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            generated_username = email.split("@")[0]

            user = User(
                username=generated_username,
                email=email,
                hashed_password="auth0_external_user"
            )
            try:
                self.db.add(user)
                await self.db.commit()
                await self.db.refresh(user)

                logger.info(f"Dynamically created new Auth0 user: {email}")
            except Exception as e:
                logger.info(f'Error during dynamic user creation: {str(e)}')
                raise HTTPException( status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
        return user