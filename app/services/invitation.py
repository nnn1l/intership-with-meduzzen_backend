from typing import TYPE_CHECKING

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from ..models.company import company_members
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
        await self._check_already_member(company_id, current_user.id)

        # ensuring if there is no invites sent to this user from a company
        await self._check_pending_request(company_id, current_user.id)

        new_invitation = MembershipManagement(
            company_id = company_id,
            user_id = invitation_data.user_id,
            type = InvitationType.INVITATION,
            status = Status.PENDING)

        self.db.add(new_invitation)
        await self.db.commit()
        await self.db.refresh(new_invitation)
        logger.info(f"Invitation with ID {new_invitation.id} successfully created")
        return new_invitation


    # CREATE JOIN REQUEST
    async def create_join_request(self, request_data: JoinRequestCreate, company_id: int, current_user: User) -> MembershipManagement:
        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(company_id)  # ensuring if company exists & get company

        # ensuring if current user isn't owner of a company
        if company.owner_id == current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You're an owner of this company")

        # ensuring if user isn't a member of a company
        await self._check_already_member(company_id, current_user.id)

        # ensuring if there is no invites sent to this user from a company
        await self._check_pending_request(company_id, current_user.id)

        new_request = MembershipManagement(
            company_id=company_id,
            user_id=request_data.user_id,
            type=InvitationType.REQUEST,
            status=Status.PENDING)

        self.db.add(new_request)
        await self.db.commit()
        await self.db.refresh(new_request)
        logger.info(f"Invitation with ID {new_request.id} successfully created")
        return new_request


    # CHECK IF USER IS A MEMBER OF A COMPANY ALREADY
    async def _check_already_member(self, company_id: int, user_id: int):
        member_status = select(company_members).where(
            and_(
                company_members.c.company_id == company_id,
                company_members.c.user_id == user_id))

        member_result = await self.db.execute(member_status)
        if member_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You can't send invite or join request if user's a member of this company already")


    # CHECK IF PEND REQUEST IS SENT ALREADY
    async def _check_pending_request(self, company_id: int, user_id: int):
        pending_status = select(MembershipManagement).where(
            and_(
                MembershipManagement.company_id == company_id,
                MembershipManagement.user_id == user_id,
                MembershipManagement.status == Status.PENDING))

        pending_result = await self.db.execute(pending_status)
        if pending_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You have already sent a join request or invitation")


    # GET INVITATION OR JOIN REQUEST BY ID
    async def get_membership_management_by_id(self, invite_id: int) -> MembershipManagement:
        query = select(MembershipManagement).where(MembershipManagement.id == invite_id)
        result = await self.db.execute(query)
        invitation = result.scalar_one_or_none()

        if not invitation:
            logger.error(f"Invitation or join request with ID {invite_id} wasn't found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Invitation or join request with this ID doesn't exist")

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

        insert_user = company_members.insert().values(
            user_id=current_user.id,
            company_id=invitation.company_id)
        await self.db.execute(insert_user)
        await self.db.commit()
        await self.db.refresh(invitation)
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
        insert_user = company_members.insert().values(
            user_id=current_user.id,
            company_id=request.company_id)
        await self.db.execute(insert_user)
        await self.db.commit()
        await self.db.refresh(request)
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

        await self.db.delete(record)
        await self.db.commit()
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
        await self.db.commit()
        await self.db.refresh(invitation)
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
        await self.db.commit()
        await self.db.refresh(request)
        logger.info(f"Join request with ID {request_id} declined")
        return request


    # GET USER'S SENT REQUESTS
    async def get_user_sent_requests(self, current_user: User, limit: int, offset: int):
        requests = (select(MembershipManagement).where(
                and_(
                    MembershipManagement.user_id == current_user.id,
                    MembershipManagement.type == InvitationType.REQUEST))
            .limit(limit)
            .offset(offset))

        result = await self.db.execute(requests)
        return result.scalars().all()


    # GET USER'S RECEIVED INVITATIONS
    async def get_user_received_invitations(self, current_user: User, limit: int, offset: int):
        invitations = (select(MembershipManagement).where(
                and_(
                    MembershipManagement.user_id == current_user.id,
                    MembershipManagement.type == InvitationType.INVITATION))
            .limit(limit)
            .offset(offset))

        result = await self.db.execute(invitations)
        return result.scalars().all()


    # COMPANY'S INVITED USERS
    async def get_owner_sent_invitations(self, company_id: int, current_user: User, limit: int, offset: int):
        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(company_id)

        if company.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only the company owner can view this list")

        invitations = (select(MembershipManagement).where(
                and_(
                    MembershipManagement.company_id == company_id,
                    MembershipManagement.type == InvitationType.INVITATION))
            .limit(limit)
            .offset(offset))

        result = await self.db.execute(invitations)
        return result.scalars().all()


    # COMPANY'S PENDING REQUESTS
    async def get_company_pending_requests(self, company_id: int, current_user: User, limit: int, offset: int):
        company_service = CompanyService(self.db)
        company = await company_service.get_company_by_id(company_id)

        if company.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only the company owner can view this list")

        requests = (select(MembershipManagement).where(
                and_(
                    MembershipManagement.company_id == company_id,
                    MembershipManagement.type == InvitationType.REQUEST,
                    MembershipManagement.status == Status.PENDING))
            .limit(limit)
            .offset(offset))

        result = await self.db.execute(requests)
        return result.scalars().all()

