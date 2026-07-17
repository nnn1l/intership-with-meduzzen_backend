from datetime import datetime

from fastapi import APIRouter, Depends

from app.models.user import User
from app.schemas.analytics import CompanyMemberLastAttemptResponse, CompanyOverallDynamicsResponse, \
    UserLastCompletionResponse, UserQuizPeriodAnalyticsResponse, CompanyMemberQuizTrendsResponse, \
    UserGlobalAnalyticsResponse
from app.services.analytics import UserAnalytics, CompanyAnalytics
from app.utils.dependencies import get_user_analytics_service, get_company_analytics_service, get_current_user

router = APIRouter()

@router.get('/analytics/global', response_model=UserGlobalAnalyticsResponse)
async def get_user_analytics_global(current_user: User = Depends(get_current_user),
                                    service: UserAnalytics = Depends(get_user_analytics_service)):
    return await service.get_user_analytics_global(current_user)

@router.get('/analytics/by-time', response_model=list[UserQuizPeriodAnalyticsResponse])
async def get_user_analytics_by_time_periods(start_date: datetime = None,
                                            end_date: datetime = None,
                                            current_user: User = Depends(get_current_user),
                                            service: UserAnalytics = Depends(get_user_analytics_service)):
    return await service.get_user_analytics_by_time_periods(current_user, start_date, end_date)

@router.get("/analytics/last-completion", response_model=list[UserLastCompletionResponse])
async def get_user_analytics_last_competition(current_user: User = Depends(get_current_user),
                                              service: UserAnalytics = Depends(get_user_analytics_service)):
    return await service.get_user_analytics_last_competition(current_user)

@router.get('/companies/{company_id}/members/{user_id}/analytics', response_model=list[CompanyMemberQuizTrendsResponse])
async def get_user_analytics_in_company(user_id: int,
                                        company_id: int,
                                        service: CompanyAnalytics = Depends(get_company_analytics_service),
                                        current_user: User = Depends(get_current_user)):
    return await service.get_user_analytics_in_company(user_id, company_id, current_user)

@router.get('/companies/{company_id}/analytics/weekly-dynamics', response_model=list[CompanyOverallDynamicsResponse])
async def get_member_analytics_over_week(company_id: int,
                                         service: CompanyAnalytics = Depends(get_company_analytics_service),
                                         current_user: User = Depends(get_current_user)):
    return await service.get_member_analytics_over_week(company_id, current_user)

@router.get('/companies/{company_id}/analytics/members-last-completion', response_model=list[CompanyMemberLastAttemptResponse])
async def get_company_members_last_competition(company_id: int,
                                         service: CompanyAnalytics = Depends(get_company_analytics_service),
                                         current_user: User = Depends(get_current_user)):
    return await service.get_company_members_last_competition(company_id, current_user)