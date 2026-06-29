from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import String, ForeignKey, Integer, Boolean, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(80))
    description: Mapped[Optional[str]] = mapped_column(String(500))
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))

    max_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=True) # if max attempts = 0 -> infinity attempts

    questions: Mapped[List['Question']] = relationship(back_populates='quiz', cascade="all, delete-orphan")
    quiz_attempts: Mapped[List['QuizAttempt']] = relationship(back_populates='quiz', cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(400))
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"))

    answers: Mapped[List['AnswerOption']] = relationship(back_populates="question", cascade="all, delete-orphan")


class AnswerOption(Base):
    __tablename__ = "answer_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    answer: Mapped[str] = mapped_column(String(100), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean)

    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    question: Mapped['Question'] = relationship(back_populates='answer_option')


class QuizAttempt(Base):
    __tablename__ = "quiz_attempt"

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey('quizzes.id', ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"))
    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id', ondelete="CASCADE"))

    score: Mapped[float] = mapped_column(Float, default=0.0) # score in %
    total_questions: Mapped[int] = mapped_column(Integer)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    user = relationship("User", back_populates="quiz_attempts")
    quiz = relationship("Quiz", back_populates="quiz_attempts")
