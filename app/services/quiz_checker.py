from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.company import company_members
from ..models.quiz import Quiz, QuizAttempt
from ..schemas.notification import NotificationCreate

if TYPE_CHECKING:
    from .company import CompanyService
    from .notification import NotificationService
    from .user import UserService


class QuizReminderService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session


    async def check_and_remind_users(self):
        quizzes_query = select(Quiz)
        quizzes = (await self.db.execute(quizzes_query)).scalars().all()

        time_limit = datetime.now(timezone.utc) - timedelta(hours=24)

        for quiz in quizzes:
            members_query = select(company_members.c.user_id).where(
                company_members.c.company_id == quiz.company_id)
            result = await self.db.execute(members_query)
            all_members_ids = [row[0] for row in result.all()]

            if not all_members_ids:
                continue

            completed_query = select(QuizAttempt.user_id).where(
                and_(
                    QuizAttempt.quiz_id == quiz.id,
                    QuizAttempt.updated_at >= time_limit))
            completed_result = await self.db.execute(completed_query)
            completed_user_ids = [row[0] for row in completed_result.all()]

            lazy_user_ids = list(set(all_members_ids) - set(completed_user_ids))

            if lazy_user_ids:
                notification_service = NotificationService(self.db)
                notification_data = NotificationCreate(message=f"Reminder: You haven't completed the quiz '{quiz.title}' in the last 24 hours. Please take it!")

                company_service = CompanyService(self.db)
                company = await company_service.get_company_by_id(quiz.company_id)

                user_service = UserService(self.db)
                user = await user_service.get_user_by_id(company.owner_id)

                await notification_service.create_notifications(
                    notification_data = notification_data,
                    current_user = user,
                    receiver_ids = lazy_user_ids,
                    company_id = quiz.company_id
                )
