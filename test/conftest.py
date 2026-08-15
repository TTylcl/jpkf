""" test/conftest.py """
import sys
import asyncio
from pathlib import Path
import pytest

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from core.service.models import AGENT_PERMISSIONS_MATRIX
from core.database import AsyncDatabase

TEST_DB_URL = "postgresql+asyncpg://postgres:123456@127.0.0.1:5434/test_database"


@pytest.fixture(scope="function", autouse=True)
async def init_database():
    """每个测试独立 engine，loop 天然一致"""
    engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        pool_pre_ping=False,
    )
    AsyncDatabase._engine = engine
    AsyncDatabase._session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    yield
    await engine.dispose()
    AsyncDatabase._engine = None
    AsyncDatabase._session_factory = None


@pytest.fixture(scope="session", autouse=True)
def setup_test_permissions():
    if 'edu_admin_agent' not in AGENT_PERMISSIONS_MATRIX:
        AGENT_PERMISSIONS_MATRIX['edu_admin_agent'] = {}
    AGENT_PERMISSIONS_MATRIX['edu_admin_agent']['rag'] = ['rag_search']