import json
import logging
import uuid

import redis.asyncio as redis

from app.config import settings
from app.errors import SessionError, SessionNotFound

logger = logging.getLogger(__name__)

redis_client = redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=5, socket_connect_timeout=5)

SESSION_TTL_SECONDS = 60 * 60 #session expires after 1 hour
MESSAGE_LIMIT = 5 # limit the number of messages stored in a session to avoid excessive memory usage

def _key(session_id: str) -> str:
    return f"session:{session_id}"

async def create_session(resume_text: str, analysis, kind: str = "review", market: str = "india_modern") -> str:
    #store a new session in Redis with a unique session ID
    # `analysis` is a pydantic model (Analysis for review, FitAnalysis for fit);
    # its dump grounds the coach chat, which works for both flows.
    # `market` is persisted so the coach chat stays specific to the same target market.
    session_id = uuid.uuid4().hex
    data = {
        "resume_text": resume_text,
        "analysis": analysis.model_dump(),
        "kind": kind,
        "market": market,
        "message_count": 0,
        "history": [],
    }
    try:
        await redis_client.set(
            _key(session_id), 
            json.dumps(data), 
            ex=SESSION_TTL_SECONDS)
    except redis.RedisError as e:
        logger.exception("Failed to create session in Redis")
        raise SessionError("Could not create session") from e
    return session_id

async def get_session(session_id: str) -> dict:
    """Fetch a session's data, or raise if it's gone."""
    try:
        raw = await redis_client.get(_key(session_id))
    except redis.RedisError as e:
        logger.exception("Failed to read session")
        raise SessionError("Could not read session.") from e

    if raw is None:
        raise SessionNotFound("Session not found or expired.")

    return json.loads(raw)


async def save_session(session_id: str, data: dict) -> None:
    """Overwrite a session's data and refresh its expiry."""
    try:
        await redis_client.set(
            _key(session_id),
            json.dumps(data),
            ex=SESSION_TTL_SECONDS,   # activity resets the 1-hour clock
        )
    except redis.RedisError as e:
        logger.exception("Failed to save session")
        raise SessionError("Could not save session.") from e