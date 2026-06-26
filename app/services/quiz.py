import json
from typing import TYPE_CHECKING, List

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ..logger import logger
from ..models.user import User
from ..repositories.base import delete_from_db, get_with_pagination
from ..repositories.quiz import create_quiz, get_quiz_by_id, update_quiz
from ..models.quiz import Quiz
from ..schemas.quiz import QuizCreate, QuizUpdate, QuizSubmit, UserAnswerSubmit

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


    # TEMPORARILY SAVES ANSWER FOR 1 QUESTION IN REDIS FOR 48 HOURS
    async def save_question_progress(self, redis: Redis, quiz_id: int, user_id: int, answer_data: UserAnswerSubmit):
        redis_key = f"quiz_progress:{user_id}:{quiz_id}"

        async with redis.pipeline(transaction=True) as pipe:
            await pipe.hset(
                redis_key,
                str(answer_data.question_id),
                json.dumps(answer_data.chosen_answer_id))
            await pipe.expire(redis_key, 172800)  # 48 hours

            await pipe.execute()


    # GETS ALL STORED ANSWERS IN REDIS FOR PAST 48 HOURS
    async def get_quiz_progress(self, redis: Redis, user_id: int, quiz_id: int) -> dict:
            redis_key = f"quiz_progress:{user_id}:{quiz_id}"
            stored_data = await redis.hgetall(redis_key)

            if not stored_data:
                return {}

            return {int(q_id): json.loads(val) for q_id, val in stored_data.items()}

    # DELETES CACHE IN REDIS AFTER SUCCESSFUL QUIZ SAVING IN POSTGRESQL
    async def clear_quiz_progress(self, redis: Redis, user_id: int, quiz_id: int):
            redis_key = f"quiz_progress:{user_id}:{quiz_id}"
            await redis.delete(redis_key)


    # SUBMITS QUIZ
    async def submit_quiz(self, redis: Redis, current_user: User, quiz_id: int, submission_data: QuizSubmit):
            user_answers_dict = await self.get_quiz_progress(redis, current_user.id, quiz_id)

            if not user_answers_dict:
                if submission_data and submission_data.answers:
                    user_answers_dict = {a.question_id: a.chosen_answer_id for a in submission_data.answers}
                else:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                        detail="No answers found in progress or request body. Please answer the questions.")


