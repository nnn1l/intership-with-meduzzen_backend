from datetime import datetime

from pydantic import BaseModel, ConfigDict
from ..utils.enums import Status, InvitationType

class InvitationCreate(BaseModel):
    user_id: int

class JoinRequestCreate(BaseModel):
    company_id: int

class MembershipStatusUpdate(BaseModel):
    status: Status

class MembershipResponse(BaseModel):
    id: int

    type: InvitationType
    status: Status

    user_id: int
    company_id: int

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)