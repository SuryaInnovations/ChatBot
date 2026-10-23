"""
Async Database Session, Connection Pool, and Engine Management.
Supports PostgreSQL (with asyncpg) for high-concurrency production (600+ chats)
and SQLite (with aiosqlite) for zero-setup local operation and unit tests.
"""

import os
import logging
from typing import AsyncGenerator, Dict, Any
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from db.models import Base

logger = logging.getLogger("chatbot.db")

# Retrieve database connection string
# Examples:
# PostgreSQL: postgresql+asyncpg://user:pass@host:5432/dbname
# SQLite Fallback: sqlite+aiosqlite:///./chatbot.db
RAW_DB_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./chatbot.db")

# Automatically fix legacy postgres:// or standard postgresql:// for asyncpg
if RAW_DB_URL.startswith("postgres://"):
    ASYNC_DB_URL = RAW_DB_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif RAW_DB_URL.startswith("postgresql://") and not RAW_DB_URL.startswith("postgresql+asyncpg://"):
    ASYNC_DB_URL = RAW_DB_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    ASYNC_DB_URL = RAW_DB_URL

# Engine connection pool arguments
IS_SQLITE = "sqlite" in ASYNC_DB_URL

engine_kwargs: Dict[str, Any] = {
    "echo": os.getenv("DB_ECHO", "false").lower() == "true",
}

if IS_SQLITE:
    # SQLite does not support standard connection pool size/overflow
    engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30.0}
else:
    # High-concurrency production connection pool for PostgreSQL
    engine_kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "25"))
    engine_kwargs["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "35"))
    engine_kwargs["pool_timeout"] = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    engine_kwargs["pool_recycle"] = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    engine_kwargs["pool_pre_ping"] = True

try:
    async_engine = create_async_engine(ASYNC_DB_URL, **engine_kwargs)
    async_session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
    if IS_SQLITE and hasattr(async_engine, "sync_engine"):
        @event.listens_for(async_engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            try:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA synchronous=NORMAL;")
                cursor.execute("PRAGMA busy_timeout=5000;")
                cursor.close()
            except Exception:
                pass
except Exception as e:
    logger.warning("Could not initialize async_engine: %s", e)
    async_engine = None
    async_session_factory = None


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides a transactional async database session context manager."""
    session: AsyncSession = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_db():
    """Initializes tables in database if they do not already exist."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized successfully.")
