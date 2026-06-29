from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.quiz import Quiz
from ..repositories.base import select_all
from ..repositories.quiz import get_members_ids_of_company_by_quiz, get_members_completed_quiz
from ..schemas.notification import NotificationCreate

if TYPE_CHECKING:
    from .company import CompanyService
    from .notification import NotificationService
    from .user import UserService


class QuizReminderService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session


    async def check_and_remind_users(self):
        quizzes = await select_all(Quiz, self.db)

        time_limit = datetime.now(timezone.utc) - timedelta(hours=24)

        for quiz in quizzes:
            all_members_ids = await get_members_ids_of_company_by_quiz(quiz, self.db)

            if not all_members_ids:
                continue

            completed_user_ids = await get_members_completed_quiz(quiz, time_limit, self.db)

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
