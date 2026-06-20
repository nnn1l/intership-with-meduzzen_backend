from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status, HTTPException

from ..models.company import company_members
from ..models.quiz import QuizAttempt
from ..models.user import User
from ..utils.dependencies import check_admin_role

if TYPE_CHECKING:
    from .company import CompanyService


class UserAnalytics:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session


    # GET % OF USER'S CORRECT ANSWERS IN ALL TAKEN QUIZZES
    async def get_user_analytics_global(self, current_user: User) -> float:
        statistics = select(
            func.sum(QuizAttempt.correct_answers).label("total_correct"),
            func.sum(QuizAttempt.total_questions).label("total_questions")
        ).where(QuizAttempt.user_id == current_user.id)
        result = (await self.db.execute(statistics)).first()

        if not result or result.total_questions is None or result.total_questions == 0:
            return 0.0

        return round((result.total_correct / result.total_questions) * 100, 2)


    # PROVIDES A LIST OF AVERAGE SCORES FOR EACH QUIZ TAKEN BY THE USER WITH TIME RANGES
    async def get_user_analytics_by_time_periods(self,current_user: User, start_date: datetime = None, end_date: datetime = None) -> list[dict]:
        statistics = select(
            QuizAttempt.quiz_id,
            func.sum(QuizAttempt.correct_answers).label("total_correct"),
            func.sum(QuizAttempt.total_questions).label("total_questions")
        ).where(QuizAttempt.user_id == current_user.id).group_by(QuizAttempt.quiz_id)

        if start_date: # filter by period
            statistics = statistics.where(QuizAttempt.updated_at >= start_date)
        if end_date:
            statistics = statistics.where(QuizAttempt.updated_at <= end_date)

        res = await self.db.execute(statistics)
        rows = res.all()

        analytics_data = []
        for row in rows:
            percentage = (row.total_correct / row.total_questions) * 100 if row.total_questions and row.total_questions > 0 else 0.0

            analytics_data.append({
                "quiz_id": row.quiz_id,
                "score": round(percentage, 2),
                "total_correct": row.total_correct,
                "total_questions": row.total_questions
            })

        return analytics_data


    # DISPLAYS A LIST OF QUIZZES ALONG WITH THE TIMESTAMPS OF THEIR LAST COMPLETION
    async def get_user_analytics_last_competition(self, current_user: User) -> list[dict]:
        statistics = select(
            QuizAttempt.quiz_id,
            func.max(QuizAttempt.updated_at).label("last_completed_at")
        ).where(QuizAttempt.user_id == current_user.id).group_by(QuizAttempt.quiz_id)

        res = await self.db.execute(statistics)
        rows = res.all()
        return [{
            "quiz_id": row.quiz_id,
            "last_completed_at": row.last_completed_at
        }for row in rows]




class CompanyAnalytics:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session


    # GET % OF USER'S CORRECT ANSWERS IN TAKEN QUIZZES INSIDE 1 COMPANY
    async def get_user_analytics_in_company(self, user_id: int, company_id: int, current_user: User) -> list[dict]:
        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(company_id) # ensures company exists & get company

        admin_role = check_admin_role(company_id, current_user.id)
        if not admin_role or company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You aren't an admin/owner of this company")

        user_search = select(company_members).where(
            and_(
                company_members.c.company_id == company_id,
                company_members.c.user_id == user_id))
        user_presence = await self.db.execute(user_search)
        member = user_presence.mappings().first()

        if not member:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't check user's analytics if user isn't a member of your company")

        statistics = select(
            QuizAttempt.quiz_id,
            func.date_trunc('week', QuizAttempt.updated_at).label("week"),
            func.sum(QuizAttempt.correct_answers).label("total_correct"),
            func.sum(QuizAttempt.total_questions).label("total_questions")
        ).where(
            and_(
                QuizAttempt.user_id == user_id,
                QuizAttempt.company_id == company_id
            )
        ).group_by(QuizAttempt.quiz_id, func.date_trunc('week',
                QuizAttempt.updated_at)).order_by("week")
        res = await self.db.execute(statistics)
        rows = res.all()

        return [{
            "quiz_id": r.quiz_id,
            "week": r.week.strftime("%Y-%m-%d") if r.week else None,
            "score": round((r.total_correct / r.total_questions) * 100, 2) if r.total_questions else 0.0
        } for r in rows]


    # GET THE AVERAGE SCORES OF ALL COMPANY MEMBERS, WITH DYNAMICS OVER TIME (WEEK)
    async def get_member_analytics_over_week(self, company_id: int, current_user: User) -> list[dict]:
        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(company_id)  # ensures company exists & get company

        admin_role = check_admin_role(company_id, current_user.id)
        if not admin_role or company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You aren't an admin/owner of this company")

        statistics = select(
            QuizAttempt.quiz_id,
            func.date_trunc('week', QuizAttempt.updated_at).label("week"),
            func.sum(QuizAttempt.correct_answers).label("total_correct"),
            func.sum(QuizAttempt.total_questions).label("total_questions")
        ).join(
            company_members,
            and_(QuizAttempt.user_id == company_members.c.user_id,
                 QuizAttempt.company_id == company_members.c.company_id)
        ).where(
                QuizAttempt.company_id == company_id
        ).group_by(QuizAttempt.quiz_id, func.date_trunc('week',
                                                        QuizAttempt.updated_at)).order_by("week")
        res = await self.db.execute(statistics)
        rows = res.all()

        analytics_data = []
        for row in rows:
            percentage = (row.total_correct / row.total_questions) * 100 if row.total_questions and row.total_questions > 0 else 0.0

            analytics_data.append({
                "week": row.week.strftime("%Y-%m-%d") if row.week else None,
                "company_members_score": round(percentage, 2)
            })

        return analytics_data


    async def get_company_members_last_competition(self, company_id, current_user: User) -> list[dict]:
        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(company_id)  # ensures company exists & get company

        admin_role = check_admin_role(company_id, current_user.id)
        if not admin_role or company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You aren't an admin/owner of this company")

        statistics = select(company_members.c.user_id,
                            QuizAttempt.quiz_id,
                            func.max(QuizAttempt.updated_at).label("last_completed_at")
                            ).outerjoin(
            QuizAttempt,
            and_(company_members.c.user_id == QuizAttempt.user_id,
                 company_members.c.company_id == QuizAttempt.company_id)
        ).where(QuizAttempt.company_id == company_id).group_by(company_members.c.user_id, QuizAttempt.quiz_id).order_by(company_members.c.user_id, func.max(QuizAttempt.updated_at).desc().nulls_last())
        res = await self.db.execute(statistics)
        rows = res.all()

        return[{
            "user_id": row.user_id,
            "quiz_id": row.quiz_id,
            "last_completed_at": row.last_completed_at
        }for row in rows]


