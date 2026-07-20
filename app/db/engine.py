"""Async SQLAlchemy engine + session factory for the permanent Postgres store.

Mirrors the module-singleton pattern used for Redis (`app.session.redis_client`)
and OpenAI (`app.analyzer.client`). The datastore is OPTIONAL: when
`DATABASE_URL` is unset (local dev, tests, CI) the engine is ``None`` and every
write no-ops, so the app runs unchanged without Postgres.

A DB outage must NEVER affect the user-facing response — the write helpers in
`app.db.crud` swallow and log all errors, and callers persist fire-and-forget.
"""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all ORM models. Alembic reads ``Base.metadata``."""


def _make_engine() -> AsyncEngine | None:
    url = settings.database_url
    if not url:
        logger.info("DATABASE_URL not set — Postgres persistence disabled")
        return None
    kwargs: dict = {
        "pool_pre_ping": True,   # discard dead connections rather than erroring mid-request
        "pool_recycle": 1800,    # recycle every 30 min to dodge RDS idle timeouts
    }
    # QueuePool sizing applies to server DBs (Postgres/RDS). SQLite uses NullPool,
    # which rejects these — skip them so a sqlite:// URL also works locally.
    if not url.startswith("sqlite"):
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 5
    return create_async_engine(url, **kwargs)


# Module-level singletons, created once at import. `async_session` and
# `db_enabled` are what `app.db.crud` reads (at call time, so tests can swap
# these attributes to point at an in-memory SQLite DB).
engine: AsyncEngine | None = _make_engine()
async_session: async_sessionmaker | None = (
    async_sessionmaker(engine, expire_on_commit=False) if engine is not None else None
)
db_enabled: bool = engine is not None


async def ping() -> None:
    """Verify connectivity (``SELECT 1``). Raises if unreachable; the caller
    decides policy. No-op when the DB is disabled."""
    if engine is None:
        return
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def dispose() -> None:
    """Close the connection pool on shutdown."""
    if engine is not None:
        await engine.dispose()
