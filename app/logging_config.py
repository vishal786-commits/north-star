"""Structured JSON logging with per-request correlation IDs.

Logs are emitted as single-line JSON to stdout, so the ECS awslogs driver ships
them to CloudWatch Logs in a queryable shape (rather than opaque text). A
contextvar carries a request ID set by the middleware in `app.main`, so every
log line within a request correlates — and lines up with the metrics rows and
EMF metric emitted for that same request.
"""
import json
import logging
import sys
from contextvars import ContextVar

# Set per-request by the middleware in app.main; "-" outside any request
# (startup/shutdown, background threads).
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    """Render each log record as one line of JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: int = logging.INFO) -> None:
    """Install the JSON formatter on the root logger's stdout handler.

    Idempotent: clears existing handlers first so repeated calls (tests, reload)
    don't stack duplicate output.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
