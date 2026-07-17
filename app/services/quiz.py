import json
from typing import TYPE_CHECKING, List

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ..logger import logger
from ..models.user import User
from ..repositories.base import delete_from_db, get_with_pagination, add_to_db
from ..repositories.company import is_user_member_of_company, check_admin_role
from ..repositories.quiz import create_quiz, get_quiz_by_id, update_quiz, check_max_attepmts
from ..models.quiz import Quiz, QuizAttempt
from ..schemas.quiz import QuizCreate, QuizUpdate, QuizSubmit, UserAnswerSubmit

if TYPE_CHECKING:
    from .company import CompanyService
    from ..utils.dependencies import check_admin_role
    from .notification import NotificationService

class QuizService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session


    # CREATE QUIZ
    async def create_quiz(self, quiz_data: QuizCreate, company_id: int, current_user: User) -> Quiz:
        logger.info(f"Attempting to create a quiz with title {quiz_data.title}")
        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(company_id)

        admin_role = await check_admin_role(company_id, current_user.id, self.db)

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

        admin_role = await check_admin_role(company.id, current_user.id, self.db)

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

        admin_role = await check_admin_role(company.id, current_user.id, self.db)

        if not admin_role or company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You don't have permissions to delete quizzes from this company")

        await delete_from_db(quiz, self.db)
        logger.info(f"Quiz with ID {quiz_id} deleted successfully")

    # TEMPORARILY SAVES ANSWER FOR 1 QUESTION IN REDIS FOR 48 HOURS
    async def save_question_progress(self, redis: Redis, quiz_id: int, user_id: int, answer_data: UserAnswerSubmit):
        redis_key = f"quiz_progress:{user_id}:{quiz_id}"

        await redis.hset(
                redis_key,
                str(answer_data.question_id),
                json.dumps(answer_data.chosen_answer_id)
            )
        await redis.expire(redis_key, 172800)  # 48 hours


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


    def _calculate_score(self, quiz: Quiz, user_answers_dict: dict) -> tuple[int, float]:
        total_questions = len(quiz.questions)
        if total_questions == 0:
            return 0, 0.0

        correct_answer_count = 0
        user_answers = {}

        for q_id, ans_val in user_answers_dict.items():
            user_answers[int(q_id)] = set(ans_val) if isinstance(ans_val, list) else {ans_val}

        for question in quiz.questions:
            correct_ids = {opt.id for opt in question.answers if opt.is_correct}
            user_chosen = user_answers.get(question.id, set())

            if user_chosen == correct_ids and len(correct_ids) > 0:
                correct_answer_count += 1

        score = (correct_answer_count / total_questions) * 100
        return correct_answer_count, score

    async def _validate_attempt_permissions(self, quiz: Quiz, current_user: User, company_id: int):
        admin_role = await check_admin_role(company_id, current_user.id, self.db)

        if admin_role or current_user.id == (await CompanyService(self.db).get_company_by_id(company_id)).owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Owners and admins of companies aren't allowed to participate in their quizzes"
            )

        if quiz.max_attempts > 0:
            await check_max_attepmts(quiz, current_user, self.db)


    # SUBMIT QUIZ & RESULT (new quiz attempt creation)
    async def create_quiz_attempt(self, quiz_id: int, answers: QuizSubmit, current_user: User, redis: Redis) -> QuizAttempt:
        quiz = await self.get_quiz_by_id(quiz_id)

        await self._validate_attempt_permissions(quiz, current_user, quiz.company_id)

        user_answers_dict = await self.get_quiz_progress(redis, current_user.id, quiz_id)
        if not user_answers_dict:
            if answers and answers.answers:
                user_answers_dict = {ans.question_id: ans.chosen_answer_id for ans in answers.answers}
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No answers found in progress or request body. Please answer questions first"
                )

        correct_answers, score = self._calculate_score(quiz, user_answers_dict)

        new_attempt = QuizAttempt(
            quiz_id=quiz_id,
            user_id=current_user.id,
            company_id=quiz.company_id,
            score=score,
            total_questions=len(quiz.questions),
            correct_answers=correct_answers
        )
        await add_to_db(new_attempt, self.db)
        await self.clear_quiz_progress(redis, current_user.id, quiz_id)

        return new_attempt


    # GET USER PERSONAL QUIZZES EXPORT
    async def get_user_personal_quizzes_export(self, redis: Redis, current_user: User, quiz_id: int = None) -> list[dict]:
        quiz_pattern = quiz_id if quiz_id is not None else "*"
        search_pattern = f"quiz_progress:{current_user.id}:{quiz_pattern}"

        export_results = []

        async for redis_key in redis.scan_iter(match=search_pattern):
            if isinstance(redis_key, bytes):
                redis_key = redis_key.decode()

            parts = redis_key.split(':')
            found_quiz_id = int(parts[2])

            progress = await self.get_quiz_progress(redis, current_user.id, found_quiz_id)

            for q_id, ans_data in progress.items():
                export_results.append({
                    "user_id": current_user.id,
                    "quiz_id": found_quiz_id,
                    "question_id": q_id,
                    "answer_id": ans_data
                })

        return export_results


    async def _validate_company_export_access(self, company_id: int, current_user_id: int, target_user_id: int = None):
            company_service = CompanyService(self.db)
            company = await company_service.get_company_by_id(company_id)

            admin_role = await check_admin_role(company_id, current_user_id, self.db)
            if not admin_role and company.owner_id != current_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You aren't an admin/owner of this company"
                )

            if target_user_id is not None:
                member = await is_user_member_of_company(target_user_id, company_id, self.db)
                if not member:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You can't check quiz results of a user that isn't a member of your company"
                    )

    async def _fetch_export_data_from_redis(self, redis: Redis, company_id: int, user_id: int = None, quiz_id: int = None) -> list[dict]:
            user_pattern = user_id if user_id is not None else "*"
            quiz_pattern = quiz_id if quiz_id is not None else "*"
            search_pattern = f"quiz_progress:{user_pattern}:{quiz_pattern}"

            export_results = []

            async for redis_key in redis.scan_iter(match=search_pattern):
                if isinstance(redis_key, bytes):
                    redis_key = redis_key.decode()

                parts = redis_key.split(':')
                found_user_id = int(parts[1])
                found_quiz_id = int(parts[2])

                if quiz_id is None:
                    found_quiz = await self.get_quiz_by_id(found_quiz_id)
                    if not found_quiz or found_quiz.company_id != company_id:
                        continue

                progress = await self.get_quiz_progress(redis, found_user_id, found_quiz_id)
                for q_id, ans_data in progress.items():
                    export_results.append({
                        "user_id": found_user_id,
                        "quiz_id": found_quiz_id,
                        "question_id": q_id,
                        "answer_id": ans_data
                    })
            return export_results


    async def get_company_quizzes_export(self, redis: Redis, current_user: User, company_id: int,
                                             user_id: int = None, quiz_id: int = None) -> list[dict]:
            await self._validate_company_export_access(company_id, current_user.id, user_id)

            return await self._fetch_export_data_from_redis(redis, company_id, user_id, quiz_id)

        if quiz.max_attempts > 0:
            await check_max_attepmts(quiz, current_user, self.db)


    # SUBMIT QUIZ & RESULT (new quiz attempt creation)
    async def create_quiz_attempt(self, quiz_id: int, answers: QuizSubmit, current_user: User, redis: Redis) -> QuizAttempt:
        quiz = await self.get_quiz_by_id(quiz_id)

        await self._validate_attempt_permissions(quiz, current_user, quiz.company_id)

        user_answers_dict = await self.get_quiz_progress(redis, current_user.id, quiz_id)
        if not user_answers_dict:
            if answers and answers.answers:
                user_answers_dict = {ans.question_id: ans.chosen_answer_id for ans in answers.answers}
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No answers found in progress or request body. Please answer questions first"
                )

        correct_answers, score = self._calculate_score(quiz, user_answers_dict)

        new_attempt = QuizAttempt(
            quiz_id=quiz_id,
            user_id=current_user.id,
            company_id=quiz.company_id,
            score=score,
            total_questions=len(quiz.questions),
            correct_answers=correct_answers
        )
        await add_to_db(new_attempt, self.db)
        await self.clear_quiz_progress(redis, current_user.id, quiz_id)

        return new_attempt


    # GET USER PERSONAL QUIZZES EXPORT
    async def get_user_personal_quizzes_export(self, redis: Redis, current_user: User, quiz_id: int = None) -> list[dict]:
        quiz_pattern = quiz_id if quiz_id is not None else "*"
        search_pattern = f"quiz_progress:{current_user.id}:{quiz_pattern}"

        export_results = []

        async for redis_key in redis.scan_iter(match=search_pattern):
            if isinstance(redis_key, bytes):
                redis_key = redis_key.decode()

            parts = redis_key.split(':')
            found_quiz_id = int(parts[2])

            progress = await self.get_quiz_progress(redis, current_user.id, found_quiz_id)

            for q_id, ans_data in progress.items():
                export_results.append({
                    "user_id": current_user.id,
                    "quiz_id": found_quiz_id,
                    "question_id": q_id,
                    "answer_id": ans_data
                })

        return export_results


    async def _validate_company_export_access(self, company_id: int, current_user_id: int, target_user_id: int = None):
            company_service = CompanyService(self.db)
            company = await company_service.get_company_by_id(company_id)

            admin_role = await check_admin_role(company_id, current_user_id, self.db)
            if not admin_role and company.owner_id != current_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You aren't an admin/owner of this company"
                )

            if target_user_id is not None:
                member = await is_user_member_of_company(target_user_id, company_id, self.db)
                if not member:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You can't check quiz results of a user that isn't a member of your company"
                    )

    async def _fetch_export_data_from_redis(self, redis: Redis, company_id: int, user_id: int = None, quiz_id: int = None) -> list[dict]:
            user_pattern = user_id if user_id is not None else "*"
            quiz_pattern = quiz_id if quiz_id is not None else "*"
            search_pattern = f"quiz_progress:{user_pattern}:{quiz_pattern}"

            export_results = []

            async for redis_key in redis.scan_iter(match=search_pattern):
                if isinstance(redis_key, bytes):
                    redis_key = redis_key.decode()

                parts = redis_key.split(':')
                found_user_id = int(parts[1])
                found_quiz_id = int(parts[2])

                if quiz_id is None:
                    found_quiz = await self.get_quiz_by_id(found_quiz_id)
                    if not found_quiz or found_quiz.company_id != company_id:
                        continue

                progress = await self.get_quiz_progress(redis, found_user_id, found_quiz_id)
                for q_id, ans_data in progress.items():
                    export_results.append({
                        "user_id": found_user_id,
                        "quiz_id": found_quiz_id,
                        "question_id": q_id,
                        "answer_id": ans_data
                    })
            return export_results


    async def get_company_quizzes_export(self, redis: Redis, current_user: User, company_id: int,
                                             user_id: int = None, quiz_id: int = None) -> list[dict]:
            await self._validate_company_export_access(company_id, current_user.id, user_id)

            return await self._fetch_export_data_from_redis(redis, company_id, user_id, quiz_id)

