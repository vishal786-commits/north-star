"""Tests for the permanent datastore (`app.db`).

Runs fully offline against in-memory SQLite (aiosqlite) — no Postgres required.
Verifies the best-effort insert, the feedback update, and that writes are silent
no-ops when the DB is disabled (the 'never interrupt the user' contract).
"""
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import crud
from app.db import engine as db_engine
from app.db.models import LLMInteraction


@pytest_asyncio.fixture
async def sqlite_db():
    """Point the db layer at a fresh in-memory SQLite DB, then restore."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with test_engine.begin() as conn:
        await conn.run_sync(db_engine.Base.metadata.create_all)

    original = (db_engine.engine, db_engine.async_session, db_engine.db_enabled)
    db_engine.engine = test_engine
    db_engine.async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    db_engine.db_enabled = True
    try:
        yield test_engine
    finally:
        db_engine.engine, db_engine.async_session, db_engine.db_enabled = original
        await test_engine.dispose()


async def test_record_interaction_writes_row(sqlite_db):
    await crud.record_interaction(
        feature="resume_review", session_id="s1", model="gpt-4o-mini",
        prompt_version="resume_review@test", response_json={"ats": {"overall": 80}},
        input_tokens=100, output_tokens=50, latency_ms=1234.5, request_id="req-1",
    )
    async with db_engine.async_session() as session:
        rows = (await session.execute(sa.select(LLMInteraction))).scalars().all()

    assert len(rows) == 1
    row = rows[0]
    assert row.feature == "resume_review"
    assert row.response_json == {"ats": {"overall": 80}}
    assert row.input_tokens == 100
    assert row.output_tokens == 50
    assert row.latency_ms == 1234.5
    assert row.request_id == "req-1"
    assert row.id is not None            # UUID default applied
    assert row.created_at is not None    # server_default now() applied


async def test_update_feedback_patches_latest(sqlite_db):
    await crud.record_interaction(feature="resume_review", session_id="s2")
    await crud.update_feedback(session_id="s2", rating="up", comment="great")

    async with db_engine.async_session() as session:
        row = (await session.execute(
            sa.select(LLMInteraction).where(LLMInteraction.session_id == "s2")
        )).scalar_one()

    assert row.user_rating == "up"
    assert row.user_comment == "great"


async def test_update_feedback_missing_session_is_noop(sqlite_db):
    # No interaction for this session — must not raise.
    await crud.update_feedback(session_id="nope", rating="down", comment=None)


async def test_writes_noop_when_disabled():
    """With the DB disabled (default in tests: DATABASE_URL unset), writes are
    silent no-ops and never raise."""
    assert not db_engine.db_enabled
    await crud.record_interaction(feature="chat", session_id="x")
    await crud.update_feedback(session_id="x", rating="down", comment=None)
