"""Liveness/readiness and request-ID correlation tests, with Redis faked."""
import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

from app import session
from app.main import app


@pytest.fixture
def fake_redis(monkeypatch):
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(session, "redis_client", r)
    return r


def test_health_is_always_ok(fake_redis):
    with TestClient(app) as c:
        r = c.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


def test_ready_ok_when_redis_up(fake_redis):
    with TestClient(app) as c:
        r = c.get("/ready")
        assert r.status_code == 200
        assert r.json()["status"] == "ready"


def test_ready_503_when_redis_down(monkeypatch):
    class DownRedis:
        async def ping(self):
            raise ConnectionError("redis down")

    monkeypatch.setattr(session, "redis_client", DownRedis())
    with TestClient(app) as c:
        r = c.get("/ready")
        assert r.status_code == 503


def test_request_id_echoed_from_inbound_header(fake_redis):
    with TestClient(app) as c:
        r = c.get("/health", headers={"X-Request-ID": "abc123"})
        assert r.headers.get("X-Request-ID") == "abc123"


def test_request_id_minted_when_absent(fake_redis):
    with TestClient(app) as c:
        r = c.get("/health")
        assert r.headers.get("X-Request-ID")  # a fresh id is generated
