"""Endpoint tests: rate limit + input guardrails, with Redis and OpenAI faked."""
import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

from app import config, metrics, ratelimit, routes, session
from app.main import app
from tests.conftest import sample_analysis, sample_fit

PDF = ("resume.pdf", b"%PDF-1.4 fake pdf bytes", "application/pdf")


@pytest.fixture
def client(monkeypatch):
    # One in-memory Redis shared by the limiter and the session store.
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(ratelimit, "redis_client", r)
    monkeypatch.setattr(session, "redis_client", r)

    # No real PDF parsing or OpenAI calls.
    monkeypatch.setattr(routes, "extract_resume", lambda b: ("resume text", 1))

    async def fake_analyze(text, pages, market="india_modern"):
        return sample_analysis(), {"model": "test"}

    async def fake_fit(text, pages, jd, market="india_modern"):
        return sample_fit(), {"model": "test"}

    monkeypatch.setattr(routes, "analyze_resume", fake_analyze)
    monkeypatch.setattr(routes, "analyze_fit", fake_fit)
    monkeypatch.setattr(metrics, "record_event", lambda **k: None)

    with TestClient(app) as c:
        yield c


def test_sixth_request_across_analyze_and_fit_is_rate_limited(client):
    # Shared daily budget of 5 across /analyze + /fit for the same IP.
    for _ in range(3):
        assert client.post("/api/analyze", files={"file": PDF}).status_code == 200
    for _ in range(2):
        r = client.post("/api/fit", files={"file": PDF},
                        data={"job_description": "a real job"})
        assert r.status_code == 200

    # 6th call — over budget regardless of which endpoint.
    blocked = client.post("/api/analyze", files={"file": PDF})
    assert blocked.status_code == 429
    assert "Daily limit" in blocked.json()["detail"]


def test_oversized_upload_rejected(client, monkeypatch):
    monkeypatch.setattr(config.settings, "max_upload_bytes", 10)
    big = ("resume.pdf", b"x" * 50, "application/pdf")
    r = client.post("/api/analyze", files={"file": big})
    assert r.status_code == 413


def test_non_pdf_rejected(client):
    r = client.post("/api/analyze",
                    files={"file": ("resume.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_overlong_chat_message_rejected(client):
    r = client.post("/api/chat",
                    json={"session_id": "whatever", "message": "x" * 5000})
    assert r.status_code == 422


def test_overlong_job_description_rejected(client, monkeypatch):
    monkeypatch.setattr(config.settings, "max_jd_chars", 20)
    r = client.post("/api/fit", files={"file": PDF},
                    data={"job_description": "x" * 100})
    assert r.status_code == 413


def test_analyze_accepts_market(client):
    r = client.post("/api/analyze", files={"file": PDF}, data={"market": "uk"})
    assert r.status_code == 200


def test_analyze_defaults_market_when_omitted(client):
    # No market field — the default applies and the request succeeds.
    r = client.post("/api/analyze", files={"file": PDF})
    assert r.status_code == 200


def test_analyze_rejects_unknown_market(client):
    r = client.post("/api/analyze", files={"file": PDF}, data={"market": "mars"})
    assert r.status_code == 400


def test_fit_rejects_unknown_market(client):
    r = client.post("/api/fit", files={"file": PDF},
                    data={"job_description": "a real job", "market": "atlantis"})
    assert r.status_code == 400
