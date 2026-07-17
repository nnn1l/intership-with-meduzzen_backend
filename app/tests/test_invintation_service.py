import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException, status

from app.schemas.invitation import InvitationCreate, JoinRequestCreate
from app.services.invitation import InvitationService
from app.utils.enums import Status, InvitationType


pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db_session():
    return MagicMock()


@pytest.fixture
def invitation_service(mock_db_session):
    return InvitationService(db_session=mock_db_session)


async def test_invitation_create_success(invitation_service, mocker):
    current_user = MagicMock()
    current_user.id = 1

    fake_company = MagicMock()
    fake_company.owner_id = 1

    mock_company_service = MagicMock()
    mock_company_service.get_company_by_id = AsyncMock(
        return_value=fake_company)

    mocker.patch(
        "app.services.invitation.CompanyService",
        return_value=mock_company_service,
        create=True)

    mock_user_service = MagicMock()
    mock_user_service.get_user_by_id = AsyncMock(
        return_value=2)

    mocker.patch(
        "app.services.invitation.UserService",
        return_value=mock_user_service,
        create=True)


    mocker.patch(
        "app.services.invitation.is_user_member_of_company",
        new_callable=AsyncMock,
        return_value=False)

    mocker.patch(
        "app.services.invitation.check_pending_request",
        new_callable=AsyncMock,
        return_value=None)


    class FakeMembership:

        def __init__(self, **kwargs):
            self.id = 100
            self.__dict__.update(kwargs)

    mocker.patch(
        "app.services.invitation.MembershipManagement", side_effect=FakeMembership)
    mock_add = mocker.patch(
        "app.services.invitation.add_to_db", new_callable=AsyncMock)

    invitation_data = InvitationCreate(user_id=2)
    result = await invitation_service.invitation_create(
        invitation_data, company_id=10, current_user=current_user)

    assert result.user_id == 2
    assert result.type == InvitationType.INVITATION
    assert result.status == Status.PENDING
    mock_add.assert_called_once_with(result)


async def test_create_join_request_success(invitation_service, mocker):
    current_user = MagicMock()
    current_user.id = 5

    fake_company = MagicMock()
    fake_company.id = 10

    mock_company_service = MagicMock()
    mock_company_service.get_company_by_id = AsyncMock(
        return_value=fake_company)
    mocker.patch(
        "app.services.invitation.CompanyService",
        return_value=mock_company_service,
        create=True)

    mocker.patch(
        "app.services.invitation.is_user_member_of_company",
        new_callable=AsyncMock,
        return_value=False)
    mocker.patch(
        "app.services.invitation.check_pending_request",
        new_callable=AsyncMock,
        return_value=None,)

    class FakeMembership:

        def __init__(self, **kwargs):
            self.id = 200
            self.__dict__.update(kwargs)

    mocker.patch(
        "app.services.invitation.MembershipManagement", side_effect=FakeMembership)
    mocker.patch("app.services.invitation.add_to_db", new_callable=AsyncMock)

    request_data = JoinRequestCreate(company_id=10)
    result = await invitation_service.create_join_request(
        request_data, current_user=current_user)

    assert result.company_id == 10
    assert result.user_id == 5
    assert result.type == InvitationType.REQUEST


async def test_get_membership_management_by_id_success(invitation_service, mocker):
    fake_record = MagicMock()
    mock_get = mocker.patch("app.services.invitation.get_by_filter", new_callable=AsyncMock, return_value=fake_record)

    result = await invitation_service.get_membership_management_by_id(m_id=1)
    assert result == fake_record
    mock_get.assert_called_once()


async def test_get_membership_management_by_id_not_found(invitation_service, mocker):
    mocker.patch("app.services.invitation.get_by_filter", new_callable=AsyncMock, return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await invitation_service.get_membership_management_by_id(m_id=999)
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


async def test_accept_invitation_success(invitation_service, mocker):
    current_user = MagicMock()
    current_user.id = 3

    class FakeRecord:
        def __init__(self):
            self.company_id = 10
            self.user_id = 3
            self.type = InvitationType.INVITATION
            self.status = Status.PENDING

    fake_record = FakeRecord()
    mocker.patch.object(invitation_service, "get_membership_management_by_id", new_callable=AsyncMock,
                        return_value=fake_record)
    mock_insert = mocker.patch("app.services.invitation.insert_table_record", new_callable=AsyncMock)
    mock_refresh = mocker.patch("app.services.invitation.refresh_data_in_db", new_callable=AsyncMock)

    result = await invitation_service.accept_invitation(invitation_id=1, current_user=current_user)

    assert result.status == Status.ACCEPTED
    mock_insert.assert_called_once_with(mocker.ANY, {"user_id": 3, "company_id": 10}, invitation_service.db)
    mock_refresh.assert_called_once_with(fake_record)


async def test_accept_join_request_success(invitation_service, mocker):
    current_user = MagicMock()
    current_user.id = 1
    class FakeRecord:
        def __init__(self):
            self.company_id = 10
            self.user_id = 4
            self.type = InvitationType.REQUEST
            self.status = Status.PENDING

    fake_record = FakeRecord()
    mocker.patch.object(invitation_service, "get_membership_management_by_id", new_callable=AsyncMock,
                        return_value=fake_record)

    fake_company = MagicMock()
    fake_company.owner_id = 1
    mock_company_service = MagicMock()
    mock_company_service.get_company_by_id = AsyncMock(return_value=fake_company)
    mocker.patch("app.services.invitation.CompanyService", return_value=mock_company_service, create=True)

    mock_insert = mocker.patch("app.services.invitation.insert_table_record", new_callable=AsyncMock)
    mock_refresh = mocker.patch("app.services.invitation.refresh_data_in_db", new_callable=AsyncMock)

    result = await invitation_service.accept_join_request(request_id=1, current_user=current_user)

    assert result.status == Status.ACCEPTED
    mock_insert.assert_called_once_with(mocker.ANY, {"company_id": 10, "user_id": 4}, invitation_service.db)


async def test_delete_membership_record_success(invitation_service, mocker):
    current_user = MagicMock()
    current_user.id = 1

    fake_record = MagicMock()
    fake_record.status = Status.PENDING
    fake_record.type = InvitationType.INVITATION
    fake_record.company_id = 10

    fake_company = MagicMock()
    fake_company.owner_id = 1

    mocker.patch.object(invitation_service, "get_membership_management_by_id", new_callable=AsyncMock,
                        return_value=fake_record)
    mock_company_service = MagicMock()
    mock_company_service.get_company_by_id = AsyncMock(return_value=fake_company)
    mocker.patch("app.services.invitation.CompanyService", return_value=mock_company_service, create=True)

    mock_delete = mocker.patch("app.services.invitation.delete_from_db", new_callable=AsyncMock)

    result = await invitation_service.delete_membership_record(record_id=1, current_user=current_user)
    assert result is True
    mock_delete.assert_called_once_with(fake_record, invitation_service.db)


async def test_decline_invitation_success(invitation_service, mocker):
    current_user = MagicMock()
    current_user.id = 2

    class FakeRecord:
        def __init__(self):
            self.user_id = 2
            self.type = InvitationType.INVITATION
            self.status = Status.PENDING

    fake_record = FakeRecord()
    mocker.patch.object(invitation_service, "get_membership_management_by_id", new_callable=AsyncMock,
                        return_value=fake_record)
    mock_refresh = mocker.patch("app.services.invitation.refresh_data_in_db", new_callable=AsyncMock)

    result = await invitation_service.decline_invitation(invitation_id=1, current_user=current_user)

    assert result.status == Status.DECLINED
    mock_refresh.assert_called_once_with(fake_record, invitation_service.db)


async def test_get_user_sent_requests(invitation_service, mocker):
    current_user = MagicMock()
    current_user.id = 1
    mock_list = [MagicMock()]
    mock_get = mocker.patch("app.services.invitation.get_by_filter", new_callable=AsyncMock, return_value=mock_list)

    result = await invitation_service.get_user_sent_requests(current_user)
    assert result == mock_list


async def test_get_company_pending_requests_success(invitation_service, mocker):
    current_user = MagicMock()
    current_user.id = 1

    fake_company = MagicMock()
    fake_company.owner_id = 1

    mock_company_service = MagicMock()
    mock_company_service.get_company_by_id = AsyncMock(return_value=fake_company)
    mocker.patch("app.services.invitation.CompanyService", return_value=mock_company_service, create=True)

    mock_list = [MagicMock()]
    mocker.patch("app.services.invitation.get_by_filter", new_callable=AsyncMock, return_value=mock_list)

    result = await invitation_service.get_company_pending_requests(company_id=10, current_user=current_user)
    assert result == mock_list