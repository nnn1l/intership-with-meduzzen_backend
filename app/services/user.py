from fastapi import status, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Tuple, List, Optional

from ..logger import logger
from ..models.user import User
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
