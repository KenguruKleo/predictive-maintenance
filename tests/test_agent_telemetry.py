"""Unit tests for App Insights incident telemetry normalization."""

import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from azure.core.exceptions import HttpResponseError

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if "azure.monitor.query" not in sys.modules:
    azure_monitor_module = sys.modules.setdefault("azure.monitor", types.ModuleType("azure.monitor"))
    azure_monitor_query_module = types.ModuleType("azure.monitor.query")

    class _DummyLogsQueryClient:  # pragma: no cover - import-only stub
        def __init__(self, *_args, **_kwargs) -> None:
            pass

    class _DummyLogsQueryStatus:  # pragma: no cover - import-only stub
        SUCCESS = "SUCCESS"
        PARTIAL = "PARTIAL"

    azure_monitor_query_module.LogsQueryClient = _DummyLogsQueryClient
    azure_monitor_query_module.LogsQueryStatus = _DummyLogsQueryStatus
    azure_monitor_module.query = azure_monitor_query_module
    sys.modules["azure.monitor.query"] = azure_monitor_query_module

from shared.agent_telemetry import (  # noqa: E402
    TelemetryAccessError,
    _classify_query_error,
    _rows_from_query_tables,
    build_telemetry_summary,
    filter_telemetry_items,
    normalize_trace_rows,
)


def test_normalize_trace_rows_merges_chunks_and_builds_summary() -> None:
    rows = [
        {
            "timestamp": "2026-04-19T10:00:00Z",
            "trace_kind": "prompt_context",
            "content_type": "json",
            "round": 1,
            "chunk_index": 1,
            "chunk_count": 2,
            "metadata": '{"thread_id": "thread-1"}',
            "content": '{"incident_id": "INC-2026-0008", ',
        },
        {
            "timestamp": "2026-04-19T10:00:01Z",
            "trace_kind": "prompt_context",
            "content_type": "json",
            "round": 1,
            "chunk_index": 2,
            "chunk_count": 2,
            "metadata": '{"thread_id": "thread-1"}',
            "content": '"round": 1}',
        },
        {
            "timestamp": "2026-04-19T10:00:02Z",
            "trace_kind": "normalized_result",
            "content_type": "json",
            "round": 1,
            "chunk_index": 1,
            "chunk_count": 1,
            "metadata": '{"run_id": "run-1"}',
            "content": '{"risk_level": "HIGH"}',
        },
    ]

    items = normalize_trace_rows(rows)

    assert len(items) == 2
    assert items[0]["trace_kind"] == "prompt_context"
    assert items[0]["status"] == "started"
    assert items[0]["content"] == '{"incident_id": "INC-2026-0008", "round": 1}'
    assert items[0]["thread_id"] == "thread-1"

    assert items[1]["trace_kind"] == "normalized_result"
    assert items[1]["status"] == "completed"
    assert items[1]["run_id"] == "run-1"

    summary = build_telemetry_summary(items)
    assert summary["total_items"] == 2
    assert summary["started_items"] == 1
    assert summary["completed_items"] == 1
    assert summary["failed_items"] == 0
    assert summary["rounds"] == [1]


def test_filter_telemetry_items_applies_status_and_round() -> None:
    items = normalize_trace_rows([
        {
            "timestamp": "2026-04-19T10:00:00Z",
            "trace_kind": "prompt_context",
            "content_type": "json",
            "round": 0,
            "chunk_index": 1,
            "chunk_count": 1,
            "metadata": "{}",
            "content": "{}",
        },
        {
            "timestamp": "2026-04-19T10:01:00Z",
            "trace_kind": "normalized_result",
            "content_type": "json",
            "round": 1,
            "chunk_index": 1,
            "chunk_count": 1,
            "metadata": "{}",
            "content": '{"ok": true}',
        },
    ])

    filtered = filter_telemetry_items(items, agent_name="orchestrator", status="completed", round_number=1)

    assert len(filtered) == 1
    assert filtered[0]["trace_kind"] == "normalized_result"
    assert filtered[0]["round"] == 1


def test_normalize_trace_rows_accepts_datetime_timestamps() -> None:
    items = normalize_trace_rows([
        {
            "timestamp": datetime(2026, 4, 19, 10, 0, tzinfo=timezone.utc),
            "trace_kind": "prompt_context",
            "content_type": "json",
            "round": 0,
            "chunk_index": 1,
            "chunk_count": 1,
            "metadata": "{}",
            "content": "{}",
        },
    ])

    assert len(items) == 1
    assert items[0]["timestamp"] == "2026-04-19T10:00:00+00:00"


def test_classify_query_error_maps_insufficient_access() -> None:
    exc = HttpResponseError(
        message="(InsufficientAccessError) The provided credentials have insufficient access to perform the requested operation"
    )

    classified = _classify_query_error(exc)

    assert isinstance(classified, TelemetryAccessError)
    assert "Application Insights resource" in str(classified)


def test_classify_query_error_falls_back_to_runtime_error() -> None:
    exc = HttpResponseError(message="Some other Azure Monitor failure")

    classified = _classify_query_error(exc)

    assert type(classified) is RuntimeError
    assert str(classified) == "Failed to query App Insights telemetry"


def test_rows_from_query_tables_accepts_string_column_names() -> None:
    table = SimpleNamespace(
        columns=["timestamp", "trace_kind", "content"],
        rows=[["2026-04-19T10:00:00Z", "prompt_context", "{}"]],
    )

    rows = _rows_from_query_tables([table])

    assert rows == [{
        "timestamp": "2026-04-19T10:00:00Z",
        "trace_kind": "prompt_context",
        "content": "{}",
    }]