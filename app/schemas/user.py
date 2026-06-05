from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserSignUp(UserBase):
    password: str

class UserSignIn(UserBase):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[str] = None
    password: Optional[str] = None

class UserSchema(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserDetailResponse(BaseModel):
    username: str
    description: str
    created_at: datetime

    class Config:
        from_attributes = True

class UsersListResponse(BaseModel):
    users: List[UserSchema]
    total: int
