from sqlalchemy import String
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from ..models import Base

if TYPE_CHECKING:
    from .company import Company, company_members
    from .invitation import MembershipManagement
    from .quiz import QuizAttempt

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    username: Mapped[str] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(String(300))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    owned_companies: Mapped[List["Company"]] = relationship(back_populates='owner')
    companies: Mapped[List['Company']] = relationship(secondary='company_members', back_populates='members')
    memberships: Mapped[List['MembershipManagement']] = relationship(back_populates='user', cascade="all, delete-orphan")
    quiz_attempts: Mapped[List['QuizAttempt']] = relationship(back_populates='user', cascade="all, delete-orphan")