import pandas
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Quiz, Question, AnswerOption
from ..repositories.base import add_to_db, do_flush, do_commit, refresh_data_in_db
from ..repositories.quiz import get_quiz_by_title_and_company
from ..schemas.quiz import QuizResponse


class ExcelImportService:
    def __init__(self, db: AsyncSession):
        self.db = db


    async def import_quizzes_from_excel(self, file: UploadFile, company_id: int) -> list[QuizResponse]:
        if not file.filename.endswith('.xlsx' and '.xls'):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Incorrect file format. Expected Excel file (.xlsx or .xls)')

        try:
            df = pandas.read_excel(file.file)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f'Error during reading Excel: {str(e)}')

        # substitute all NaN with None
        df = df.where(pandas.notnull(df), None)

        grouped_by_quiz = df.groupby(['quiz_title', 'quiz_description', 'max_attempts'])
        processed_quizzes = []

        for (quiz_title, quiz_description, max_attempts), quiz_group in grouped_by_quiz:
            existing_quiz = await get_quiz_by_title_and_company(quiz_title, company_id, self.db)

            if existing_quiz:
                existing_quiz.description = quiz_description
                existing_quiz.max_attempts = int(max_attempts)if max_attempts is not None else 0
                quiz = existing_quiz

                existing_quiz.questions.clear()
            else:
                quiz = Quiz(
                    title=quiz_title,
                    description=quiz_description,
                    company_id=company_id,
                    max_attempts=int(max_attempts) if max_attempts is not None else 0)

                await add_to_db(quiz, self.db)
                await do_flush(self.db)
                processed_quizzes.append(quiz)

            grouped_by_question = quiz_group.groupby('question_title')

            for question_title, question_group in grouped_by_question:
                question = Question(
                    title = question_title,
                    quiz_id = quiz.id)
                await add_to_db(question, self.db)
                await do_flush(self.db)

                for _, row in question_group.iterrows():
                    answer_option = AnswerOption(
                        answer = str(row['answer_text']),
                        is_correct = bool(row['is_correct']),
                        question_id = question.id)
                    await add_to_db(answer_option, self.db)

        await do_commit(self.db)
        for quiz in processed_quizzes:
            await refresh_data_in_db(quiz, self.db)

        return [QuizResponse.model_validate(quiz) for quiz in processed_quizzes]
