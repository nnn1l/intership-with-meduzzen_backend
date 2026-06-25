from datetime import datetime

from fastapi import Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import init_db
from ..models import QuizAttempt, User, company_members
from ..schemas.analytics import UserGlobalAnalyticsResponse, UserQuizPeriodAnalyticsResponse, \
    UserLastCompletionResponse, CompanyMemberQuizTrendsResponse, CompanyOverallDynamicsResponse, \
    CompanyMemberLastAttemptResponse


async def get_user_analytics_global(current_user: User, db: AsyncSession = Depends(init_db)) -> UserGlobalAnalyticsResponse:
    statistics = select(
        func.sum(QuizAttempt.correct_answers).label("total_correct"),
        func.sum(QuizAttempt.total_questions).label("total_questions")
    ).where(QuizAttempt.user_id == current_user.id)
    result = (await db.execute(statistics)).mappings().first()

    if not result or result.total_questions is None or result.total_questions == 0:
        score = UserGlobalAnalyticsResponse(global_score=0.0)
        return score
    score = UserGlobalAnalyticsResponse(global_score=round((result.total_correct / result.total_questions) * 100, 2))
    return score

async def get_user_analytics_by_time_periods(current_user: User, start_date: datetime = None, end_date: datetime = None, db: AsyncSession = Depends(init_db)) -> list[UserQuizPeriodAnalyticsResponse]:
    statistics = select(
        QuizAttempt.quiz_id,
        func.sum(QuizAttempt.correct_answers).label("total_correct"),
        func.sum(QuizAttempt.total_questions).label("total_questions")
    ).where(QuizAttempt.user_id == current_user.id).group_by(QuizAttempt.quiz_id)

    if start_date: # filter by period
        statistics = statistics.where(QuizAttempt.updated_at >= start_date)
    if end_date:
        statistics = statistics.where(QuizAttempt.updated_at <= end_date)

    res = await db.execute(statistics)
    rows = res.all()

    analytics_data = []
    for row in rows:
        percentage = (row.total_correct / row.total_questions) * 100 if row.total_questions and row.total_questions > 0 else 0.0

        analytics_data.append(UserQuizPeriodAnalyticsResponse(
            quiz_id= row.quiz_id,
            score=  round(percentage, 2),
            total_correct = row.total_correct,
            total_questions = row.total_questions))

    return analytics_data

async def get_user_analytics_last_competition(current_user: User, db: AsyncSession = Depends(init_db)) -> list[UserLastCompletionResponse]:
    statistics = select(
        QuizAttempt.quiz_id,
        func.max(QuizAttempt.updated_at).label("last_completed_at")
        ).where(QuizAttempt.user_id == current_user.id).group_by(QuizAttempt.quiz_id)

    res = await db.execute(statistics)
    rows = res.all()
    return [UserLastCompletionResponse(
            quiz_id = row.quiz_id,
            last_completed_at = row.last_completed_at
        )for row in rows]

async def get_user_analytics_in_company(user_id: int, company_id: int, db: AsyncSession = Depends(init_db)) -> list[CompanyMemberQuizTrendsResponse]:
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
    res = await db.execute(statistics)
    rows = res.all()

    return [CompanyMemberQuizTrendsResponse(
        quiz_id=r.quiz_id,
        week=r.week.strftime("%Y-%m-%d") if r.week else None,
        score=round((r.total_correct / r.total_questions) * 100, 2) if r.total_questions else 0.0
    ) for r in rows]

async def get_member_analytics_over_week(company_id: int, db: AsyncSession = Depends(init_db)) -> list[CompanyOverallDynamicsResponse]:
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
    res = await db.execute(statistics)
    rows = res.all()

    analytics_data = []
    for row in rows:
        percentage = (row.total_correct / row.total_questions) * 100 if row.total_questions and row.total_questions > 0 else 0.0

        analytics_data.append(CompanyOverallDynamicsResponse(
            week=row.week.strftime("%Y-%m-%d") if row.week else None,
            company_members_score=round(percentage, 2)))

    return analytics_data

async def get_company_members_last_competition(company_id: int, db: AsyncSession = Depends(init_db)) -> list[CompanyMemberLastAttemptResponse]:
    statistics = select(company_members.c.user_id,
                        QuizAttempt.quiz_id,
                        func.max(QuizAttempt.updated_at).label("last_completed_at")
                        ).outerjoin(
        QuizAttempt,
        and_(company_members.c.user_id == QuizAttempt.user_id,
             company_members.c.company_id == QuizAttempt.company_id)
    ).where(QuizAttempt.company_id == company_id).group_by(company_members.c.user_id, QuizAttempt.quiz_id).order_by(
        company_members.c.user_id, func.max(QuizAttempt.updated_at).desc().nulls_last())
    res = await db.execute(statistics)
    rows = res.all()

    return [CompanyMemberLastAttemptResponse(
        user_id=row.user_id,
        quiz_id=row.quiz_id,
        last_completed_at=row.last_completed_at
    ) for row in rows]