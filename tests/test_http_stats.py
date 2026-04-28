"""Unit tests for manager dashboard stats helpers."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from triggers.http_stats import _build_recent_decisions  # noqa: E402


def test_build_recent_decisions_returns_latest_finalized_items() -> None:
    rows = [
        {
            "id": "INC-3",
            "incident_number": "INC-2026-0003",
            "createdAt": "2026-04-20T08:00:00Z",
            "closedAt": "2026-04-20T09:30:00Z",
            "confidence": 0.52,
            "operatorAgreesWithAgent": False,
            "finalDecision": {
                "action": "approved",
                "role": "qa-manager",
                "user_id": "qa.manager@contoso.com",
            },
        },
        {
            "id": "INC-2",
            "incident_number": "INC-2026-0002",
            "createdAt": "2026-04-20T07:00:00Z",
            "closedAt": "2026-04-20T08:00:00Z",
            "confidence": 0.71,
            "operatorAgreesWithAgent": True,
            "finalDecision": {
                "action": "rejected",
                "role": "operator",
                "user_id": "anna.koval@contoso.com",
            },
        },
        {
            "id": "INC-1",
            "incident_number": "INC-2026-0001",
            "createdAt": "2026-04-20T06:00:00Z",
            "closedAt": "2026-04-20T06:15:00Z",
            "confidence": 0.84,
            "operatorAgreesWithAgent": True,
            "finalDecision": {
                "action": "approved",
                "role": "operator",
                "user_id": "ivan.petrenko@contoso.com",
            },
        },
        {
            "id": "INC-skip",
            "incident_number": "INC-2026-9999",
            "createdAt": "2026-04-20T05:00:00Z",
            "closedAt": "2026-04-20T05:30:00Z",
            "confidence": 0.65,
            "finalDecision": {
                "action": "more_info",
                "role": "operator",
                "user_id": "skip.user@contoso.com",
            },
        },
    ]

    result = _build_recent_decisions(rows)

    assert [item["incident_id"] for item in result] == ["INC-3", "INC-2", "INC-1"]
    assert result[0]["operator"] == "QA Manager"
    assert result[0]["human_override"] is True
    assert result[0]["response_time_minutes"] == 90
    assert result[1]["operator"] == "Anna Koval"
    assert result[1]["decision"] == "rejected"
    assert result[2]["ai_confidence"] == 0.84


def test_build_recent_decisions_ignores_items_without_closed_timestamp() -> None:
    rows = [
        {
            "id": "INC-open",
            "incident_number": "INC-2026-1234",
            "createdAt": "2026-04-20T06:00:00Z",
            "confidence": 0.9,
            "finalDecision": {
                "action": "approved",
                "role": "operator",
                "user_id": "ivan.petrenko@contoso.com",
            },
        }
    ]

    assert _build_recent_decisions(rows) == []