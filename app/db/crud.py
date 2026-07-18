"""Data access for the permanent datastore.

Every function is BEST-EFFORT: a DB failure is logged and swallowed so it can
never propagate into a user-facing request (the guiding contract of this store).
When Postgres is disabled (no ``DATABASE_URL``) every call is a silent no-op.

The engine module is imported (not its attributes) so that `db_enabled` and
`async_session` are read at call time — this lets the test suite swap the
singletons to point at an in-memory SQLite DB.
"""
import logging

import sqlalchemy as sa

from app.db import engine as db_engine
from app.db.models import LLMInteraction

logger = logging.getLogger(__name__)


async def record_interaction(
    *,
    feature: str,
    session_id: str | None = None,
    resume_text: str | None = None,
    job_description: str | None = None,
    model: str | None = None,
    prompt_version: str | None = None,
    response_json: dict | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    latency_ms: float | None = None,
    request_id: str | None = None,
) -> None:
    """Persist one successful LLM interaction. No-op when the DB is disabled."""
    if not db_engine.db_enabled or db_engine.async_session is None:
        return
    try:
        async with db_engine.async_session() as session:
            session.add(
                LLMInteraction(
                    feature=feature,
                    session_id=session_id,
                    resume_text=resume_text,
                    job_description=job_description,
                    model=model,
                    prompt_version=prompt_version,
                    response_json=response_json,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    request_id=request_id,
                )
            )
            await session.commit()
    except Exception:
        logger.exception("Failed to persist llm_interaction (non-fatal)")


async def update_feedback(*, session_id: str, rating: str, comment: str | None) -> None:
    """Attach a 👍/👎 to the MOST RECENT interaction for this session.

    Session-level, not row-precise: a session can hold a review/fit plus several
    chats, and the UI's feedback control sits on the analysis result. If exact
    per-turn feedback is needed later, return the interaction id to the client.
    No-op when the DB is disabled.
    """
    if not db_engine.db_enabled or db_engine.async_session is None:
        return
    try:
        async with db_engine.async_session() as session:
            row_id = (
                await session.execute(
                    sa.select(LLMInteraction.id)
                    .where(LLMInteraction.session_id == session_id)
                    .order_by(LLMInteraction.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if row_id is None:
                return
            await session.execute(
                sa.update(LLMInteraction)
                .where(LLMInteraction.id == row_id)
                .values(user_rating=rating, user_comment=comment)
            )
            await session.commit()
    except Exception:
        logger.exception("Failed to update llm_interaction feedback (non-fatal)")
