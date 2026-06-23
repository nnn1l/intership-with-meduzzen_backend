import io
import json
from typing import List

from fastapi import APIRouter, status, HTTPException
from fastapi.params import Depends, Query
from redis.asyncio import Redis
from starlette.responses import StreamingResponse

from ..redis_client import get_redis
from ..schemas.quiz import QuizResponse, QuizCreate, QuizUpdate, QuizResultResponse, QuizSubmit, UserAnswerSubmit
from ..services.quiz import QuizService
from ..utils.csv import conver_to_csv
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
                              current_user: User = Depends(get_current_user),
                              redis: Redis = Depends(get_redis)):
    return await service.create_quiz_attempt(quiz_id, answers, current_user, redis)

@router.put('/{quiz_id}/answers', status_code=status.HTTP_200_OK)
async def save_interim_answer(quiz_id: int,
                               answer_data: UserAnswerSubmit,
                               service: QuizService = Depends(get_quiz_service),
                               redis: Redis = Depends(get_redis),
                               current_user: User = Depends(get_current_user)):
    await service.save_question_progress(
        redis=redis,
        quiz_id=quiz_id,
        user_id=current_user.id,
        answer_data=answer_data
    )
    return {'status': 'success', 'detail': {'Answer cached in Redis'}}

@router.get("/{company_id}-quizzes-results", response_class=StreamingResponse)
async def company_quizzes_export(company_id: int,
                                        user_id: int = None,
                                        quiz_id: int = None,
                                        redis: Redis = Depends(get_redis),
                                        current_user: User = Depends(get_current_user),
                                        service: QuizService = Depends(get_quiz_service),
                                        format_: str = Query("json", pattern="^(json|csv)$")):
    export_data = await service.get_company_quizzes_export(
        redis=redis,
        current_user=current_user,
        company_id=company_id,
        user_id=user_id,
        quiz_id=quiz_id
    )

    if not export_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No found results for export by chosen filters")

    if format_ == "csv":
        csv_string = await conver_to_csv(export_data)

        file_stream = io.BytesIO(csv_string.encode("utf-8"))

        return StreamingResponse(
            file_stream,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=company_{company_id}_export.csv"}
        )

    json_string = json.dumps(export_data, indent=4, ensure_ascii=False)
    file_stream = io.BytesIO(json_string.encode("utf-8"))
    return StreamingResponse(
        file_stream,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=company_{company_id}_export.json"}
    )

@router.get("/my-results", response_class=StreamingResponse)
async def user_personal_quizzes_export(user_id: int = None,
                                        quiz_id: int = None,
                                        redis: Redis = Depends(get_redis),
                                        current_user: User = Depends(get_current_user),
                                        service: QuizService = Depends(get_quiz_service),
                                        format_: str = Query("json", pattern="^(json|csv)$")):
    export_data = await service.get_user_personal_quizzes_export(
        redis=redis,
        current_user=current_user,
        quiz_id=quiz_id
    )

    if not export_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No found results for export by chosen filters")

    if format_ == "csv":
        csv_string = await conver_to_csv(export_data)

        file_stream = io.BytesIO(csv_string.encode("utf-8"))

        return StreamingResponse(
            file_stream,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=user_{current_user.id}_export.csv"}
        )

    json_string = json.dumps(export_data, indent=4, ensure_ascii=False)
    file_stream = io.BytesIO(json_string.encode("utf-8"))
    return StreamingResponse(
        file_stream,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=user_{current_user.id}_export.json"}
    )
