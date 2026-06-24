from fastapi import HTTPException, status, Depends
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import init_db
from ..models import MembershipManagement
from ..utils.enums import Status
from ..logger import logger


async def check_pending_request(company_id: int, user_id: int, db: AsyncSession = Depends(init_db)) -> bool:
    try:
        pending_status = select(MembershipManagement).where(
            and_(
                MembershipManagement.company_id == company_id,
                MembershipManagement.user_id == user_id,
                MembershipManagement.status == Status.PENDING))

        pending_result = await db.execute(pending_status)
        pending = pending_result.mappings().first()

        return True if pending else False
    except Exception as e:
        logger.error("Error occurred while checking if pending exists")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Internal server error during query check_pending_request execute: {str(e)}")