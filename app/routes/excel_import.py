from typing import List

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.quiz import QuizResponse
from app.services.excel_import import ExcelImportService
from app.utils.dependencies import get_excel_import_service

router = APIRouter()

@router.post("/quizzes", response_model=List[QuizResponse])
async def import_quizzes(company_id: int,
                         file: UploadFile = File(),
                         service: ExcelImportService = Depends(get_excel_import_service)):
    return await service.import_quizzes_from_excel(file, company_id)