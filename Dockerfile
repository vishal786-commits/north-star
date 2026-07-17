FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static

# Durable SQLite metrics store. Declare a volume so it survives container
# restarts when mounted (e.g. `docker run -v north-star-data:/app/data ...`).
RUN mkdir -p /app/data
VOLUME ["/app/data"]

EXPOSE 8000

# Container-level liveness — hits the cheap /health endpoint with stdlib only
# (no curl in the slim image). ECS surfaces the result to CloudWatch.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=2).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
