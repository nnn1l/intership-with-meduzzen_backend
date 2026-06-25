from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional
from ..utils.enums import VisibilityStatus

class CompanyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    visibility: VisibilityStatus = VisibilityStatus.VISIBLE_TO_ALL

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class CompanyResponse(BaseModel):
    id: int
    owner_id: int
    name: str
    description: str | None
    visibility: VisibilityStatus

    model_config = ConfigDict(from_attributes = True)

class CompanyMemberResponse(BaseModel):
    id: int
    username: str
    description: str | None
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)

class CompanyVisibilityResponse(BaseModel):
    visibility: VisibilityStatus
