from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class UserGlobalAnalyticsResponse(BaseModel):
    global_score: float

class UserQuizPeriodAnalyticsResponse(BaseModel):
    quiz_id: int
    score: float
    total_correct: int
    total_questions: int

    model_config = ConfigDict(from_attributes = True)

class UserLastCompletionResponse(BaseModel):
    quiz_id: int
    last_completed_at: datetime

    model_config = ConfigDict(from_attributes = True)

class CompanyMemberQuizTrendsResponse(BaseModel):
    quiz_id: int
    week: Optional[str] = None
    score: float

    model_config = ConfigDict(from_attributes = True)

class CompanyOverallDynamicsResponse(BaseModel):
    week: Optional[str] = None
    company_members_score: float

    model_config = ConfigDict(from_attributes = True)

class CompanyMemberLastAttemptResponse(BaseModel):
    user_id: int
    quiz_id: Optional[int] = None
    last_completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes = True)
