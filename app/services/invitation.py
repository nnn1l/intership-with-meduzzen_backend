from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from ..models.company import company_members
from ..repositories.base import add_to_db, get_by_filter, delete_from_db, refresh_data_in_db, insert_table_record
from ..repositories.company import is_user_member_of_company
from ..repositories.invitation import check_pending_request
from ..schemas.invitation import InvitationCreate, JoinRequestCreate
from ..models.user import User
from ..models.invitation import MembershipManagement
from ..logger import logger
from ..utils.enums import Status, InvitationType

if TYPE_CHECKING:
    from .company import CompanyService
    from .user import UserService

class InvitationService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session


    # CREATE INVITATION
    async def invitation_create(self, invitation_data: InvitationCreate, company_id: int, current_user: User) -> MembershipManagement:
        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(company_id) # ensuring if company exists & get company

        # ensuring if current user is owner of a company
        if company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You don't have permissions to send invitation from this company")

        user_service = UserService(self.db)
        invited_user = await user_service.get_user_by_id(invitation_data.user_id) # ensuring if invited user exists & get this user

        # ensuring if current user doesn't invite itself
        if invited_user == current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't invite yourself")

        # ensuring if user isn't a member of a company
        is_member = await is_user_member_of_company(invitation_data.user_id, company_id, self.db)
        if is_member:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't invite user if user's a member of your company")

        # ensuring if there is no invites sent to this user from a company
        pending = await check_pending_request(company_id, invitation_data.user_id, self.db)
        if pending:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't send invites twice")

        try:
            new_invitation = MembershipManagement(
                company_id = company_id,
                user_id = invitation_data.user_id,
                type = InvitationType.INVITATION,
                status = Status.PENDING)

            await add_to_db(new_invitation)
            logger.info(f"Invitation with ID {new_invitation.id} successfully created")
            return new_invitation
        except Exception as e:
            logger.error('Error appeared during creating an invitation')
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f"Internal server error during invitation creating: {str(e)}")


    # CREATE JOIN REQUEST
    async def create_join_request(self, request_data: JoinRequestCreate, current_user: User) -> MembershipManagement:
        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(request_data.company_id)  # ensuring if company exists & get company

        # ensuring if user isn't a member of a company
        is_member = await is_user_member_of_company(current_user.id, company.id, self.db)
        if is_member:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail="You can't invite user if user's a member of your company")

        # ensuring if there is no join requests sent to this company from a user
        pending = await check_pending_request(company.id, current_user.id, self.db)
        if pending:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail="You can't send invites twice")

        try:
            new_request = MembershipManagement(
                company_id=request_data.company_id,
                user_id=current_user.id,
                type=InvitationType.REQUEST,
                status=Status.PENDING)

            await add_to_db(new_request)
            logger.info(f"Invitation with ID {new_request.id} successfully created")
            return new_request

        except Exception as e:
            logger.error('Error appeared during creating a join request')
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f"Internal server error during join request creating: {str(e)}")


    # GET INVITATION OR JOIN REQUEST BY ID
    async def get_membership_management_by_id(self, m_id: int) -> MembershipManagement:
        invitation = await get_by_filter(MembershipManagement, self.db, id=m_id)

        if not invitation:
            logger.error(f"Invitation or join request with ID {m_id} wasn't found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Invitation or join request with ID {m_id} doesn't exist")

        return invitation


    # ACCEPT INVITATION
    async def accept_invitation(self, invitation_id: int, current_user: User) -> MembershipManagement:
        invitation = await self.get_membership_management_by_id(invitation_id)

        if invitation.type != InvitationType.INVITATION or invitation.status != Status.PENDING:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                detail="This membership management record can't be accepted")

        if invitation.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You don't have permission to accept invitation")

        invitation.status = Status.ACCEPTED

        await insert_table_record(company_members, {"user_id": current_user.id, "company_id": invitation.company_id} , self.db)
        await refresh_data_in_db(invitation)
        logger.info(f"Invitation with ID {invitation_id} accepted")
        return invitation


    # ACCEPT JOIN REQUEST
    async def accept_join_request(self, request_id: int, current_user: User) -> MembershipManagement:
        request = await self.get_membership_management_by_id(request_id)

        if request.type != InvitationType.REQUEST or request.status != Status.PENDING:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="This membership management record can't be accepted")

        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(request.company_id)

        if company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You don't have permission to accept join request")

        request.status = Status.ACCEPTED
        await insert_table_record(company_members, {"company_id_id": request.company_id, "user_id": request.user_id})
        await refresh_data_in_db(request)
        logger.info(f"Join request with ID {request_id} accepted")
        return request


    # DELETE INVITE/JOIN REQUEST
    async def delete_membership_record(self, record_id: int, current_user: User) -> bool:
        record = await self.get_membership_management_by_id(record_id)

        if record.status != Status.PENDING:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                detail="You can't delete invitation or join request if they're accepted or declined")

        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(record.company_id)

        if record.type == InvitationType.INVITATION and company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete invitation")

        if record.type == InvitationType.REQUEST and current_user.id != record.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permissions to delete requests that don't belong to you")

        await delete_from_db(record, self.db)
        logger.info(f"The {str(record.type)} with ID {record.id} deleted successfully")
        return True


    # DECLINE INVITATION
    async def decline_invitation(self, invitation_id: int, current_user: User) -> MembershipManagement:
        invitation = await self.get_membership_management_by_id(invitation_id)

        if invitation.type != InvitationType.INVITATION or invitation.status != Status.PENDING:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                detail="This membership management record can't be declined")

        if invitation.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You don't have permission to decline invitation")

        invitation.status = Status.DECLINED
        await refresh_data_in_db(invitation, self.db)
        logger.info(f"Invitation with ID {invitation_id} declined")
        return invitation


    # DECLINE JOIN REQUEST
    async def decline_join_request(self, request_id: int, current_user: User) -> MembershipManagement:
        request = await self.get_membership_management_by_id(request_id)

        if request.type != InvitationType.REQUEST or request.status != Status.PENDING:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="This membership management record can't be declined")

        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(request.company_id)

        if company.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You don't have permission to decline join request")

        request.status = Status.DECLINED
        await refresh_data_in_db(request, self.db)
        logger.info(f"Join request with ID {request_id} declined")
        return request


    # GET USER'S SENT REQUESTS
    async def get_user_sent_requests(self, current_user: User):
        requests = await get_by_filter(MembershipManagement, self.db, user_id=current_user.id, type=InvitationType.REQUEST)

        return requests


    # GET USER'S RECEIVED INVITATIONS
    async def get_user_received_invitations(self, current_user: User):
        invitations = get_by_filter(MembershipManagement, self.db, user_id=current_user.id, type=InvitationType.INVITATION)

        return invitations


    # COMPANY'S INVITED USERS
    async def get_owner_sent_invitations(self, company_id: int, current_user: User):
        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(company_id)

        if company.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only the company owner can view this list")

        invitations = await get_by_filter(MembershipManagement, self.db, company_id=company_id, type=InvitationType.INVITATION)

        return invitations


    # COMPANY'S PENDING REQUESTS
    async def get_company_pending_requests(self, company_id: int, current_user: User):
        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(company_id)

        if company.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only the company owner can view this list")

        invitations = await get_by_filter(MembershipManagement, self.db, company_id=company_id, type=InvitationType.REQUEST, status=Status.PENDING)
        return invitations

