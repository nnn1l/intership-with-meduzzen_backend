from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum, ForeignKey
from ..models import Base
from ..utils.enums import InvitationType, Status

if TYPE_CHECKING:
    from .user import User
    from .company import Company

class MembershipManagement(Base):
    __tablename__ = 'membership_managements'

    id: Mapped[int] = mapped_column(primary_key=True)

    type: Mapped[InvitationType] = mapped_column(Enum(InvitationType))
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.PENDING)

    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"))
    user: Mapped['User'] = relationship(back_populates='memberships')

    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id', ondelete="CASCADE"))
    company: Mapped['Company'] = relationship(back_populates='memberships')

    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

