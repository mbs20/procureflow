from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from procureflow.config import get_settings

settings = get_settings()

# Configure async engine
# Note: SQLite requires different connect_args than PostgreSQL
is_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug and settings.environment == "development",
    future=True,
    connect_args=connect_args,
)

async_session_maker = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Create database tables directly if needed (e.g. in tests or initial setup)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
