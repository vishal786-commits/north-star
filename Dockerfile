FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static
# Alembic migrations + config, and the entrypoint that applies them on boot.
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations
COPY docker-entrypoint.sh ./docker-entrypoint.sh

# Durable SQLite metrics store. Declare a volume so it survives container
# restarts when mounted (e.g. `docker run -v north-star-data:/app/data ...`).
RUN mkdir -p /app/data
VOLUME ["/app/data"]

EXPOSE 8000

# Container-level liveness — hits the cheap /health endpoint with stdlib only
# (no curl in the slim image). ECS surfaces the result to CloudWatch.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=2).status==200 else 1)"

# Entrypoint runs 'alembic upgrade head' (when DATABASE_URL is set) then execs
# uvicorn. Invoked via `sh` so it works regardless of the file's exec bit on the
# Windows build host.
CMD ["sh", "/app/docker-entrypoint.sh"]
