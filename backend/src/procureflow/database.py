from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

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

is_sync_sqlite = settings.database_url_sync.startswith("sqlite")
sync_connect_args = {"check_same_thread": False} if is_sync_sqlite else {}

sync_engine = create_engine(
    settings.database_url_sync,
    echo=False,
    connect_args=sync_connect_args,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_session_factory() -> sessionmaker[Session]:
    """Provides synchronous sessionmaker for background Celery worker tasks."""
    return SyncSessionLocal


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
        if not is_sqlite:
            from sqlalchemy import text

            alter_statements = [
                "ALTER TABLE extracted_quotations ADD COLUMN IF NOT EXISTS is_current BOOLEAN DEFAULT TRUE NOT NULL",
                "ALTER TABLE extracted_quotations ADD COLUMN IF NOT EXISTS acknowledged_warnings JSON DEFAULT '[]'",
                "ALTER TABLE extracted_line_items ADD COLUMN IF NOT EXISTS calculated_total_price NUMERIC(14, 4)",
                "ALTER TABLE extracted_line_items ADD COLUMN IF NOT EXISTS source_evidence JSON",
                "ALTER TABLE extracted_line_items ADD COLUMN IF NOT EXISTS human_corrected BOOLEAN DEFAULT FALSE NOT NULL",
                "ALTER TABLE extracted_line_items ADD COLUMN IF NOT EXISTS is_removed BOOLEAN DEFAULT FALSE NOT NULL",
                "ALTER TABLE extracted_line_items ADD COLUMN IF NOT EXISTS removal_reason VARCHAR(255)",
                "ALTER TABLE extracted_quotation_fields ADD COLUMN IF NOT EXISTS source_evidence JSON",
                "ALTER TABLE extracted_quotation_fields ADD COLUMN IF NOT EXISTS human_corrected BOOLEAN DEFAULT FALSE NOT NULL",
            ]
            for stmt in alter_statements:
                await conn.execute(text(stmt))
