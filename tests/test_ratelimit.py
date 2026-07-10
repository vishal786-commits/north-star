"""Unit tests for the per-IP daily rate limiter."""
from types import SimpleNamespace

import fakeredis.aioredis
import pytest
from redis.exceptions import RedisError

from app import ratelimit
from app.config import settings


@pytest.fixture
def fake_redis(monkeypatch):
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(ratelimit, "redis_client", r)
    return r


def make_request(xff=None, client_host="10.0.0.1"):
    headers = {}
    if xff is not None:
        headers["x-forwarded-for"] = xff
    client = SimpleNamespace(host=client_host) if client_host else None
    return SimpleNamespace(headers=headers, client=client)


async def test_allows_first_five_blocks_sixth(fake_redis):
    for i in range(settings.daily_ip_limit):
        allowed, remaining = await ratelimit.check_and_increment("1.2.3.4")
        assert allowed is True
        assert remaining == settings.daily_ip_limit - (i + 1)

    allowed, remaining = await ratelimit.check_and_increment("1.2.3.4")
    assert allowed is False
    assert remaining == 0


async def test_ttl_set_on_first_hit(fake_redis):
    await ratelimit.check_and_increment("9.9.9.9")
    ttl = await fake_redis.ttl(ratelimit._key("9.9.9.9"))
    assert ttl > 0


async def test_budget_isolated_per_ip(fake_redis):
    for _ in range(settings.daily_ip_limit):
        await ratelimit.check_and_increment("1.1.1.1")
    # A different IP still has its full budget.
    allowed, remaining = await ratelimit.check_and_increment("2.2.2.2")
    assert allowed is True
    assert remaining == settings.daily_ip_limit - 1


async def test_fails_open_on_redis_error(monkeypatch):
    class BoomRedis:
        async def incr(self, *a, **k):
            raise RedisError("redis is down")

    monkeypatch.setattr(ratelimit, "redis_client", BoomRedis())
    allowed, remaining = await ratelimit.check_and_increment("x")
    assert allowed is True
    assert remaining == settings.daily_ip_limit


def test_get_client_ip_prefers_forwarded_for():
    # One trusted hop (ALB): the real client is the RIGHTMOST XFF entry, so a
    # client-spoofed leftmost value is ignored.
    req = make_request(xff="1.2.3.4, 203.0.113.9", client_host="10.0.0.1")
    assert ratelimit.get_client_ip(req) == "203.0.113.9"


def test_get_client_ip_falls_back_to_peer():
    req = make_request(xff=None, client_host="10.0.0.1")
    assert ratelimit.get_client_ip(req) == "10.0.0.1"


def test_get_client_ip_honours_hop_count(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
    # CloudFront + ALB: two appended hops → second-from-right is the client.
    req = make_request(xff="1.2.3.4, 5.6.6.6, 7.7.7.7")
    assert ratelimit.get_client_ip(req) == "5.6.6.6"


def test_get_client_ip_unknown_when_no_peer():
    req = make_request(xff=None, client_host=None)
    assert ratelimit.get_client_ip(req) == "unknown"
