import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException, status

from app.schemas.quiz import QuizCreate, QuizSubmit, UserAnswerSubmit
from app.services.quiz import QuizService

pytestmark = pytest.mark.asyncio


# --- ФІКСТУРИ ---

@pytest.fixture
def mock_db_session():
    return MagicMock()


@pytest.fixture
def mock_redis():
    redis_client = MagicMock()
    pipe_mock = AsyncMock()
    redis_client.pipeline.return_value.__aenter__.return_value = pipe_mock
    return redis_client


@pytest.fixture
def quiz_service(mock_db_session):
    return QuizService(db_session=mock_db_session)


async def test_create_quiz_success(quiz_service, mocker):
    current_user = MagicMock()
    current_user.id = 1

    fake_company = MagicMock()
    fake_company.owner_id = 1

    mock_company_service = MagicMock()
    mock_company_service.get_company_by_id = AsyncMock(return_value=fake_company)
    mocker.patch("app.services.quiz.CompanyService", return_value=mock_company_service, create=True)

    mocker.patch("app.services.quiz.check_admin_role", new_callable=AsyncMock, return_value=False, create=True)

    fake_quiz = MagicMock()
    mock_create = mocker.patch("app.services.quiz.create_quiz", new_callable=AsyncMock, return_value=fake_quiz)

    quiz_data = QuizCreate.model_construct(title="Python Basics")
    result = await quiz_service.create_quiz(quiz_data, company_id=10, current_user=current_user)

    assert result == fake_quiz
    mock_create.assert_called_once_with(quiz_data, 10, quiz_service.db)


async def test_get_quiz_by_id_success(quiz_service, mocker):
    fake_quiz = MagicMock()
    mock_get = mocker.patch("app.services.quiz.get_quiz_by_id", new_callable=AsyncMock, return_value=fake_quiz)

    result = await quiz_service.get_quiz_by_id(quiz_id=42)
    assert result == fake_quiz
    mock_get.assert_called_once()


async def test_get_quiz_by_id_not_found(quiz_service, mocker):
    mocker.patch("app.services.quiz.get_quiz_by_id", new_callable=AsyncMock, return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await quiz_service.get_quiz_by_id(quiz_id=999)
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


async def test_save_question_progress_success(quiz_service, mock_redis):
    answer_data = UserAnswerSubmit.model_construct(
        question_id=1, chosen_answer_id=5)

    mock_redis.hset = AsyncMock()
    mock_redis.expire = AsyncMock()

    pipe_mock = AsyncMock()
    pipe_mock.hset = AsyncMock()
    pipe_mock.expire = AsyncMock()
    pipe_mock.execute = AsyncMock()
    mock_redis.pipeline.return_value.__aenter__.return_value = pipe_mock

    await quiz_service.save_question_progress(
        mock_redis, quiz_id=10, user_id=1, answer_data=answer_data)

    assert mock_redis.hset.called or pipe_mock.hset.called


async def test_get_quiz_progress_success(quiz_service, mock_redis):
    mock_redis.hgetall = AsyncMock(return_value={b"1": b"5", b"2": b"[3, 4]"})

    result = await quiz_service.get_quiz_progress(mock_redis, user_id=1, quiz_id=10)

    assert result == {1: 5, 2: [3, 4]}


async def test_create_quiz_attempt_success(quiz_service, mock_redis, mocker):
    current_user = MagicMock()
    current_user.id = 2

    fake_option_1 = MagicMock(id=10, is_correct=True)
    fake_option_2 = MagicMock(id=11, is_correct=False)
    fake_question = MagicMock(id=1, answers=[fake_option_1, fake_option_2])

    fake_quiz = MagicMock()
    fake_quiz.company_id = 100
    fake_quiz.max_attempts = 0
    fake_quiz.questions = [fake_question]

    fake_company = MagicMock()
    fake_company.id = 100
    fake_company.owner_id = 1

    mocker.patch.object(quiz_service, "get_quiz_by_id", new_callable=AsyncMock, return_value=fake_quiz)

    mock_company_service = MagicMock()
    mock_company_service.get_company_by_id = AsyncMock(return_value=fake_company)
    mocker.patch("app.services.quiz.CompanyService", return_value=mock_company_service, create=True)

    mocker.patch("app.services.quiz.check_admin_role", new_callable=AsyncMock, return_value=False, create=True)

    mocker.patch.object(quiz_service, "get_quiz_progress", new_callable=AsyncMock, return_value={1: 10})
    mocker.patch.object(quiz_service, "clear_quiz_progress", new_callable=AsyncMock)

    class FakeAttempt:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    mocker.patch("app.services.quiz.QuizAttempt", side_effect=FakeAttempt)
    mock_add = mocker.patch("app.services.quiz.add_to_db", new_callable=AsyncMock)

    answers_data = QuizSubmit.model_construct(answers=[])
    result = await quiz_service.create_quiz_attempt(quiz_id=5, answers=answers_data, current_user=current_user,
                                                    redis=mock_redis)

    assert result.score == 100.0
    assert result.correct_answers == 1
    mock_add.assert_called_once()


async def test_get_user_personal_quizzes_export(quiz_service, mock_redis, mocker):
    current_user = MagicMock()
    current_user.id = 1

    async def mock_scan_iter(match):
        yield b"quiz_progress:1:10"

    mock_redis.scan_iter = mock_scan_iter
    mocker.patch.object(quiz_service, "get_quiz_progress", new_callable=AsyncMock, return_value={101: [5]})

    result = await quiz_service.get_user_personal_quizzes_export(mock_redis, current_user, quiz_id=10)

    assert len(result) == 1
    assert result[0]["quiz_id"] == 10
    assert result[0]["question_id"] == 101


async def test_get_company_quizzes_export_success(quiz_service, mock_redis, mocker):
    current_user = MagicMock()
    current_user.id = 1

    fake_company = MagicMock()
    fake_company.owner_id = 1

    mock_company_service = MagicMock()
    mock_company_service.get_company_by_id = AsyncMock(return_value=fake_company)
    mocker.patch("app.services.quiz.CompanyService", return_value=mock_company_service, create=True)
    mocker.patch("app.services.quiz.check_admin_role", new_callable=AsyncMock, return_value=True, create=True)

    mocker.patch("app.services.quiz.is_user_member_of_company", new_callable=AsyncMock, return_value=True, create=True)

    async def mock_scan_iter(match):
        yield b"quiz_progress:2:10"
    mock_redis.scan_iter = mock_scan_iter

    mocker.patch.object(quiz_service, "get_quiz_progress", new_callable=AsyncMock, return_value={5: 12})

    result = await quiz_service.get_company_quizzes_export(
        redis=mock_redis, current_user=current_user, company_id=1, user_id=2, quiz_id=10)

    assert len(result) == 1
    assert result[0]["user_id"] == 2
    assert result[0]["quiz_id"] == 10