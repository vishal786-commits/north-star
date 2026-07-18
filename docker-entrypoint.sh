#!/bin/sh
set -e

# Apply database migrations before boot when a Postgres URL is configured.
# Alembic is idempotent — re-running against an up-to-date DB is a no-op.
#
# NOTE: concurrent multi-task rollouts race here. That's fine for a single
# service; if you scale to several tasks applying migrations at once, wrap this
# in a Postgres advisory lock (SELECT pg_advisory_lock(...)) or run migrations
# as a dedicated one-off task instead.
if [ -n "$DATABASE_URL" ]; then
  echo "DATABASE_URL set — running 'alembic upgrade head'..."
  alembic upgrade head
else
  echo "DATABASE_URL not set — skipping migrations."
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'
