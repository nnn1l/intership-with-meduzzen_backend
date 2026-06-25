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

        admin_role = await check_admin_role(company_id, current_user.id)

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

        admin_role = await check_admin_role(company.id, current_user.id)

        if not admin_role and company.owner_id != current_user.id:
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

        if not admin_role and company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You don't have permissions to delete quizzes from this company")

        await delete_from_db(quiz, self.db)
        logger.info(f"Quiz with ID {quiz_id} deleted successfully")




    # SUBMIT QUIZ & RESULT (new quiz attempt creation)
    async def create_quiz_attempt(self, quiz_id: int, answers: QuizSubmit, current_user: User) -> QuizAttempt:
        quiz = await self.get_quiz_by_id(quiz_id) # ensures that quiz exists & gets quiz

        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(quiz.company_id)

        admin_role = await check_admin_role(company.id, current_user.id)
        if admin_role or company.owner_id == current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Owners and admins of companies aren't allowed to take participation in their own companies' quizzes")

        if quiz.max_attempts > 0: # if quiz.max_attempts == 0, user is able to take quiz as many times as user wants
            query = select(func.count()).where(
                and_(QuizAttempt.quiz_id == quiz_id,
                     QuizAttempt.user_id == current_user.id)
            )
            attempts = (await self.db.execute(query)).scalar() or 0

            if quiz.max_attempts <= attempts:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"You've reached the maximum limit of {quiz.quiz_attempts} attempts for this quiz")

        total_questions = len(quiz.questions)
        correct_answer_count = 0
        user_answers = {ans.question_id: set(ans.chosen_answer_id) for ans in answers.answers}

        for question in quiz.questions:
            correct_ids = {opt.id for opt in question.answers if opt.is_correct}
            user_chosen = user_answers.get(question.id, set())

            if user_chosen == correct_ids and len(correct_ids) > 0:
                correct_answer_count += 1

        score = (correct_answer_count / total_questions) * 100

        try:
            new_attempt = QuizAttempt(
                quiz_id = quiz_id,
                user_id = current_user.id,
                company_id = company.id,
                score = score,
                total_questions = total_questions,
                correct_answers = correct_answer_count
            )

            self.db.add(new_attempt)
            await self.db.commit()
            await self.db.refresh(new_attempt)

            return new_attempt

        except Exception as e:
            await self.db.rollback()
            logger.error('Error appeared during creating a quiz attempt')
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error during quiz update: {str(e)}")


    # GET % OF USER'S CORRECT ANSWERS IN TAKEN QUIZZES INSIDE 1 COMPANY
    async def get_user_analytics_in_company(self, user_id: int, company_id: int) -> float:
        statistics = select(
            func.sum(QuizAttempt.correct_answers).label("total_correct"),
            func.sum(QuizAttempt.total_questions).label("total_questions")
        ).where(
            and_(
                QuizAttempt.user_id == user_id,
                QuizAttempt.company_id == company_id
            )
        )
        result = (await self.db.execute(statistics)).first()

        if not result or result.total_questions is None or result.total_questions == 0:
            return 0.0

        return (result.total_correct / result.total_questions) * 100


    # GET % OF USER'S CORRECT ANSWERS IN ALL TAKEN QUIZZES
    async def get_user_analytics_global(self, user_id: int) -> float:
        statistics = select(
            func.sum(QuizAttempt.correct_answers).label("total_correct"),
            func.sum(QuizAttempt.total_questions).label("total_questions")
        ).where(QuizAttempt.user_id == user_id)
        result = (await self.db.execute(statistics)).first()

        if not result or result.total_questions is None or result.total_questions == 0:
            return 0.0

        return (result.total_correct / result.total_questions) * 100


