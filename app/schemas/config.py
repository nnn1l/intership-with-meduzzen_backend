from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_URL: str

    SECRET_KEY: str
    ALGORITHM: str

    AUTH0_DOMAIN: str
    AUTH0_CLIENT: str
    AUTH0_CLIENT_SECRET: str
    AUTH0_SECRET: str
    AUTH0_AUDIENCE: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int

    @property
    def DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env")

settings = Settings()