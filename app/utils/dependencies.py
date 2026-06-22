from fastapi import Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth import verify_auth0_token
from ..database import init_db
from ..models.company import company_members
from ..services.notification import NotificationService
from ..services.quiz import QuizService
from ..services.quiz_checker import QuizReminderService
from ..services.user import UserService
from ..services.analytics import UserAnalytics, CompanyAnalytics
from ..models.user import User
from ..services.auth import AuthService
from ..services.company import CompanyService
from ..services.invitation import InvitationService


async def get_user_service(db: AsyncSession = Depends(init_db)) -> UserService:
    return UserService(db)

async def get_auth_service(db: AsyncSession = Depends(init_db)) -> AuthService:
    return AuthService(db)

async def get_company_service(db: AsyncSession = Depends(init_db)) -> CompanyService:
    return CompanyService(db)

async def get_invitation_service(db: AsyncSession = Depends(init_db)) -> InvitationService:
    return InvitationService(db)

async def get_quiz_service(db: AsyncSession = Depends(init_db)):
    return QuizService(db)

async def get_user_analytics_service(db: AsyncSession = Depends(init_db)) -> UserAnalytics:
    return UserAnalytics(db)

async def get_company_analytics_service(db: AsyncSession = Depends(init_db)) -> CompanyAnalytics:
    return CompanyAnalytics(db)

async def get_notification_service(db: AsyncSession = Depends(init_db)) -> NotificationService:
    return NotificationService(db)

async def get_scheduler_service(db: AsyncSession = Depends(init_db)) -> QuizReminderService:
    return QuizReminderService(db)

async def get_current_user(payload: dict = Depends(verify_auth0_token), service: AuthService = Depends(get_auth_service)) -> User:
    email = payload.get('email')

    if not email:
        email = f'{payload.get("sub")}@auth0.io'

    user = await service.get_or_create_auth0_user(email=email)
    return user

async def validate_profile_owner(user_id: int, current_user: User = Depends(get_current_user)) -> User:
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You're able to manage only your own profile"
        )

    return current_user

async def check_admin_role(company_id: int, user_id: int, db: AsyncSession = Depends(init_db)) -> bool:

    user_search = select(company_members).where(
        and_(
            company_members.c.company_id == company_id,
            company_members.c.user_id == user_id))
    user_presence = await db.execute(user_search)
    member = user_presence.mappings().first()

    if not member:
        return False

    return bool(member['is_admin'])  # if user is amin -> True, otherwise -> false