"""Database session management for DataGuard.

Provides async and sync sessions for PostgreSQL via SQLAlchemy.
Falls back to SQLite for local development without Docker.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.api.config import settings
from database.models import Base

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get the async database URL, with SQLite fallback."""
    url = settings.database_url
    if not url or "postgresql" not in url:
        # Fallback to SQLite for local dev
        db_path = Path("storage/dataguard.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite+aiosqlite:///{db_path}"
        logger.info(f"Using SQLite fallback: {url}")
    return url


def get_sync_database_url() -> str:
    """Get the sync database URL, with SQLite fallback."""
    url = settings.database_url_sync
    if not url or "postgresql" not in url:
        db_path = Path("storage/dataguard.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{db_path}"
    return url


# ── Async engine + session ──
_async_engine = None
_async_session_factory = None


def get_async_engine():
    global _async_engine
    if _async_engine is None:
        url = get_database_url()
        _async_engine = create_async_engine(url, echo=settings.debug, pool_pre_ping=True)
    return _async_engine


def get_async_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_async_engine()
        _async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return _async_session_factory


async def get_db() -> AsyncSession:
    """Dependency for FastAPI routes."""
    factory = get_async_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


# ── Sync engine + session (for Alembic, scripts) ──
_sync_engine = None
_sync_session_factory = None


def get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        url = get_sync_database_url()
        _sync_engine = create_engine(url, echo=settings.debug)
    return _sync_engine


def get_sync_session_factory():
    global _sync_session_factory
    if _sync_session_factory is None:
        engine = get_sync_engine()
        _sync_session_factory = sessionmaker(engine)
    return _sync_session_factory


async def init_db():
    """Create all tables. For development/testing only."""
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created.")


async def drop_db():
    """Drop all tables. For testing only."""
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("Database tables dropped.")
