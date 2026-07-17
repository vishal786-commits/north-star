"""EMF metric emission tests — verify the CloudWatch Embedded Metric Format
document shape without touching AWS (emit_emf just writes JSON to stdout)."""
import io
import json
from contextlib import redirect_stdout

from app.observability import emit_emf


def _capture(**kwargs) -> dict:
    buf = io.StringIO()
    with redirect_stdout(buf):
        emit_emf(**kwargs)
    return json.loads(buf.getvalue())


def test_emf_basic_shape_and_cost():
    doc = _capture(
        kind="review", status="ok", market="uk", model="gpt-4o-mini",
        prompt_tokens=1000, completion_tokens=500, total_tokens=1500,
        extract_ms=10.0, llm_ms=800.0, total_ms=850.0,
    )
    cw = doc["_aws"]["CloudWatchMetrics"][0]
    assert cw["Namespace"] == "NorthStar"
    # Aggregate set (alarms/totals) plus per-endpoint slicing.
    assert cw["Dimensions"] == [[], ["Kind"]]
    assert doc["Kind"] == "review"
    assert doc["RequestCount"] == 1
    assert doc["ErrorCount"] == 0
    assert doc["TotalTokens"] == 1500
    assert doc["EstCostUsd"] == round(1000 / 1_000_000 * 0.15 + 500 / 1_000_000 * 0.60, 6)
    names = {m["Name"] for m in cw["Metrics"]}
    assert {"RequestCount", "ErrorCount", "EstCostUsd", "TotalTokens", "LatencyTotalMs"} <= names


def test_emf_error_status_sets_error_count():
    doc = _capture(kind="fit", status="error")
    assert doc["RequestCount"] == 1
    assert doc["ErrorCount"] == 1


def test_emf_omits_absent_metrics_and_ignores_extra_kwargs():
    # Called with the same surplus fields metrics.record_event passes through.
    doc = _capture(kind="chat", status="ok", session_id="ignored", score=80, error_detail=None)
    names = {m["Name"] for m in doc["_aws"]["CloudWatchMetrics"][0]["Metrics"]}
    assert "LatencyTotalMs" not in names
    assert "TotalTokens" not in names
    assert {"RequestCount", "ErrorCount", "EstCostUsd"} <= names
    # Surplus kwargs are accepted but never surface as metric/context fields.
    assert "session_id" not in doc
    assert "score" not in doc
