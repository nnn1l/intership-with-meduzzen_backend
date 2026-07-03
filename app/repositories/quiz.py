from datetime import datetime
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..logger import logger
from ..models import Quiz, Question, AnswerOption, QuizAttempt, User, company_members
from ..schemas.quiz import QuizCreate, QuizUpdate, AnswerUpdate


async def create_quiz(quiz_data: QuizCreate, company_id: int, db: AsyncSession) -> Quiz:
    try:
        logger.info(f"Attempting to create quiz with title f{quiz_data.title}...")
        quiz = Quiz(
            company_id=company_id,
            title=quiz_data.title,
            description=quiz_data.description,
            max_attemtps=quiz_data.max_attempts
        )
        db.add(quiz)
        await db.flush()  # get quiz.id without transaction commit

        for q_item in quiz_data.questions:
            question = Question(
                quiz_id=quiz.id,
                title=q_item.title
            )
            db.add(question)
            await db.flush()  # get question.id to link answers

            for a_item in q_item.answers:
                answer = AnswerOption(
                    question_id=question.id,
                    answer=a_item.answer,
                    is_correct=a_item.is_correct
                )
                db.add(answer)
        await db.commit()
        await db.refresh(quiz)
        return quiz
    except Exception as e:
        await db.rollback()
        logger.error('Error appeared during creating a quiz block')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Internal server error during quiz creating: {str(e)}")

async def get_quiz_by_id(quiz_id: int, db: AsyncSession) -> Quiz:
    query = select(Quiz).where(Quiz.id == quiz_id).options(selectinload(Quiz.questions).selectinload(Question.answers))
    result = await db.execute(query)
    return result.scalars().first()

async def update_quiz(quiz: Quiz, quiz_data: QuizUpdate, db: AsyncSession):
    quiz_questions: list[Question] = quiz.questions
    try:
        # modifying quiz data itself
        update_data = quiz_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(quiz, key, value)

        # synchronising questions (if they were sent)
        if quiz_data.questions is not None:
            incoming_question_ids = {q.id for q in quiz_data.questions if q.id is not None}

            for db_question in list(quiz.questions):  # deleting questions that frontend didn't send
                if db_question.id not in incoming_question_ids:  # (user deleted question during update)
                    await db.delete(db_question)

            # updating existing or new questions
            for q_item in quiz_data.questions:
                if q_item.id is not None:  # existing question
                    db_question = next((q for q in quiz_questions if q.id == q_item.id), None)
                    if db_question:
                        db_question.title = q_item.title
                        await _sync_answer(db_question, q_item.answers, db)

                else:  # new question
                    new_question = Question(
                        quiz_id=quiz.id,
                        title=q_item.title
                    )
                    db.add(new_question)
                    await db.flush()  # get question id

                    for a_item in q_item.answers:
                        new_answer = AnswerOption(
                            question_id=new_question.id,
                            answer=a_item.answer,
                            is_correct=a_item.is_correct
                        )
                        db.add(new_answer)

        await db.commit()
        await db.refresh(quiz)
        logger.info(f"Quiz {quiz_data.title} successfully modified")
        return quiz

    except Exception as e:
        await db.rollback()
        logger.error('Error appeared during updating quiz block')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Internal server error during quiz creation: {str(e)}")

async def _sync_answer(db_question: Question, incoming_answers: List[AnswerUpdate], db: AsyncSession):
        incoming_answer_ids = {a.id for a in incoming_answers if a.id is not None}

        # deleting removed answers
        for db_answer in list(db_question.answers):
            if db_answer.id not in incoming_answer_ids:
                await db.delete(db_answer)

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
                db.add(new_answer)

async def check_max_attepmts(quiz: Quiz, current_user: User, db: AsyncSession):
    query = select(func.count()).where(
        and_(QuizAttempt.quiz_id == quiz.id,
             QuizAttempt.user_id == current_user.id)
    )
    attempts = (await db.execute(query)).scalar() or 0

    if quiz.max_attempts <= attempts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"You've reached the maximum limit of {quiz.max_attempts} attempts for this quiz")

async def get_members_ids_of_company_by_quiz(quiz: Quiz, db: AsyncSession) -> list[int]:
    members_query = select(company_members.c.user_id).where(
        company_members.c.company_id == quiz.company_id)
    result = await db.execute(members_query)
    return [row[0] for row in result.all()]

async def get_members_completed_quiz(quiz: Quiz, time_limit: datetime, db: AsyncSession) -> list[int]:
    completed_query = select(QuizAttempt.user_id).where(
        and_(
            QuizAttempt.quiz_id == quiz.id,
            QuizAttempt.updated_at >= time_limit))
    completed_result = await db.execute(completed_query)
    return [row[0] for row in completed_result.all()]

async def get_quiz_by_title_and_company(title: str, company_id: int, db: AsyncSession) -> Quiz|None:
    query = select(Quiz).where(
        and_(
            Quiz.title == title,
            Quiz.company_id == company_id))
    result = await db.execute(query)
    return result.scalar_one_or_none()
