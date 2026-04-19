"""Unit tests for App Insights incident telemetry normalization."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from shared.agent_telemetry import (  # noqa: E402
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