from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Tuple, List, Optional

from ..models.user import User
from ..schemas.user import UserSignUp, UserUpdate
from ..utils.security import hash_password

class UserService:
    def __init__(self,db_session: AsyncSession):
        self.db = db_session

    # NEW USER REGISTRATION WITH HASHING
    async def create_user(self, user_data: UserSignUp):
        hashed_password = hash_password(user_data.password)

        new_user = User(
            username = user_data.username,
            email = user_data.email,
            hashed_password=hashed_password
        )

        self.db.add(new_user)
        await  self.db.commit()
        await self.db.refresh(new_user)
        return new_user

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

        return result.scalar_one_or_none()

    # UPDATE USER
    async def user_update(self, user_id: int, update_data: UserUpdate) -> Optional[User]:
        user = await self.get_user_by_id(user_id)

        if not user:
            return None
        else:
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
            return False

        await self.db.delete(user)
        await self.db.commit()
        return True
