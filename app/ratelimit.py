"""Per-IP daily usage limiting.

Caps each client IP to `settings.daily_ip_limit` combined /analyze + /fit
requests per calendar day (UTC), backed by the same Redis the session store
uses. Deliberately FAILS OPEN on Redis errors: a cache outage should not take
the whole tool offline — a cost cap matters less than availability.
"""
import logging
from datetime import datetime, timezone

import redis.asyncio as redis
from fastapi import HTTPException, Request

from app.config import settings
from app.session import redis_client  # reuse the existing async client

logger = logging.getLogger(__name__)

# Key TTL: 48h comfortably covers the day-long window plus slack, so a stale
# counter never lingers even though we key by the calendar date.
_KEY_TTL_SECONDS = 60 * 60 * 48


def _key(ip: str) -> str:
    return f"ratelimit:{ip}:{datetime.now(timezone.utc):%Y-%m-%d}"


def get_client_ip(request: Request) -> str:
    """Best-effort real client IP.

    Behind a load balancer, `request.client.host` is the LB, not the visitor —
    the real IP rides in `X-Forwarded-For`. The leftmost XFF entry is
    client-controlled (spoofable), so we count `trusted_proxy_hops` from the
    RIGHT to land on the first address our own infrastructure appended.
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            hops = settings.trusted_proxy_hops
            if len(parts) >= hops:
                return parts[-hops]
            return parts[0]
    return request.client.host if request.client else "unknown"


async def check_and_increment(ip: str) -> tuple[bool, int]:
    """Count this request against the IP's daily budget.

    Returns (allowed, remaining). Fails OPEN (allowed=True) on any Redis error.
    """
    key = _key(ip)
    try:
        count = await redis_client.incr(key)
        if count == 1:
            # First hit today — start the expiry clock.
            await redis_client.expire(key, _KEY_TTL_SECONDS)
        allowed = count <= settings.daily_ip_limit
        return allowed, max(0, settings.daily_ip_limit - count)
    except redis.RedisError:
        logger.warning("rate-limit check failed; failing open", exc_info=True)
        return True, settings.daily_ip_limit


async def enforce_daily_limit(request: Request) -> None:
    """FastAPI dependency: reject over-budget IPs before any OpenAI spend."""
    ip = get_client_ip(request)
    allowed, remaining = await check_and_increment(ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Daily limit reached. You can analyze up to "
                f"{settings.daily_ip_limit} resumes per day. Please try again tomorrow."
            ),
            headers={"Retry-After": "86400"},
        )
    request.state.rate_remaining = remaining
