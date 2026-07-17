import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException, status
from datetime import datetime

from app.schemas.analytics import (
    UserGlobalAnalyticsResponse, UserQuizPeriodAnalyticsResponse,
    UserLastCompletionResponse, CompanyMemberQuizTrendsResponse,
    CompanyOverallDynamicsResponse, CompanyMemberLastAttemptResponse
)
from app.services.analytics import UserAnalytics, CompanyAnalytics


pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db_session():
    return MagicMock()


@pytest.fixture
def user_analytics_service(mock_db_session):
    return UserAnalytics(db_session=mock_db_session)


@pytest.fixture
def company_analytics_service(mock_db_session):
    return CompanyAnalytics(db_session=mock_db_session)



async def test_get_user_analytics_global_success(user_analytics_service, mocker):
    current_user = MagicMock()
    mock_response = UserGlobalAnalyticsResponse.model_construct(correct_answers_percentage=75.5)

    mock_repo = mocker.patch("app.services.analytics.get_user_analytics_global", new_callable=AsyncMock,
                             return_value=mock_response)

    result = await user_analytics_service.get_user_analytics_global(current_user)

    assert result == mock_response
    mock_repo.assert_called_once_with(current_user)


async def test_get_user_analytics_by_time_periods_success(user_analytics_service, mocker):
    current_user = MagicMock()
    start = datetime(2026, 1, 1)
    end = datetime(2026, 1, 7)
    mock_list = [UserQuizPeriodAnalyticsResponse.model_construct(quiz_id=1, average_score=80.0)]

    mock_repo = mocker.patch("app.services.analytics.get_user_analytics_by_time_periods", new_callable=AsyncMock,
                             return_value=mock_list)

    result = await user_analytics_service.get_user_analytics_by_time_periods(current_user, start, end)

    assert result == mock_list
    mock_repo.assert_called_once_with(current_user, start, end)


async def test_get_user_analytics_last_competition_success(user_analytics_service, mocker):
    current_user = MagicMock()
    mock_list = [UserLastCompletionResponse.model_construct(quiz_id=1, last_completed_at=datetime.now())]

    mock_repo = mocker.patch("app.services.analytics.get_user_analytics_last_competition", new_callable=AsyncMock,
                             return_value=mock_list)

    result = await user_analytics_service.get_user_analytics_last_competition(current_user)

    assert result == mock_list
    mock_repo.assert_called_once_with(current_user)



async def test_get_user_analytics_in_company_success(company_analytics_service, mocker):
    current_user = MagicMock()
    current_user.id = 1

    fake_company = MagicMock()
    fake_company.owner_id = 1

    mock_company_service = MagicMock()
    mock_company_service.get_company_by_id = AsyncMock(return_value=fake_company)
    mocker.patch("app.services.analytics.CompanyService", return_value=mock_company_service, create=True)

    mocker.patch("app.services.analytics.check_admin_role", new_callable=AsyncMock, return_value=False, create=True)
    mocker.patch("app.services.analytics.is_user_member_of_company", new_callable=AsyncMock, return_value=True,
                 create=True)

    mock_trends = [CompanyMemberQuizTrendsResponse.model_construct(quiz_id=5, score=90.0)]
    mock_repo = mocker.patch("app.services.analytics.get_user_analytics_in_company", new_callable=AsyncMock,
                             return_value=mock_trends)

    result = await company_analytics_service.get_user_analytics_in_company(user_id=2, company_id=10,
                                                                           current_user=current_user)

    assert result == mock_trends
    mock_repo.assert_called_once_with(2, 10)


async def test_get_user_analytics_in_company_forbidden(company_analytics_service, mocker):
    current_user = MagicMock()
    current_user.id = 99

    fake_company = MagicMock()
    fake_company.owner_id = 1

    mock_company_service = MagicMock()
    mock_company_service.get_company_by_id = AsyncMock(return_value=fake_company)
    mocker.patch("app.services.analytics.CompanyService", return_value=mock_company_service, create=True)

    mocker.patch("app.services.analytics.check_admin_role", new_callable=AsyncMock, return_value=False, create=True)
    mocker.patch("app.services.analytics.is_user_member_of_company", new_callable=AsyncMock, return_value=False,
                 create=True)
    mocker.patch("app.services.analytics.get_user_analytics_in_company", new_callable=AsyncMock, create=True)

    with pytest.raises(HTTPException) as exc_info:
        await company_analytics_service.get_user_analytics_in_company(user_id=2, company_id=10,
                                                                      current_user=current_user)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


async def test_get_member_analytics_over_week_success(company_analytics_service, mocker):
    current_user = MagicMock()
    current_user.id = 1

    fake_company = MagicMock()
    fake_company.owner_id = 1

    mock_company_service = MagicMock()
    mock_company_service.get_company_by_id = AsyncMock(return_value=fake_company)
    mocker.patch("app.services.analytics.CompanyService", return_value=mock_company_service, create=True)

    mocker.patch("app.services.analytics.check_admin_role", new_callable=AsyncMock, return_value=True, create=True)

    mock_week_data = [CompanyOverallDynamicsResponse.model_construct(average_score=85.0)]
    mock_repo = mocker.patch("app.services.analytics.get_member_analytics_over_week", new_callable=AsyncMock,
                             return_value=mock_week_data)

    result = await company_analytics_service.get_member_analytics_over_week(company_id=10, current_user=current_user)

    assert result == mock_week_data
    mock_repo.assert_called_once_with(10)


async def test_get_company_members_last_competition_success(company_analytics_service, mocker):
    current_user = MagicMock()
    current_user.id = 1

    fake_company = MagicMock()
    fake_company.owner_id = 1

    mock_company_service = MagicMock()
    mock_company_service.get_company_by_id = AsyncMock(return_value=fake_company)
    mocker.patch("app.services.analytics.CompanyService", return_value=mock_company_service, create=True)

    mocker.patch("app.services.analytics.check_admin_role", new_callable=AsyncMock, return_value=True, create=True)

    mock_last_comp = [CompanyMemberLastAttemptResponse.model_construct(user_id=2, score=70.0)]
    mock_repo = mocker.patch("app.services.analytics.get_company_members_last_competition", new_callable=AsyncMock,
                             return_value=mock_last_comp)

    result = await company_analytics_service.get_company_members_last_competition(company_id=10,
                                                                                  current_user=current_user)

    assert result == mock_last_comp
    mock_repo.assert_called_once_with(10)