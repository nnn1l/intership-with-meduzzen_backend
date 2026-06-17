from typing import TYPE_CHECKING, List

from fastapi import HTTPException, status
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..logger import logger
from ..models.user import User
from ..models.quiz import Quiz, Question, AnswerOption, QuizAttempt
from ..schemas.quiz import QuizCreate, QuizUpdate, AnswerUpdate, QuizSubmit

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

        try:
            quiz = Quiz(
                company_id = company_id,
                title = quiz_data.title,
                description = quiz_data.description,
                max_attemtps = quiz_data.max_attempts
            )
            self.db.add(quiz)
            await self.db.flush() # get quiz.id without transaction commit

            for q_item in quiz_data.questions:
                question = Question(
                    quiz_id = quiz.id,
                    title = q_item.title
                )
                self.db.add(question)
                await self.db.flush() # get question.id to link answers

                for a_item in q_item.answers:
                    answer = AnswerOption(
                        question_id = question.id,
                        answer = a_item.answer,
                        is_correct = a_item.is_correct
                    )
                    self.db.add(answer)
            await self.db.commit()
            await self.db.refresh(quiz)
            return quiz

        except Exception as e:
            await self.db.rollback()
            logger.error('Error appeared during creating a quiz block')
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error during quiz update: {str(e)}")


    # GET QUIZ BY ID
    async def get_quiz_by_id(self, quiz_id: int) -> Quiz:
        query = select(Quiz).where(Quiz.id == quiz_id).options(selectinload(Quiz.questions).selectinload(Question.answers))
        result = await self.db.execute(query)
        quiz = result.scalar_one_or_none()

        if not quiz:
            logger.error(f"Quiz with ID {quiz_id} wasn't found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz with this ID doesn't exist")

        return quiz


    # GET QUIZZES WITH PAGINATION
    async def get_quizzes(self, limit: int, offset: int) -> List[Quiz]:
        query = select(Quiz).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())


    # UPDATE QUIZ
    async def update_quiz(self, quiz_id: int, quiz_data: QuizUpdate, current_user: User) -> Quiz:
        quiz = await self.get_quiz_by_id(quiz_id)
        quiz_questions: list[Question] = quiz.questions

        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(quiz.company_id)

        admin_role = check_admin_role(company.id, current_user.id)

        if not admin_role or company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You don't have permissions to modify quizzes from this company")

        logger.info(f"Modifying quiz {quiz_data.title}")
        try:
            # modifying quiz data itself
            update_data = quiz_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(quiz, key, value)

            # synchronising questions (if they were sent)
            if quiz_data.questions is not None:
                incoming_question_ids = {q.id for q in quiz.questions if q.id is not None}

                for db_question in list(quiz.questions): # deleting questions that frontend didn't send
                    if db_question.id not in incoming_question_ids: # (user deleted question during update)
                        await self.db.delete(db_question)

                # updating existing or new questions
                for q_item in quiz_data.questions:
                    if q_item.id is not None: # existing question
                        db_question = next((q for q in quiz_questions if q.id == q_item.id), None)
                        if db_question:
                            db_question.title = q_item.title
                            await self._sync_answer(db_question, q_item.answers)

                    else: # new question
                        new_question = Question(
                            quiz_id = quiz_id,
                            title = q_item.title
                        )
                        self.db.add(new_question)
                        await self.db.flush() # get question id

                        for a_item in q_item.answers:
                            new_answer = AnswerOption(
                                question_id=new_question.id,
                                answer=a_item.answer,
                                is_correct=a_item.is_correct
                            )
                            self.db.add(new_answer)

            await self.db.commit()
            await self.db.refresh(quiz)
            logger.info(f"Quiz {quiz_data.name} successfully modified")
            return quiz

        except Exception as e:
            await self.db.rollback()
            logger.error('Error appeared during updating quiz block')
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f"Internal server error during quiz creation: {str(e)}")


    # DELETE QUIZ
    async def delete_quiz(self, quiz_id: int, current_user: User) -> bool:
        quiz = await self.get_quiz_by_id(quiz_id)

        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(quiz.company_id)

        admin_role = check_admin_role(company.id, current_user.id)

        if not admin_role or company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You don't have permissions to delete quizzes from this company")

        await self.db.delete(quiz)
        await self.db.commit()
        logger.info(f"Quiz with ID {quiz_id} deleted successfully")
        return True


    # synchronizing answers
    async def _sync_answer(self, db_question: Question, incoming_answers: List[AnswerUpdate]):
        incoming_answer_ids = {a.id for a in incoming_answers if a.id is not None}

        # deleting removed answers
        for db_answer in list(db_question.answers):
            if db_answer.id not in incoming_answer_ids:
                await self.db.delete(db_answer)

        # updating existing or new answers
        for a_item in incoming_answers:
            if a_item.id is not None: # existing answer
                db_answer = next((a for a in db_question.answers if a.id == a_item.id), None)
                if db_answer:
                    db_answer.answer = a_item.answer
                    db_answer.is_correct = a_item.is_correct

            else: # new answer
                new_answer = AnswerOption(
                    question_id = db_question.id,
                    answer = a_item.answer,
                    is_correct = a_item.is_correct
                )
                self.db.add(new_answer)


    # SUBMIT QUIZ & RESULT (new quiz attempt creation)
    async def create_quiz_attempt(self, quiz_id: int, answers: QuizSubmit, current_user: User) -> QuizAttempt:
        quiz = await self.get_quiz_by_id(quiz_id) # ensures that quiz exists & gets quiz

        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(quiz.company_id)

        admin_role = check_admin_role(company.id, current_user.id)
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


