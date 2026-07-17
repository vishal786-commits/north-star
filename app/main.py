import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles

from app import session
from app.logging_config import request_id_var, setup_logging
from app.metrics import init_db
from app.routes import router

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the SQLite metrics tables if they don't exist yet.
    init_db()
    # Ping Redis once at boot — warn loudly but don't crash if it's unreachable
    # (sessions and the rate limiter degrade rather than take the app down).
    try:
        await session.redis_client.ping()
        logger.info("Redis reachable at startup")
    except Exception:
        logger.warning("Redis ping failed at startup — sessions/rate-limit degraded", exc_info=True)
    yield


app = FastAPI(title="North Star", lifespan=lifespan)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    # Reuse an inbound X-Request-ID (e.g. from the ALB / a caller) or mint one,
    # so every log line and the response carry the same correlation ID.
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    token = request_id_var.set(rid)
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)
    response.headers["X-Request-ID"] = rid
    return response


app.include_router(router, prefix="/api")


@app.get("/health")
def health():
    """Cheap liveness probe — the process is up. Does not touch dependencies."""
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    """Readiness probe — verifies Redis is reachable so a load balancer can stop
    routing to an instance whose session store is down."""
    try:
        await session.redis_client.ping()
    except Exception as e:
        logger.warning("Readiness check failed: Redis unreachable", exc_info=True)
        raise HTTPException(status_code=503, detail="Redis unavailable") from e
    return {"status": "ready"}


# MUST be registered last — this catch-all mount at "/" would otherwise swallow
# /api, /health and /ready. It serves the single-page frontend (static/index.html).
app.mount("/", StaticFiles(directory="static", html=True), name="static")
