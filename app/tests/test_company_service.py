import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.company import CompanyCreate, CompanyUpdate
from app.services.company import CompanyService
from app.utils.enums import VisibilityStatus

pytestmark = pytest.mark.asyncio


async def test_create_company_success(db_session: AsyncSession):
    service = CompanyService(db_session)
    company_in = CompanyCreate(
        name="Test Company",
        description="Test Description",
        visibility=VisibilityStatus.VISIBLE_TO_ALL
    )
    test_owner_id = 1

    new_company = await service.create_company(company_in, owner_id=test_owner_id)

    assert new_company.id is not None
    assert new_company.name == "Test Company"
    assert new_company.owner_id == test_owner_id
    assert new_company.visibility == VisibilityStatus.VISIBLE_TO_ALL


async def test_update_company_by_non_owner_raises_403(db_session: AsyncSession):
    service = CompanyService(db_session)

    company_in = CompanyCreate(name="Owner's Company")
    company = await service.create_company(company_in, owner_id=1)

    company_update = CompanyUpdate(name="Hacked Name")

    with pytest.raises(HTTPException) as exc_info:
        await service.update_company(
            company_id=company.id,
            company_data=company_update,
            user_id=2
        )

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "permission" in exc_info.value.detail


async def test_update_company_by_owner_success(db_session: AsyncSession):
    service = CompanyService(db_session)

    company_in = CompanyCreate(name="Old Name", description="Old Desc")
    company = await service.create_company(company_in, owner_id=1)

    company_update = CompanyUpdate(name="New Name")
    updated_company = await service.update_company(
        company_id=company.id,
        company_data=company_update,
        user_id=1
    )

    assert updated_company.name == "New Name"
    assert updated_company.description == "Old Desc"


async def test_get_company_by_id_not_found(db_session: AsyncSession):
    service = CompanyService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_company_by_id(company_id=99999)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


async def test_get_companies_pagination(db_session: AsyncSession):
    service = CompanyService(db_session)

    for i in range(3):
        company_in = CompanyCreate(name=f"Company {i}", visibility=VisibilityStatus.VISIBLE_TO_ALL)
        await service.create_company(company_in, owner_id=1)

    companies_list = await service.get_companies(limit=2, offset=0)

    assert len(companies_list) == 2
