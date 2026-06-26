from typing import List

from fastapi import APIRouter, status
from fastapi.params import Depends, Query

from ..schemas.company import CompanyResponse, CompanyCreate, CompanyUpdate, CompanyMemberResponse, \
    CompanyVisibilityResponse
from ..services.company import CompanyService
from ..utils.dependencies import get_company_service, get_current_user
from ..models.user import User

router = APIRouter()

@router.post('/', response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(company_data: CompanyCreate,
                        service: CompanyService = Depends(get_company_service),
                        current_user: User = Depends(get_current_user)):
    return await service.create_company(company_data, current_user.id)


@router.get('/{company_id}', response_model=CompanyResponse)
async def get_company_by_id(company_id: int,
                            service: CompanyService = Depends(get_company_service),):
    return await service.get_company_by_id(company_id)

@router.get('/companies', response_model=List[CompanyResponse])
async def get_companies(limit: int = Query(default=10, ge=1, le=100),
                        offset: int = Query(default=0, ge=0),
                        service: CompanyService = Depends(get_company_service)):
    return await service.get_companies(limit, offset)

@router.patch('/{company_id}', response_model=CompanyResponse)
async def update_company(company_id: int,
                         company_data: CompanyUpdate,
                         service: CompanyService = Depends(get_company_service),
                         current_user: User = Depends(get_current_user)):

    return await service.update_company(company_id, company_data, current_user.id)

@router.delete('/{company_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(company_id: int,
                         service: CompanyService = Depends(get_company_service),
                         current_user: User = Depends(get_current_user)):
    await service.delete_company(company_id, current_user.id)

@router.patch('/{company_id}/toggle-visibility', response_model=CompanyVisibilityResponse)
async def change_company_visibility(company_id: int,
                                    service: CompanyService = Depends(get_company_service),
                                    current_user: User = Depends(get_current_user)):
    return await service.change_company_visibility(company_id, current_user.id)

@router.delete('/{company_id}/members/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
async def fire_user_from_company(company_id: int,
                                 user_id: int,
                                 current_user: User = Depends(get_current_user),
                                 service: CompanyService = Depends(get_company_service)):
    return await service.fire_user_from_company(company_id, user_id, current_user)

@router.delete('/{company_id}/members/{current_user.id}', status_code=status.HTTP_204_NO_CONTENT)
async def leave_company(company_id: int,
                        service: CompanyService = Depends(get_company_service),
                        current_user: User = Depends(get_current_user)):
    return await service.leave_company(company_id,current_user)

@router.get('/{company_id}/members', response_model=List[CompanyMemberResponse])
async def get_company_members(company_id: int,
                              limit: int = 10,
                              offset: int = 0,
                              service: CompanyService = Depends(get_company_service)):
    return await service.get_company_members(company_id, limit, offset)

@router.patch('/{company_id}/members/{user_id}/appoint-role', response_model=CompanyMemberResponse)
async def appoint_admin(company_id: int,
                        user_id: int,
                        service: CompanyService = Depends(get_company_service),
                        current_user: User = Depends(get_current_user)):
    return await service.appoint_admin(company_id, user_id, current_user)

@router.patch('/{company_id}/members/{user_id}/decline-role', response_model=CompanyMemberResponse)
async def decline_admin_role(company_id: int,
                        user_id: int,
                        service: CompanyService = Depends(get_company_service),
                        current_user: User = Depends(get_current_user)):
    return await service.decline_admin_role(company_id, user_id, current_user)

@router.get('/{company_id}/administration', response_model=List[CompanyMemberResponse])
async def get_administration(company_id: int,
                             service: CompanyService = Depends(get_company_service)):
    return await service.get_company_administration(company_id)


