from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status, HTTPException

from ..models.user import User
from ..repositories.analytics import get_user_analytics_by_time_periods, get_user_analytics_last_competition
from ..repositories.company import check_admin_role, is_user_member_of_company
from ..routes.analytics import get_user_analytics_global, get_user_analytics_in_company, get_member_analytics_over_week, \
    get_company_members_last_competition
from ..schemas.analytics import UserGlobalAnalyticsResponse, UserQuizPeriodAnalyticsResponse, \
    UserLastCompletionResponse, CompanyMemberQuizTrendsResponse, CompanyOverallDynamicsResponse, \
    CompanyMemberLastAttemptResponse

if TYPE_CHECKING:
    from .company import CompanyService


class UserAnalytics:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session


    # GET % OF USER'S CORRECT ANSWERS IN ALL TAKEN QUIZZES
    async def get_user_analytics_global(self, current_user: User) -> UserGlobalAnalyticsResponse:
        return await get_user_analytics_global(current_user)


    # PROVIDES A LIST OF AVERAGE SCORES FOR EACH QUIZ TAKEN BY THE USER WITH TIME RANGES
    async def get_user_analytics_by_time_periods(self,current_user: User, start_date: datetime = None, end_date: datetime = None) -> list[UserQuizPeriodAnalyticsResponse]:
        return await get_user_analytics_by_time_periods(current_user, start_date, end_date)


    # DISPLAYS A LIST OF QUIZZES ALONG WITH THE TIMESTAMPS OF THEIR LAST COMPLETION
    async def get_user_analytics_last_competition(self, current_user: User) -> list[UserLastCompletionResponse]:
        return await get_user_analytics_last_competition(current_user)




class CompanyAnalytics:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session


    # GET % OF USER'S CORRECT ANSWERS IN TAKEN QUIZZES INSIDE 1 COMPANY
    async def get_user_analytics_in_company(self, user_id: int, company_id: int, current_user: User) -> list[CompanyMemberQuizTrendsResponse]:
        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(company_id) # ensures company exists & get company

        admin_role = await check_admin_role(company_id, current_user.id)
        if not admin_role and company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You aren't an admin/owner of this company")

        member = await is_user_member_of_company(company_id, user_id)

        if not member:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't check user's analytics if user isn't a member of your company")

        query = await get_user_analytics_in_company(user_id, company_id)

        return query


    # GET THE AVERAGE SCORES OF ALL COMPANY MEMBERS, WITH DYNAMICS OVER TIME (WEEK)
    async def get_member_analytics_over_week(self, company_id: int, current_user: User) -> list[CompanyOverallDynamicsResponse]:
        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(company_id)  # ensures company exists & get company

        admin_role = await check_admin_role(company_id, current_user.id)
        if not admin_role and company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You aren't an admin/owner of this company")

        analytics_data = await get_member_analytics_over_week(company_id)

        return analytics_data


    async def get_company_members_last_competition(self, company_id, current_user: User) -> list[CompanyMemberLastAttemptResponse]:
        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(company_id)  # ensures company exists & get company

        admin_role = await check_admin_role(company_id, current_user.id)
        if not admin_role and company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You aren't an admin/owner of this company")

        query = await get_company_members_last_competition(company_id)
        return query


