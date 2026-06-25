from typing import TYPE_CHECKING, List

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..logger import logger
from ..models.user import User
from ..models.quiz import Quiz
from ..repositories.base import delete_from_db, get_with_pagination
from ..repositories.quiz import create_quiz, get_quiz_by_id, update_quiz
from ..schemas.quiz import QuizCreate, QuizUpdate

if TYPE_CHECKING:
    from .company import CompanyService
    from ..utils.dependencies import check_admin_role

class QuizService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session


    # CREATE QUIZ
    async def create_quiz(self, quiz_data: QuizCreate, company_id: int, current_user: User) -> Quiz:
        logger.info(f"Attempting to create a quiz with title {quiz_data.title}")
        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(company_id)

        admin_role = check_admin_role(company_id, current_user.id)

        if not admin_role and company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You don't have permissions to create quizzes from this company")

        return await create_quiz(quiz_data, company_id, self.db)


    # GET QUIZ BY ID
    async def get_quiz_by_id(self, quiz_id: int) -> Quiz:
        quiz = await get_quiz_by_id(quiz_id, self.db)

        if not quiz:
            logger.error(f"Quiz with ID {quiz_id} wasn't found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz with this ID doesn't exist")

        return quiz


    # GET QUIZZES WITH PAGINATION
    async def get_quizzes(self, limit: int, offset: int) -> List[Quiz]:
        result = await get_with_pagination(Quiz, self.db, limit, offset)
        return list(result)


    # UPDATE QUIZ
    async def update_quiz(self, quiz_id: int, quiz_data: QuizUpdate, current_user: User) -> Quiz:
        quiz = await self.get_quiz_by_id(quiz_id)

        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(quiz.company_id)

        admin_role = check_admin_role(company.id, current_user.id)

        if not admin_role or company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You don't have permissions to modify quizzes from this company")

        logger.info(f"Modifying quiz {quiz_data.title}")
        return await update_quiz(quiz, quiz_data, self.db)


    # DELETE QUIZ
    async def delete_quiz(self, quiz_id: int, current_user: User):
        quiz = await self.get_quiz_by_id(quiz_id)

        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(quiz.company_id)

        admin_role = await check_admin_role(company.id, current_user.id)

        if not admin_role or company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You don't have permissions to delete quizzes from this company")

        await delete_from_db(quiz, self.db)
        logger.info(f"Quiz with ID {quiz_id} deleted successfully")




