from typing import Optional, List

from .base import Base
from sqlalchemy import String, ForeignKey, Integer, Boolean, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(80))
    description: Mapped[Optional[str]] = mapped_column(String(500))
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))

    max_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=True) # if max attempts = 0 -> infinity attempts

    questions: Mapped[List['Question']] = relationship(back_populates='quiz', cascade="all, delete-orphan")


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


quiz_attempts = Table("quiz_attempts",
                      Base.metadata,
                      Column("user_id", ForeignKey("users.id", ondelete='CASCADE'), primary_key=True),
                      Column("quiz_id", ForeignKey("quizzes.id", ondelete="CASCADE"), primary_key=True),
                      Column("attempts", Integer, default=0))