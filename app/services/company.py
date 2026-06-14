from typing import List, TYPE_CHECKING

from sqlalchemy import select, and_, delete, update
from ..models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from ..models.company import Company, company_members
from ..schemas.company import CompanyCreate, CompanyUpdate
from ..logger import logger
from ..utils.enums import VisibilityStatus

if TYPE_CHECKING:
    from .user import UserService

class CompanyService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session


    # CREATE COMPANY
    async def create_company(self, company_data: CompanyCreate, owner_id: int) -> Company:
        logger.info(f"Attempting to create a company with name {company_data.name}")
        try:
            company = Company(
                name = company_data.name,
                description = company_data.description,
                visibility = company_data.visibility,
                owner_id = owner_id
            )
        except Exception as e:
            logger.error('Error appeared during creating a company')
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error during user creation: {str(e)}")

        self.db.add(company)
        await self.db.commit()
        await self.db.refresh(company)
        return company


    # GET COMPANY BY ID
    async def get_company_by_id(self, company_id: int) -> Company:
        query = select(Company).where(Company.id == company_id)
        result = await self.db.execute(query)
        company = result.scalar_one_or_none()

        if not company:
            logger.error(f"Company with ID {company_id} wasn't found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company with this ID doesn't exist")

        return company


    async def get_companies(self, limit: int, offset: int) -> List[Company]:
        query = (select(Company)
                .where(Company.visibility == VisibilityStatus.VISIBLE_TO_ALL)
                .limit(limit)
                .offset(offset))

        result = await self.db.execute(query)
        return list(result.scalars().all())


    # UPDATE COMPANY
    async def update_company(self, company_id: int, company_data: CompanyUpdate, user_id: int) -> Company:
        company = await self.get_company_by_id(company_id)
        if company.owner_id != user_id:
             raise HTTPException(
                 status_code=status.HTTP_403_FORBIDDEN,
                 detail="You don't have permission to modify this company"
             )

        logger.info(f"Modifying company {company_data.name}")
        update_data = company_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(company, key, value)

        await self.db.commit()
        await self.db.refresh(company)
        logger.info(f"Company {company_data.name} successfully modified")
        return company


    # DELETE COMPANY
    async def delete_company(self, company_id: int, user_id: int) -> bool:
        company = await self.get_company_by_id(company_id)

        if company.owner_id != user_id:
             raise HTTPException(
                 status_code=status.HTTP_403_FORBIDDEN,
                 detail="You don't have permission to delete this company"
             )

        await self.db.delete(company)
        await self.db.commit()
        logger.info(f"Company ID {company_id} deleted successfully")
        return True


    # CHANGE COMPANY VISIBILITY
    async def change_company_visibility(self, company_id: int, user_id: int) -> bool:
        company = await self.get_company_by_id(company_id)

        if company.owner_id != user_id:
             raise HTTPException(
                 status_code=status.HTTP_403_FORBIDDEN,
                 detail="You don't have permission to modify this company"
             )

        if company.visibility == VisibilityStatus.VISIBLE_TO_ALL:
            company.visibility = VisibilityStatus.HIDDEN
        else:
            company.visibility = VisibilityStatus.VISIBLE_TO_ALL

        return True


    # FIRE USER FROM COMPANY
    async def fire_user_from_company(self, company_id: int, fired_user_id: int, current_user: User) -> bool:

        if fired_user_id == current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't fire yourself")

        company = await self.get_company_by_id(company_id)

        if company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You don't have permissions to fire user from this company")

        user_search = select(company_members.c.user_id).where(
            and_(
                company_members.c.company_id == company_id,
                company_members.c.user_id == fired_user_id))
        user_presence = await self.db.execute(user_search)

        if not user_presence.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="This user isn't in this company")

        fire = delete(company_members).where(
            and_(
                company_members.c.company_id == company_id,
                company_members.c.user_id == fired_user_id))

        await self.db.execute(fire)
        await self.db.commit()
        logger.info(f"User with ID {fired_user_id} fired from company with ID {company_id}")
        return True


    # LEAVE COMPANY
    async def leave_company(self, company_id: int, current_user: User) -> bool:
        company = await self.get_company_by_id(company_id)

        if company.owner_id == current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You can't leave from your own company")

        user_search = select(company_members.c.user_id).where(
            and_(
                company_members.c.company_id == company_id,
                company_members.c.user_id == current_user.id))
        user_presence = await self.db.execute(user_search)

        if not user_presence.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You're not in this company to have ability to leave")

        leave = delete(company_members).where(
            and_(
                company_members.c.company_id == company_id,
                company_members.c.user_id == current_user.id))
        await self.db.execute(leave)
        await self.db.commit()
        logger.info(f"User with ID {current_user.id} left a company with ID {company_id}")
        return True


    # GET COMPANY'S MEMBERS
    async def get_company_members(self, company_id: int, limit: int, offset: int):
        await self.get_company_by_id(company_id)

        members = (select(User).join(company_members, User.id == company_members.c.user_id)
            .where(company_members.c.company_id == company_id)
            .limit(limit)
            .offset(offset))

        result = await self.db.execute(members)
        return result.scalars().all()


    # APPOINT ADMIN
    async def appoint_admin(self, company_id: int, user_id: int, current_user: User) -> User:
        if user_id == current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't appoint yourself as an admin")

        company = await self.get_company_by_id(company_id) # ensures that company exists & gets company

        if company.owner_id != current_user.id:
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                 detail="You don't have permissions to appoint admins in this company")

        user_service = UserService(self.db)
        user = await user_service.get_user_by_id(user_id) # ensures that user exists & gets user

        user_search = select(company_members).where(
            and_(
                company_members.c.company_id == company_id,
                company_members.c.user_id == user_id))
        user_presence = await self.db.execute(user_search)
        member = user_presence.mappings().first()

        if not member:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't appoint user as an admin if user isn't a member of company")

        if member['is_admin']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't appoint user as an admin twice")

        update_user = update(company_members).where(
            and_(
                company_members.c.company_id == company_id,
                company_members.c.user_id == user_id)).values(is_admin=True)
        await self.db.execute(update_user)
        await self.db.commit()
        return user


    # FIRE FROM ADMIN ROLE
    async def decline_admin_role(self, company_id: int, user_id: int, current_user: User) -> User:
        if user_id == current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't fire yourself from admin role")

        company = await self.get_company_by_id(company_id)  # ensures that company exists & gets company

        if company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You don't have permissions to fire from admin role in this company")

        user_service = UserService(self.db)
        user = await user_service.get_user_by_id(user_id)  # ensures that user exists & gets user

        user_search = select(company_members).where(
            and_(
                company_members.c.company_id == company_id,
                company_members.c.user_id == user_id))
        user_presence = await self.db.execute(user_search)
        member = user_presence.mappings().first()

        if not member:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't fire user from admin role if user isn't a member of company")

        if not member['is_admin']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't fire user from admin role who isn't an admin already")

        update_user = update(company_members).where(
            and_(
                company_members.c.company_id == company_id,
                company_members.c.user_id == user_id)).values(is_admin=False)
        await self.db.execute(update_user)
        await self.db.commit()
        return user


    # GET COMPANY'S ADMINISTRATION
    async def get_company_administration(self, company_id: int, current_user: User):
        company = await self.get_company_by_id(company_id)

        if company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Only owners of company are able to view administration list")

        admins = select(User).where(
            and_(
                company_members.c.company_id == company_id,
                company_members.c.is_admin == True
            )
        )

        administration = await self.db.execute(admins)
        return administration.scalars().all()
