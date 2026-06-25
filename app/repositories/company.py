from fastapi import Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import init_db
from ..models import company_members, User
from ..logger import logger


async def is_user_member_of_company(user_id: int, company_id: int, db: AsyncSession = Depends(init_db)):
    try:
        user_search = select(company_members).where(
            and_(
                company_members.c.user_id == user_id,
                company_members.c.company_id == company_id))
        user_presence = await db.execute(user_search)

        return user_presence.mappings().first() is not None
    except Exception as e:
        logger.error("Error occurred while checking if user is member of company")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Internal server error during query is_user_member_of_company execute: {str(e)}")


async def check_admin_role(company_id: int, user_id: int, db: AsyncSession = Depends(init_db)) -> bool:
    try:
        user_search = select(company_members).where(
            and_(
                company_members.c.company_id == company_id,
                company_members.c.user_id == user_id))
        user_presence = await db.execute(user_search)
        member = user_presence.mappings().first()

        if not member:
            return False

        return bool(member['is_admin'])  # if user is amin -> True, otherwise -> false
    except Exception as e:
        logger.error("Error occurred while checking if user is admin of company")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Internal server error during query check_admin_role execute: {str(e)}")

async def get_company_administration(company_id: int, db: AsyncSession = Depends(init_db)):
    admins = select(User).where(
        and_(
            company_members.c.company_id == company_id,
            company_members.c.is_admin == True
        )
    )

    administration = await db.execute(admins)
    return administration.scalars().all()

async def get_company_members(company_id: int, limit: int = 10, offset: int = 0, db: AsyncSession = Depends(init_db)):
    members = (select(User).join(company_members, User.id == company_members.c.user_id)
               .where(company_members.c.company_id == company_id)
               .limit(limit)
               .offset(offset))

    result = await db.execute(members)
    return result.scalars().all()
