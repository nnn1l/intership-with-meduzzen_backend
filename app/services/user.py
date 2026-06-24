from fastapi import status, HTTPException
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ..logger import logger
from ..models.user import User
from ..repositories.base import add_to_db, delete_from_db, refresh_data_in_db, get_by_filter, get_with_pagination
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

            await add_to_db(new_user, self.db)
            return new_user

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error appeared during creating user {user_data.username}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during user creation")

    # GETTING ALL USERS WITH PAGINATION
    async def get_all_users(self, limit: int=10, offset: int=0) -> List[User]:
        #getting list of users with limit and offset
        users = await get_with_pagination(User, limit, offset, self.db)
        return list(users)

    # GET USER BY ID
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        found_user = await get_by_filter(User, self.db, id=user_id)
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

        await refresh_data_in_db(user)
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

        await delete_from_db(user, self.db)
        logger.info(f"User ID {user_id} deleted successfully")

        return True

    # GET USER BY EMAIL
    async def get_user_by_email(self, email: EmailStr) -> User:
        found_user = await get_by_filter(User, self.db, email=email)

        if not found_user:
            logger.info(f"User with e-mail {email} not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or incorrect e-mail")

        return found_user

