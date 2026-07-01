import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException, status

from ..schemas.company import CompanyCreate, CompanyUpdate
from ..services.company import CompanyService
from ..utils.enums import VisibilityStatus


pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db_session():
    return MagicMock()


@pytest.fixture
def company_service(mock_db_session):
    return CompanyService(db_session=mock_db_session)


async def test_create_company_success(company_service, mocker):
    company_data = CompanyCreate(name="Meduzzen", description="Best IT", visibility=VisibilityStatus.VISIBLE_TO_ALL)

    class FakeCompany:
        def __init__(self):
            self.name = "Meduzzen"
            self.description = "Best IT"
            self.visibility = VisibilityStatus.VISIBLE_TO_ALL
            self.owner_id = 1

    fake_company = FakeCompany()
    mocker.patch("app.services.company.Company", return_value=fake_company)
    mock_add = mocker.patch("app.services.company.add_to_db", new_callable=AsyncMock)

    result = await company_service.create_company(company_data, owner_id=1)

    assert result.name == "Meduzzen"
    assert result.owner_id == 1
    mock_add.assert_called_once_with(fake_company, company_service.db)


async def test_get_company_by_id_success(company_service, mocker):
    fake_company = MagicMock()
    mock_get = mocker.patch("app.services.company.get_by_filter", new_callable=AsyncMock, return_value=fake_company)

    result = await company_service.get_company_by_id(company_id=42)

    assert result == fake_company
    mock_get.assert_called_once()


async def test_get_company_by_id_not_found(company_service, mocker):
    mocker.patch("app.services.company.get_by_filter", new_callable=AsyncMock, return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await company_service.get_company_by_id(company_id=999)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


async def test_get_companies_success(company_service, mocker):
    mock_list = [MagicMock(), MagicMock()]
    mock_pagination = mocker.patch("app.services.company.get_with_pagination", new_callable=AsyncMock,
                                   return_value=mock_list)

    result = await company_service.get_companies(limit=10, offset=0)

    assert result == mock_list
    mock_pagination.assert_called_once()


async def test_update_company_success(company_service, mocker):
    class FakeCompany:
        def __init__(self):
            self.name = "Old Name"
            self.owner_id = 1

    fake_company = FakeCompany()
    mocker.patch.object(company_service, "get_company_by_id", new_callable=AsyncMock, return_value=fake_company)
    mock_refresh = mocker.patch("app.services.company.refresh_data_in_db", new_callable=AsyncMock)

    update_data_mock = MagicMock()
    update_data_mock.model_dump.return_value = {"name": "New Name"}

    result = await company_service.update_company(company_id=1, company_data=update_data_mock, user_id=1)

    assert result.name == "New Name"
    mock_refresh.assert_called_once_with(fake_company, company_service.db)


async def test_update_company_forbidden(company_service, mocker):
    fake_company = MagicMock()
    fake_company.owner_id = 1
    mocker.patch.object(company_service, "get_company_by_id", new_callable=AsyncMock, return_value=fake_company)

    with pytest.raises(HTTPException) as exc_info:
        await company_service.update_company(company_id=1, company_data=MagicMock(), user_id=2)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


async def test_delete_company_success(company_service, mocker):
    fake_company = MagicMock()
    fake_company.owner_id = 1
    mocker.patch.object(company_service, "get_company_by_id", new_callable=AsyncMock, return_value=fake_company)
    mock_delete = mocker.patch("app.services.company.delete_from_db", new_callable=AsyncMock)

    await company_service.delete_company(company_id=1, user_id=1)
    mock_delete.assert_called_once_with(fake_company, company_service.db)


async def test_change_company_visibility_to_hidden(company_service, mocker):
    class FakeCompany:
        def __init__(self):
            self.visibility = VisibilityStatus.VISIBLE_TO_ALL
            self.owner_id = 1

    fake_company = FakeCompany()
    mocker.patch.object(company_service, "get_company_by_id", new_callable=AsyncMock, return_value=fake_company)
    mocker.patch("app.services.company.refresh_data_in_db", new_callable=AsyncMock)

    result = await company_service.change_company_visibility(company_id=1, user_id=1)

    assert result.visibility == VisibilityStatus.HIDDEN


async def test_fire_user_success(company_service, mocker):
    current_user = MagicMock()
    current_user.id = 1

    fake_company = MagicMock()
    fake_company.owner_id = 1

    mocker.patch.object(company_service, "get_company_by_id", new_callable=AsyncMock, return_value=fake_company)
    mocker.patch("app.services.company.is_user_member_of_company", new_callable=AsyncMock, return_value=True)
    mock_delete_record = mocker.patch("app.services.company.delete_table_record_by_filter", new_callable=AsyncMock)

    await company_service.fire_user_from_company(company_id=1, fired_user_id=2, current_user=current_user)

    mock_delete_record.assert_called_once()


async def test_fire_user_yourself_error(company_service):
    current_user = MagicMock()
    current_user.id = 1

    with pytest.raises(HTTPException) as exc_info:
        await company_service.fire_user_from_company(company_id=1, fired_user_id=1, current_user=current_user)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


async def test_leave_company_success(company_service, mocker):
    current_user = MagicMock()
    current_user.id = 2

    fake_company = MagicMock()
    fake_company.owner_id = 1

    mocker.patch.object(company_service, "get_company_by_id", new_callable=AsyncMock, return_value=fake_company)
    mocker.patch("app.services.company.is_user_member_of_company", new_callable=AsyncMock, return_value=True)
    mock_delete_record = mocker.patch("app.services.company.delete_table_record_by_filter", new_callable=AsyncMock)

    await company_service.leave_company(company_id=1, current_user=current_user)
    mock_delete_record.assert_called_once()


# 9. APPOINT ADMIN
async def test_appoint_admin_success(company_service, mocker):
    current_user = MagicMock()
    current_user.id = 1

    fake_company = MagicMock()
    fake_company.owner_id = 1

    fake_target_user = MagicMock()

    mocker.patch.object(company_service, "get_company_by_id", new_callable=AsyncMock, return_value=fake_company)

    mock_user_service_instance = MagicMock()
    mock_user_service_instance.get_user_by_id = AsyncMock(return_value=fake_target_user)

    mocker.patch("app.services.company.UserService", return_value=mock_user_service_instance, create=True)

    mocker.patch("app.services.company.is_user_member_of_company", new_callable=AsyncMock, return_value=True)
    mocker.patch("app.services.company.check_admin_role", new_callable=AsyncMock, return_value=False)
    mock_update_record = mocker.patch("app.services.company.update_table_record_by_filter", new_callable=AsyncMock)

    result = await company_service.appoint_admin(company_id=1, user_id=2, current_user=current_user)

    assert result == fake_target_user
    mock_update_record.assert_called_once()


async def test_decline_admin_role_success(company_service, mocker):
    current_user = MagicMock()
    current_user.id = 1

    fake_company = MagicMock()
    fake_company.owner_id = 1

    fake_target_user = MagicMock()

    mocker.patch.object(company_service, "get_company_by_id", new_callable=AsyncMock, return_value=fake_company)

    mock_user_service_instance = MagicMock()
    mock_user_service_instance.get_user_by_id = AsyncMock(return_value=fake_target_user)

    mocker.patch("app.services.company.UserService", return_value=mock_user_service_instance, create=True)

    mocker.patch("app.services.company.is_user_member_of_company", new_callable=AsyncMock, return_value=True)
    mocker.patch("app.services.company.check_admin_role", new_callable=AsyncMock, return_value=True)
    mock_update_record = mocker.patch("app.services.company.update_table_record_by_filter", new_callable=AsyncMock)

    result = await company_service.decline_admin_role(company_id=1, user_id=2, current_user=current_user)

    assert result == fake_target_user
    mock_update_record.assert_called_once()


async def test_get_company_administration_success(company_service, mocker):
    mocker.patch.object(company_service, "get_company_by_id", new_callable=AsyncMock)
    mock_admins_list = [MagicMock(), MagicMock()]
    mock_get_admins = mocker.patch("app.services.company.get_company_administration", new_callable=AsyncMock,
                                   return_value=mock_admins_list)

    result = await company_service.get_company_administration(company_id=1)

    assert result == mock_admins_list
    mock_get_admins.assert_called_once()