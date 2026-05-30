FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1\
    PYTHONDONTWRITEBYTECODE=1\
    POETRY_VIRTUALENVS_CREATE=false\
    POETRY_NO_INTERACTION=1

RUN pip install --no-cache-dir poetry

WORKDIR /app

COPY poetry.lock pyproject.toml /app/

RUN poetry install --no-root

COPY . /app/

EXPOSE 8000

CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0","--port", "8000"]