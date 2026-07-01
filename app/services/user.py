from fastapi import status, HTTPException
from pydantic import EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Tuple, List, Optional

from ..logger import logger
from ..models.user import User
from ..schemas.user import UserSignUp, UserUpdate


class UserService:
    def __init__(self,db_session: AsyncSession):
        self.db = db_session

    # NEW USER REGISTRATION WITH HASHING
    async def create_user(self, user_data: UserSignUp):
        from .auth import AuthService
        hashed_password = AuthService.hash_password(user_data.password)

        try:
            logger.info(f"Attempting to create user with username: {user_data.username}")
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
            await self.db.rollback()
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
        result = await self.db.execute(query)
        found_user = result.scalar_one_or_none()
        if not found_user:
            logger.info(f"User with ID {user_id} not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return found_user

    # UPDATE USER
    async def user_update(self, user_id: int, update_data: UserUpdate) -> User:
        logger.info(f"Modifying database: updating user ID {user_id}")
        user = await self.get_user_by_id(user_id)

        if not user:
            logger.info(f"Updating isn't completed: user wasn't found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        allowed_fields = {'name', 'password', 'description'}
        data_to_update = update_data.model_dump(exclude_unset=True)
        filtered_data = {k: v for k, v in data_to_update.items() if k in allowed_fields}
        for key, value in filtered_data.items():
            setattr(user, key, value)

        await self.db.commit()
        await self.db.refresh(user)
        logger.info(f"User ID {user_id} modified successfully")

        return user

    # USER DELETION
    async def delete_user(self, user_id: int) -> bool:
        logger.info(f"Modifying database: deleting user ID {user_id}")
        user = await self.get_user_by_id(user_id)
        if not user:
            logger.info(f"Deletion isn't completed: user wasn't found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
                )

        await self.db.delete(user)
        await self.db.commit()
        logger.info(f"User ID {user_id} deleted successfully")

        return True

    # GET USER BY EMAIL
    async def get_user_by_email(self, email: EmailStr) -> User:
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        found_user = result.scalar_one_or_none()

        if not found_user:
            logger.info(f"User with e-mail {email} not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or incorrect e-mail")

        return found_user

