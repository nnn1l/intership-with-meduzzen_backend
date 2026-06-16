from typing import List

from fastapi import APIRouter, status
from fastapi.params import Depends, Query

from ..schemas.quiz import QuizResponse, QuizCreate, QuizUpdate
from ..services.quiz import QuizService
from ..utils.dependencies import get_current_user, get_quiz_service
from ..models.user import User

router = APIRouter()

@router.post('/{company_id}/create_quiz/', status_code=status.HTTP_201_CREATED, response_model=QuizResponse)
async def create_quiz(quiz_data: QuizCreate,
                      company_id: int,
                      service: QuizService = Depends(get_quiz_service),
                      current_user: User = Depends(get_current_user)):
    return await service.create_quiz(quiz_data, company_id, current_user)

@router.get('/{quiz_id}', response_model=QuizResponse)
async def get_quiz_by_id(quiz_id: int,
                         service: QuizService = Depends(get_quiz_service)):
    return await service.get_quiz_by_id(quiz_id)

@router.get('/multi', response_model=List[QuizResponse])
async def get_quizzes(limit: int = Query(default=10, ge=1, le=100),
                      offset: int = Query(default=0, ge=0),
                      service: QuizService = Depends(get_quiz_service)):
    return await service.get_quizzes(limit, offset)

@router.patch('/{quiz_id}/update', response_model=QuizResponse)
async def update_quiz(quiz_id: int,
                      quiz_data: QuizUpdate,
                      service: QuizService = Depends(get_quiz_service),
                      current_user: User = Depends(get_current_user)):
    return await service.update_quiz(quiz_id, quiz_data, current_user)

@router.delete('/{quiz_id}/delete', status_code=status.HTTP_204_NO_CONTENT)
async def delete_quiz(quiz_id: int,
                      service: QuizService = Depends(get_quiz_service),
                      current_user: User = Depends(get_current_user)):
    return await service.delete_quiz(quiz_id, current_user)