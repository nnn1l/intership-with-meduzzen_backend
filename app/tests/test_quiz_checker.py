import pytest
from unittest.mock import AsyncMock, MagicMock
from ..services.quiz_checker import QuizReminderService


pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db_session():
    return MagicMock()


@pytest.fixture
def quiz_checker_service(mock_db_session):
    return QuizReminderService(db_session=mock_db_session)



async def test_check_and_remind_users_success(quiz_checker_service, mocker):
    fake_quiz = MagicMock()
    fake_quiz.title = "Python Core"
    fake_quiz.company_id = 10

    fake_company = MagicMock()
    fake_company.owner_id = 1

    fake_owner_user = MagicMock()

    mocker.patch("app.services.quiz_checker.select_all", new_callable=AsyncMock, return_value=[fake_quiz])

    mocker.patch("app.services.quiz_checker.get_members_ids_of_company_by_quiz", new_callable=AsyncMock,
                 return_value=[2, 3, 4])
    mocker.patch("app.services.quiz_checker.get_members_completed_quiz", new_callable=AsyncMock, return_value=[2])

    mock_notification_service = MagicMock()
    mock_notification_service.create_notifications = AsyncMock()
    mocker.patch("app.services.quiz_checker.NotificationService", return_value=mock_notification_service, create=True)

    mock_company_service = MagicMock()
    mock_company_service.get_company_by_id = AsyncMock(return_value=fake_company)
    mocker.patch("app.services.quiz_checker.CompanyService", return_value=mock_company_service, create=True)

    mock_user_service = MagicMock()
    mock_user_service.get_user_by_id = AsyncMock(return_value=fake_owner_user)
    mocker.patch("app.services.quiz_checker.UserService", return_value=mock_user_service, create=True)

    fake_notification_data = MagicMock()
    mocker.patch("app.schemas.notification.NotificationCreate.model_construct", return_value=fake_notification_data)
    mocker.patch("app.services.quiz_checker.NotificationCreate", return_value=fake_notification_data)

    await quiz_checker_service.check_and_remind_users()

    mock_notification_service.create_notifications.assert_called_once()

    called_kwargs = mock_notification_service.create_notifications.call_args[1]
    assert called_kwargs["current_user"] == fake_owner_user
    assert set(called_kwargs["receiver_ids"]) == {3, 4}
    assert called_kwargs["company_id"] == 10


async def test_check_and_remind_users_no_members(quiz_checker_service, mocker):
    fake_quiz = MagicMock()

    mocker.patch("app.services.quiz_checker.select_all", new_callable=AsyncMock, return_value=[fake_quiz])
    mocker.patch("app.services.quiz_checker.get_members_ids_of_company_by_quiz", new_callable=AsyncMock,
                 return_value=[])

    mock_notification_service = MagicMock()
    mocker.patch("app.services.quiz_checker.NotificationService", return_value=mock_notification_service, create=True)

    await quiz_checker_service.check_and_remind_users()

    mock_notification_service.create_notifications.assert_not_called()