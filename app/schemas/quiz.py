from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List


class AnswerCreate(BaseModel):
    answer: str
    is_correct: bool

class AnswerUpdate(BaseModel):
    id: int
    answer: Optional[str] = None
    is_correct: Optional[bool] = None

class AnswerResponse(BaseModel):
    id: int
    question_id: int
    answer: str
    is_correct: bool

    model_config = ConfigDict(from_attributes=True)


class QuestionCreate(BaseModel):
    title: str
    answers: List[AnswerCreate]

    @classmethod
    @field_validator("answers")
    def validate_answers_count(cls, a: List[AnswerCreate]):
        if not (2 <= len(a) <= 4):
            raise ValueError("Each question must have from 2 to 4 answer options")

        if not any(answer.is_correct for answer in a):
            raise ValueError("Each question must have at least 1 correct answer")

        return a

class QuestionUpdate(BaseModel):
    id: int
    title: Optional[str] = None
    answers: Optional[List[AnswerUpdate]] = None

    @classmethod
    @field_validator("answers")
    def validate_answers_count(cls, a: Optional[List[AnswerCreate]]):
        if a is None:
            return a

        if not (2 <= len(a) <= 4):
            raise ValueError("Each question must have from 2 to 4 answer options")

        if not any(answer.is_correct for answer in a):
            raise ValueError("Each question must have at least 1 correct answer")

        return a

class QuestionResponse(BaseModel):
    id: int
    quiz_id: int
    title: str
    answers: List[AnswerResponse]

    model_config = ConfigDict(from_attributes=True)


class QuizCreate(BaseModel):
    title: str
    description: Optional[str] = None
    max_attempts: Optional[int] = 0
    questions: List[QuestionCreate]

    @classmethod
    @field_validator("questions")
    def validate_patch_questions(cls, q: List[QuestionCreate]):

        if len(q) < 2:
            raise ValueError("Each quiz must have more than 1 question")

        return q

class QuizUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    max_attempts: Optional[int] = None
    questions: Optional[List[QuestionUpdate]] = None

    @classmethod
    @field_validator("questions")
    def validate_patch_questions(cls, q: Optional[List[QuestionUpdate]]):
        if q is None:
            return q

        if len(q) < 2:
            raise ValueError("Each quiz must have more than 1 question")

        return q

class QuizResponse(BaseModel):
    id: int
    company_id: int
    title: str
    description: str | None
    max_attempts: int
    questions: List[QuestionResponse]

    model_config = ConfigDict(from_attributes=True)