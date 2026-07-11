"""Durable monitoring store (SQLite).

Every analysis/fit/chat request writes one row to `events`; every 👍/👎 writes to
`feedback`. Aggregates power the dashboard. Writes are best-effort — a metrics
failure must never break the user-facing response (callers wrap accordingly, and
the write helpers also swallow-and-log).

SQLite is blocking, so callers offload via asyncio.to_thread. Rows are tiny.
"""

import logging
import os
import sqlite3
import time
from contextlib import contextmanager

from app.config import settings

logger = logging.getLogger(__name__)

DB_PATH = settings.metrics_db_path


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the metrics tables if they don't exist. Safe to call on every boot."""
    parent = os.path.dirname(DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at        REAL NOT NULL,
                kind              TEXT NOT NULL,          -- review | fit | chat
                session_id        TEXT,
                market            TEXT,                   -- india_modern | india_traditional | uk | us_global
                model             TEXT,
                page_count        INTEGER,
                resume_chars      INTEGER,
                prompt_tokens     INTEGER,
                completion_tokens INTEGER,
                total_tokens      INTEGER,
                extract_ms        REAL,
                llm_ms            REAL,
                total_ms          REAL,
                score             INTEGER,               -- ats overall | fit match_score
                status            TEXT NOT NULL,          -- ok | error
                error_detail      TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);
            CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);

            CREATE TABLE IF NOT EXISTS feedback (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  REAL NOT NULL,
                session_id  TEXT,
                rating      TEXT NOT NULL,               -- up | down
                comment     TEXT
            );
            """
        )
        # Additive migration for DBs created before the `market` column existed.
        # CREATE TABLE IF NOT EXISTS won't add columns to a pre-existing table.
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(events)").fetchall()}
        if "market" not in cols:
            conn.execute("ALTER TABLE events ADD COLUMN market TEXT")
    logger.info("Metrics DB ready at %s", DB_PATH)


# ---- writes (best-effort) --------------------------------------------------

def record_event(
    *,
    kind: str,
    status: str,
    session_id: str | None = None,
    market: str | None = None,
    model: str | None = None,
    page_count: int | None = None,
    resume_chars: int | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    extract_ms: float | None = None,
    llm_ms: float | None = None,
    total_ms: float | None = None,
    score: int | None = None,
    error_detail: str | None = None,
) -> None:
    try:
        with _connect() as conn:
            conn.execute(
                """INSERT INTO events (
                    created_at, kind, session_id, market, model, page_count, resume_chars,
                    prompt_tokens, completion_tokens, total_tokens,
                    extract_ms, llm_ms, total_ms, score, status, error_detail
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    time.time(), kind, session_id, market, model, page_count, resume_chars,
                    prompt_tokens, completion_tokens, total_tokens,
                    extract_ms, llm_ms, total_ms, score, status, error_detail,
                ),
            )
    except Exception:
        logger.exception("Failed to record metrics event (non-fatal)")


def record_feedback(*, session_id: str, rating: str, comment: str | None) -> None:
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO feedback (created_at, session_id, rating, comment) VALUES (?,?,?,?)",
                (time.time(), session_id, rating, comment),
            )
    except Exception:
        logger.exception("Failed to record feedback (non-fatal)")


# ---- reads (aggregates) ----------------------------------------------------

def _percentile(values: list[float], pct: float) -> float | None:
    """Nearest-rank percentile. `pct` in [0,1]."""
    if not values:
        return None
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, round(pct * (len(ordered) - 1))))
    return round(ordered[k], 1)


# gpt-4o-mini pricing (USD per 1M tokens) for a rough cost estimate.
_COST_PER_M = {"prompt": 0.15, "completion": 0.60}


def get_metrics() -> dict:
    """Aggregate everything the dashboard needs in one pass."""
    with _connect() as conn:
        events = [dict(r) for r in conn.execute("SELECT * FROM events").fetchall()]
        feedback = [dict(r) for r in conn.execute("SELECT * FROM feedback").fetchall()]

    total = len(events)
    errors = [e for e in events if e["status"] == "error"]
    ok = [e for e in events if e["status"] == "ok"]

    by_kind: dict[str, int] = {}
    for e in events:
        by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + 1

    total_ms = [e["total_ms"] for e in ok if e["total_ms"] is not None]
    llm_ms = [e["llm_ms"] for e in ok if e["llm_ms"] is not None]

    prompt_tok = sum(e["prompt_tokens"] or 0 for e in ok)
    completion_tok = sum(e["completion_tokens"] or 0 for e in ok)
    total_tok = sum(e["total_tokens"] or 0 for e in ok)
    est_cost = round(
        prompt_tok / 1_000_000 * _COST_PER_M["prompt"]
        + completion_tok / 1_000_000 * _COST_PER_M["completion"],
        4,
    )

    # Score distribution buckets (0-59 / 60-79 / 80-100) over review + fit.
    buckets = {"low (0-59)": 0, "mid (60-79)": 0, "high (80-100)": 0}
    for e in ok:
        s = e["score"]
        if s is None:
            continue
        if s < 60:
            buckets["low (0-59)"] += 1
        elif s < 80:
            buckets["mid (60-79)"] += 1
        else:
            buckets["high (80-100)"] += 1

    up = sum(1 for f in feedback if f["rating"] == "up")
    down = sum(1 for f in feedback if f["rating"] == "down")
    recent_comments = [
        {"comment": f["comment"], "rating": f["rating"]}
        for f in sorted(feedback, key=lambda f: f["created_at"], reverse=True)
        if f["comment"]
    ][:10]

    return {
        "totals": {
            "events": total,
            "by_kind": by_kind,
            "errors": len(errors),
            "error_rate": round(len(errors) / total, 3) if total else 0,
        },
        "latency_ms": {
            "total_p50": _percentile(total_ms, 0.5),
            "total_p95": _percentile(total_ms, 0.95),
            "llm_p50": _percentile(llm_ms, 0.5),
            "llm_p95": _percentile(llm_ms, 0.95),
        },
        "tokens": {
            "prompt": prompt_tok,
            "completion": completion_tok,
            "total": total_tok,
            "avg_per_event": round(total_tok / len(ok), 1) if ok else 0,
            "est_cost_usd": est_cost,
        },
        "score_distribution": buckets,
        "feedback": {
            "up": up,
            "down": down,
            "total": up + down,
            "positive_rate": round(up / (up + down), 3) if (up + down) else None,
            "recent_comments": recent_comments,
        },
    }
