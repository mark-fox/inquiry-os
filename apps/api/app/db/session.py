from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

# Create async engine using DATABASE_URL from settings
engine = create_async_engine(
    settings.database_url,
    echo=False,   # set True if you want to see SQL in logs while debugging
    future=True,
)

# Factory for async sessions
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an AsyncSession.
    We'll use this in endpoints and services when we start
    reading/writing research runs.
    """
    async with AsyncSessionLocal() as session:
        yield session
