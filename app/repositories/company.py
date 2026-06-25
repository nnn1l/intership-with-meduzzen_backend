from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import company_members, User
from ..logger import logger


async def is_user_member_of_company(user_id: int, company_id: int, db: AsyncSession):
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


async def check_admin_role(company_id: int, user_id: int, db: AsyncSession) -> bool:
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

async def get_company_administration(company_id: int, db: AsyncSession) -> list[User]:
    admins_query = (
        select(User)
        .join(company_members, User.id == company_members.c.user_id)
        .where(
            and_(
                company_members.c.company_id == company_id,
                company_members.c.is_admin == True
            )
        )
    )
    result = await db.execute(admins_query)
    return list(result.scalars().all())

async def get_company_members(company_id: int, limit: int, offset: int, db: AsyncSession) -> list[User]:
    members_query = (
        select(User)
        .join(company_members, User.id == company_members.c.user_id)
        .where(company_members.c.company_id == company_id)
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(members_query)
    return list(result.scalars().all())