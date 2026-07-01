from typing import Optional, TYPE_CHECKING, List

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Enum, Table, Column, Boolean
from ..models import Base
from ..utils.enums import VisibilityStatus

if TYPE_CHECKING:
    from .user import User
    from .invitation import MembershipManagement


company_members = Table(
    "company_members",
    Base.metadata,
    Column("user_id", ForeignKey('users.id', ondelete="CASCADE"), primary_key=True),
    Column("company_id", ForeignKey('companies.id', ondelete="CASCADE"), primary_key=True),
    Column("is_admin", Boolean, default=False)
)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(330))

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    owner: Mapped['User'] = relationship(back_populates="companies")

    members: Mapped[List['User']] = relationship( secondary=company_members, back_populates='companies')
    memberships: Mapped[List['MembershipManagement']] = relationship(back_populates='company',
                                                                     cascade="all, delete-orphan")

    visibility: Mapped[VisibilityStatus] = mapped_column(Enum(VisibilityStatus), default=VisibilityStatus.VISIBLE_TO_ALL)