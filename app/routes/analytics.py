from datetime import datetime

from fastapi import APIRouter, status, Depends

from app.models.user import User
from app.services.analytics import UserAnalytics, CompanyAnalytics
from app.utils.dependencies import get_user_analytics_service, get_company_analytics_service, get_current_user

router = APIRouter()

@router.get('/{user_id}/analytics', response_model=float)
async def get_user_analytics_global(current_user: User = Depends(get_current_user),
                                    service: UserAnalytics = Depends(get_user_analytics_service)):
    return await service.get_user_analytics_global(current_user)

@router.get('{user_id}/analytics-by-time', response_model=list[dict])
async def get_user_analytics_by_time_periods(start_date: datetime = None,
                                            end_date: datetime = None,
                                            current_user: User = Depends(get_current_user),
                                            service: UserAnalytics = Depends(get_user_analytics_service)):
    return await service.get_user_analytics_by_time_periods(current_user, start_date, end_date)

@router.get("{user_id}/analytics-last-competition", response_model=list[dict])
async def get_user_analytics_last_competition(current_user: User = Depends(get_current_user),
                                              service: UserAnalytics = Depends(get_user_analytics_service)):
    return await service.get_user_analytics_last_competition(current_user)

@router.get('/{company_id}/{user_id}/analytics', response_model=list[dict])
async def get_user_analytics_in_company(user_id: int,
                                        company_id: int,
                                        service: CompanyAnalytics = Depends(get_company_analytics_service),
                                        current_user: User = Depends(get_current_user)):
    return await service.get_user_analytics_in_company(user_id, company_id, current_user)

@router.get('/{company_id}/all-members-analytics-over-week', response_model=list[dict])
async def get_member_analytics_over_over(company_id: int,
                                         service: CompanyAnalytics = Depends(get_company_analytics_service),
                                         current_user: User = Depends(get_current_user)):
    return await service.get_member_analytics_over_week(company_id, current_user)

@router.get('/{company_id}/analytics-last-competition', response_model=list[dict])
async def get_company_members_last_competition(company_id: int,
                                         service: CompanyAnalytics = Depends(get_company_analytics_service),
                                         current_user: User = Depends(get_current_user)):
    return await service.get_company_members_last_competition(company_id, current_user)