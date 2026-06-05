import jwt
from fastapi import status, HTTPException
from pydantic import EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Tuple, List, Optional

from ..logger import logger
from ..models.user import User
from ..schemas.config import settings
from ..schemas.user import UserSignUp, UserUpdate
from ..utils.security import hash_password

class UserService:
    def __init__(self,db_session: AsyncSession):
        self.db = db_session

    # NEW USER REGISTRATION WITH HASHING
    async def create_user(self, user_data: UserSignUp):
        hashed_password = hash_password(user_data.password)

        try:
            new_user = User(
                username = user_data.username,
                email = user_data.email,
                hashed_password=hashed_password
            )

            self.db.add(new_user)
            await  self.db.commit()
            await self.db.refresh(new_user)

            return new_user
        except Exception as e:
            logger.error(f"Error appeared during creating user {user_data.username}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during user creation")

    # GETTING ALL USERS WITH PAGINATION
    async def get_all_users(self, limit: int=10, offset: int=0) -> Tuple[List[User],int]:
        #getting list of users with limit and offset
        query = select(User).limit(limit).offset(offset)
        result = await self.db.execute(query)
        users = result.scalars().all()

        #counting amount for full response schema
        count_query = select(func.count()).select_from(User)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return list(users), total

    # GET USER BY ID
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        query = select(User).where(User.id == user_id)
        found_user = await self.db.execute(query)
        if not found_user:
            logger.info(f"User with ID {user_id} not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return found_user.scalar_one_or_none()

    # UPDATE USER
    async def user_update(self, user_id: int, update_data: UserUpdate) -> User:
        user = await self.get_user_by_id(user_id)

        if not user:
            logger.info(f"Updating isn't completed: user wasn't found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        data_to_update = update_data.model_dump(exclude_unset=True)
        for key, value in data_to_update.items():
            setattr(user, key, value)

        await self.db.commit()
        await self.db.refresh(user)

        return user

    # USER DELETION
    async def delete_user(self, user_id: int) -> bool:
        user = await self.get_user_by_id(user_id)
        if not user:
            logger.info(f"Deletion isn't completed: user wasn't found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
                )

        await self.db.delete(user)
        await self.db.commit()

        return True

    # GET USER BY EMAIL
    async def get_user_by_email(self, user_email: EmailStr) -> User:
        query = select(User).where(User.email == user_email)
        result = await self.db.execute(query)
        found_user = result.scalar_one_or_none()

        if not found_user:
            logger.info(f"User with e-mail {user_email} not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or incorrect e-mail")

        return found_user

    # GET USER BY TOKEN
    async def get_current_user_by_token(self, token: str) -> User:
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )

            email: str | None = payload.get("email")

            if email is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )

        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        return await self.get_user_by_email(email)


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