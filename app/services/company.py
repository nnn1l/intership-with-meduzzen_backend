from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from ..models.company import Company
from ..schemas.company import CompanyCreate, CompanyUpdate
from ..logger import logger
from ..utils.enums import VisibilityStatus


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