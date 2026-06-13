from typing import List

from fastapi import APIRouter, status
from fastapi.params import Depends

from ..schemas.invitation import InvitationCreate, JoinRequestCreate, MembershipResponse
from ..utils.dependencies import get_invitation_service, get_current_user
from ..services.invitation import InvitationService
from ..models.user import User

router = APIRouter()

@router.post('/{company_id}/invitations', response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(company_id: int,
                            invitation_data: InvitationCreate,
                            service: InvitationService = Depends(get_invitation_service),
                            current_user: User = Depends(get_current_user)):
    return await service.invitation_create(invitation_data, company_id, current_user)

@router.post('/{company_id}/invitations', response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
async def create_join_request(company_id: int,
                            request_data: JoinRequestCreate,
                            service: InvitationService = Depends(get_invitation_service),
                            current_user: User = Depends(get_current_user)):
    return await service.request_create(request_data, company_id, current_user)

@router.patch('/invitations/{invitation_id}/accept', response_model=MembershipResponse)
async def accept_invitation(invitation_id: int,
                            service: InvitationService = Depends(get_invitation_service),
                            current_user: User = Depends(get_current_user)):
    return await service.accept_invitation(invitation_id, current_user)

@router.patch('/requests/{request_id}/accept', response_model=MembershipResponse)
async def accept_request(request_id: int,
                            service: InvitationService = Depends(get_invitation_service),
                            current_user: User = Depends(get_current_user)):
    return await service.accept_join_request(request_id, current_user)

@router.patch('/invitations/{invitation_id}/decline', response_model=MembershipResponse)
async def decline_invitation(invitation_id: int,
                            service: InvitationService = Depends(get_invitation_service),
                            current_user: User = Depends(get_current_user)):
    return await service.decline_invitation(invitation_id, current_user)

@router.patch('/requests/{request_id}/decline', response_model=MembershipResponse)
async def decline_request(request_id: int,
                            service: InvitationService = Depends(get_invitation_service),
                            current_user: User = Depends(get_current_user)):
    return await service.decline_join_request(request_id, current_user)

@router.get("/my/requests", response_model=List[MembershipResponse])
async def get_my_sent_requests(limit: int = 10,
                                offset: int = 0,
                                current_user: User = Depends(get_current_user),
                                service: InvitationService = Depends(get_invitation_service)):
    return await service.get_user_sent_requests(current_user, limit, offset)

@router.get("/my/invitations", response_model=List[MembershipResponse])
async def get_my_received_invitations(limit: int = 10,
                                    offset: int = 0,
                                    current_user: User = Depends(get_current_user),
                                    service: InvitationService = Depends(get_invitation_service)):
    return await service.get_user_received_invitations(current_user, limit, offset)

@router.get("/{company_id}/invited-users", response_model=List[MembershipResponse])
async def get_company_invited_users(company_id: int,
                                    limit: int = 10,
                                    offset: int = 0,
                                    current_user: User = Depends(get_current_user),
                                    service: InvitationService = Depends(get_invitation_service)):
    return await service.get_owner_sent_invitations(company_id, current_user, limit, offset)

@router.get("/{company_id}/pending-requests", response_model=List[MembershipResponse])
async def get_company_pending_join_requests(company_id: int,
                                            limit: int = 10,
                                            offset: int = 0,
                                            current_user: User = Depends(get_current_user),
                                            service: InvitationService = Depends(get_invitation_service)):
    return await service.get_company_pending_requests(company_id, current_user, limit, offset)




