"""Unit tests for notification API helpers and unread-state normalization."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from triggers.http_notifications import (  # noqa: E402
    _is_visible_to_caller,
    _normalize_notification,
    _notification_is_read,
)


def test_operator_only_sees_notifications_assigned_to_them() -> None:
    visible_doc = {
        "id": "notif-1",
        "incidentId": "INC-1",
        "targetRole": "operator",
        "assignedTo": "ivan.petrenko",
    }
    hidden_doc = {
        "id": "notif-2",
        "incidentId": "INC-2",
        "targetRole": "operator",
        "assignedTo": "other.operator",
    }

    assert _is_visible_to_caller(visible_doc, "Operator", "ivan.petrenko") is True
    assert _is_visible_to_caller(hidden_doc, "Operator", "ivan.petrenko") is False


def test_qamanager_sees_escalation_notifications() -> None:
    doc = {
        "id": "notif-qa-1",
        "incidentId": "INC-3",
        "targetRole": "qa-manager",
    }

    assert _is_visible_to_caller(doc, "QAManager", "qa.manager") is True


def test_normalize_notification_defaults_legacy_items_to_unread() -> None:
    normalized = _normalize_notification({
        "id": "notif-legacy-1",
        "incidentId": "INC-4",
        "type": "approval_required",
        "message": "Action required",
        "targetRole": "operator",
        "createdAt": "2026-04-20T10:00:00+00:00",
    })

    assert normalized["incident_id"] == "INC-4"
    assert normalized["is_read"] is False
    assert normalized["created_at"] == "2026-04-20T10:00:00+00:00"


def test_notification_is_read_when_timestamp_or_flag_present() -> None:
    assert _notification_is_read({"isRead": True}) is True
    assert _notification_is_read({"readAt": "2026-04-20T10:00:00+00:00"}) is True
    assert _notification_is_read({"status": "read"}) is True
    assert _notification_is_read({"status": "pending"}) is False