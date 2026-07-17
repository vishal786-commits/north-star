"""CloudWatch Embedded Metric Format (EMF) emission.

We print one EMF JSON line per request event to stdout. In ECS the awslogs
driver ships it to CloudWatch Logs, which parses the `_aws` block and
auto-publishes the named metrics under the `NorthStar` namespace — no boto3, no
`PutMetricData` IAM, and no network call in the request path. This keeps the app
cloud-agnostic: locally the line is just harmless JSON on stdout.

Emission is best-effort: a failure here must never affect the user response or
the durable SQLite metrics write, so everything is wrapped and swallowed.

Reference: AWS "Specification: Embedded Metric Format".
"""
import json
import logging
import sys
import time

logger = logging.getLogger(__name__)

NAMESPACE = "NorthStar"

# gpt-4o-mini pricing (USD per 1M tokens). Mirrors app/metrics._COST_PER_M so
# the CloudWatch cost metric and the dashboard aggregate agree.
_COST_PER_M = {"prompt": 0.15, "completion": 0.60}

# CloudWatch unit for each metric we may publish.
_METRIC_UNITS = {
    "RequestCount": "Count",
    "ErrorCount": "Count",
    "LatencyTotalMs": "Milliseconds",
    "LatencyLlmMs": "Milliseconds",
    "ExtractMs": "Milliseconds",
    "PromptTokens": "Count",
    "CompletionTokens": "Count",
    "TotalTokens": "Count",
    "EstCostUsd": "None",
}


def _est_cost_usd(prompt_tokens: int | None, completion_tokens: int | None) -> float:
    return round(
        (prompt_tokens or 0) / 1_000_000 * _COST_PER_M["prompt"]
        + (completion_tokens or 0) / 1_000_000 * _COST_PER_M["completion"],
        6,
    )


def emit_emf(
    *,
    kind: str,
    status: str,
    market: str | None = None,
    model: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    extract_ms: float | None = None,
    llm_ms: float | None = None,
    total_ms: float | None = None,
    **_ignored,
) -> None:
    """Print one EMF metric line describing a single request event.

    Each metric is published against two dimension sets: the empty set (a fleet
    aggregate across the whole service, which alarms and dashboard totals read)
    and ["Kind"] (per-endpoint slicing: review / fit / chat). Keeping the
    dimension sets small bounds custom-metric cost. Status/Market/Model ride
    along as context properties — queryable in CloudWatch Logs Insights without
    multiplying the metric count. Extra keyword arguments (session_id,
    page_count, score, error_detail, …) are accepted and ignored, so this can be
    called with the same fields as `metrics.record_event`.
    """
    try:
        values = {
            "RequestCount": 1,
            "ErrorCount": 1 if status == "error" else 0,
            "EstCostUsd": _est_cost_usd(prompt_tokens, completion_tokens),
        }
        for name, value in (
            ("LatencyTotalMs", total_ms),
            ("LatencyLlmMs", llm_ms),
            ("ExtractMs", extract_ms),
            ("PromptTokens", prompt_tokens),
            ("CompletionTokens", completion_tokens),
            ("TotalTokens", total_tokens),
        ):
            if value is not None:
                values[name] = value

        # Context properties (not metric dimensions — no cost multiplier).
        context = {"Kind": kind, "Status": status}
        if market:
            context["Market"] = market
        if model:
            context["Model"] = model

        doc = {
            "_aws": {
                "Timestamp": int(time.time() * 1000),
                "CloudWatchMetrics": [
                    {
                        "Namespace": NAMESPACE,
                        "Dimensions": [[], ["Kind"]],
                        "Metrics": [
                            {"Name": name, "Unit": _METRIC_UNITS[name]} for name in values
                        ],
                    }
                ],
            },
            **context,
            **values,
        }
        # Write the EMF document as its own raw line — NOT through the logging
        # formatter, which would nest it under a "message" field and break the
        # CloudWatch EMF parser.
        sys.stdout.write(json.dumps(doc) + "\n")
    except Exception:
        logger.exception("Failed to emit EMF metric (non-fatal)")
