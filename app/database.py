from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.schemas.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()