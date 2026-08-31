"""Database engine and session management abstraction.

Note: Data models, schemas, and migrations are strictly deferred to Phase 1.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from apps.api.core.config import settings

# Async database engine abstraction
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.API_ENV == "development"),
    future=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency helper to yield an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
