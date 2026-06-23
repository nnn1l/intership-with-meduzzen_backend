from typing import List

from fastapi import APIRouter, status
from fastapi.params import Depends, Query
from watchfiles import awatch

from ..schemas.quiz import QuizResponse, QuizCreate, QuizUpdate, QuizResultResponse, QuizSubmit
from ..services.quiz import QuizService
from ..utils.dependencies import get_current_user, get_quiz_service
from ..models.user import User

router = APIRouter()

@router.post('/{company_id}', status_code=status.HTTP_201_CREATED, response_model=QuizResponse)
async def create_quiz(quiz_data: QuizCreate,
                      company_id: int,
                      service: QuizService = Depends(get_quiz_service),
                      current_user: User = Depends(get_current_user)):
    return await service.create_quiz(quiz_data, company_id, current_user)

@router.get('/{quiz_id}', response_model=QuizResponse)
async def get_quiz_by_id(quiz_id: int,
                         service: QuizService = Depends(get_quiz_service)):
    return await service.get_quiz_by_id(quiz_id)

@router.get('/quizzes', response_model=List[QuizResponse])
async def get_quizzes(limit: int = Query(default=10, ge=1, le=100),
                      offset: int = Query(default=0, ge=0),
                      service: QuizService = Depends(get_quiz_service)):
    return await service.get_quizzes(limit, offset)

@router.patch('/{quiz_id}', response_model=QuizResponse)
async def update_quiz(quiz_id: int,
                      quiz_data: QuizUpdate,
                      service: QuizService = Depends(get_quiz_service),
                      current_user: User = Depends(get_current_user)):
    return await service.update_quiz(quiz_id, quiz_data, current_user)

@router.delete('/{quiz_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_quiz(quiz_id: int,
                      service: QuizService = Depends(get_quiz_service),
                      current_user: User = Depends(get_current_user)):
    return await service.delete_quiz(quiz_id, current_user)

@router.post('/{quiz_id}', response_model=QuizResultResponse, status_code=status.HTTP_201_CREATED)
async def create_quiz_attempt(quiz_id: int,
                              answers: QuizSubmit,
                              service: QuizService = Depends(get_quiz_service),
                              current_user: User = Depends(get_current_user)):
    return await service.create_quiz_attempt(quiz_id, answers, current_user)

@router.get('/{company_id}/{user_id}/analytics', response_model=float)
async def get_user_analytics_in_company(user_id: int,
                                        company_id: int,
                                        service: QuizService = Depends(get_quiz_service)):
    return await service.get_user_analytics_in_company(user_id, company_id)

@router.get('/{user_id}/analytics', response_model=float)
async def get_user_analytics_global(user_id: int,
                                    service: QuizService = Depends(get_quiz_service)):
    return await service.get_user_analytics_global(user_id)