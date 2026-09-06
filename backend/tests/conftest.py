import os
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

# Set test environment flags
TEST_DB_FILE = Path("/tmp/test_procureflow.db").resolve()
os.environ["PROCUREFLOW_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_FILE}"
os.environ["DATABASE_URL_SYNC"] = f"sqlite:///{TEST_DB_FILE}"
os.environ["CELERY_ALWAYS_EAGER"] = "true"
os.environ["PROCUREFLOW_LLM_PROVIDER"] = "mock"
os.environ["STORAGE_LOCAL_DIR"] = "/tmp/test_storage"

import procureflow.database as db_mod  # noqa: E402
import procureflow.tasks.extraction as extraction_mod  # noqa: E402
from procureflow.api.deps import verify_api_key  # noqa: E402
from procureflow.database import Base, get_db  # noqa: E402
from procureflow.main import app  # noqa: E402

test_engine = create_async_engine(
    f"sqlite+aiosqlite:///{TEST_DB_FILE}",
    connect_args={"check_same_thread": False},
    future=True,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

test_sync_engine = create_engine(
    f"sqlite:///{TEST_DB_FILE}",
    connect_args={"check_same_thread": False},
)

TestSyncSessionLocal = sessionmaker(
    bind=test_sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def test_get_session_factory() -> sessionmaker[Session]:
    return TestSyncSessionLocal


# Monkeypatch session factory for Celery tasks in tests
db_mod.get_session_factory = test_get_session_factory
extraction_mod.get_session_factory = test_get_session_factory


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncSession:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncClient:
    async def override_get_db():
        yield db_session

    async def override_verify_api_key():
        return "test-user"

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[verify_api_key] = override_verify_api_key
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
