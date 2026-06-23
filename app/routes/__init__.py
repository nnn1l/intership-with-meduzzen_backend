from fastapi import APIRouter
from .healthcheck import router as health_router
from .signup_log import router as signuplog_router
from .user import router as user_router
from .company import router as company_router
from .invitation import router as invitation_router
from .quiz import router as quiz_router

api_router = APIRouter()

api_router.include_router(health_router, tags=['Health'])
api_router.include_router(user_router, tags=['User'])
api_router.include_router(signuplog_router, tags=['Sign Up Log'])
api_router.include_router(company_router,tags=['Companies'])
api_router.include_router(invitation_router, tags=['Invitation'])
api_router.include_router(quiz_router, tags=['Quiz'])
