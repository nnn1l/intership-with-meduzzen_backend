from typing import List, TYPE_CHECKING

from ..models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from ..models.company import Company, company_members
from ..repositories.base import add_to_db, get_by_filter, get_with_pagination, refresh_data_in_db, delete_from_db, \
    delete_table_record_by_filter, update_table_record_by_filter
from ..schemas.company import CompanyCreate, CompanyUpdate
from ..logger import logger
from ..utils.enums import VisibilityStatus
from ..repositories.company import check_admin_role, is_user_member_of_company, get_company_administration, \
    get_company_members

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

            await add_to_db(company, self.db)
            return company

        except Exception as e:
            await self.db.rollback()
            logger.error('Error appeared during creating a company')
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error during company creation: {str(e)}")



    # GET COMPANY BY ID
    async def get_company_by_id(self, company_id: int) -> Company:
        company = await get_by_filter(Company, self.db, id=company_id)

        if not company:
            logger.error(f"Company with ID {company_id} wasn't found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company with this ID doesn't exist")

        return company


    async def get_companies(self, limit: int, offset: int) -> List[Company]:
        companies = await get_with_pagination(Company, limit, offset, self.db)

        return list(companies)


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

        await refresh_data_in_db(company, self.db)
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

        await delete_from_db(company, self.db)
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
        await refresh_data_in_db(company)

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

        user_presence = await is_user_member_of_company(fired_user_id, company_id, self.db)

        if not user_presence:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="This user isn't in this company")

        await delete_table_record_by_filter(company_members, self.db, user_id=fired_user_id, company_id=company_id)
        logger.info(f"User with ID {fired_user_id} fired from company with ID {company_id}")
        return True


    # LEAVE COMPANY
    async def leave_company(self, company_id: int, current_user: User) -> bool:
        company = await self.get_company_by_id(company_id)

        if company.owner_id == current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You can't leave from your own company")

        user_presence = await is_user_member_of_company(current_user.id, company_id, self.db)

        if not user_presence:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You're not in this company to have ability to leave")

        await delete_table_record_by_filter(company_members, self.db, user_id=current_user.id, company_id=company_id)
        logger.info(f"User with ID {current_user.id} left a company with ID {company_id}")
        return True


    # GET COMPANY'S MEMBERS
    async def get_company_members(self, company_id: int, limit: int, offset: int):
        await self.get_company_by_id(company_id)
        members = await get_company_members(company_id, limit, offset, self.db)

        return members



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

        user_presence = await is_user_member_of_company(user_id, company_id, self.db)

        if not user_presence:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't appoint user as an admin if user isn't a member of company")

        admin_role = await check_admin_role(company_id, user_id, self.db)

        if admin_role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't appoint user as an admin twice")

        await update_table_record_by_filter(company_members,{"is_admin":True}, self.db, company_id=company_id, user_id=user_id)
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

        user_presence = await is_user_member_of_company(user_id, company_id, self.db)
        if not user_presence:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't decline user's admin role if user isn't a member of company")

        is_admin = await check_admin_role(company_id, user_id, self.db)
        if not is_admin:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't fire the same user twice")

        await update_table_record_by_filter(company_members,{"is_admin":False}, self.db, company_id=company_id, user_id=user_id)
        return user


    # GET COMPANY'S ADMINISTRATION
    async def get_company_administration(self, company_id: int):
        await self.get_company_by_id(company_id) # ensuring that company exists
        admins = await get_company_administration(company_id, self.db)

        return admins

