"""Unit tests for notification API helpers and unread-state normalization."""

import json
import sys
from pathlib import Path

import azure.functions as func

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import triggers.http_notifications as http_notifications  # noqa: E402
from triggers.http_notifications import (  # noqa: E402
    _dedupe_notifications_by_incident,
    _is_visible_to_caller,
    _mark_visible_notifications_read,
    _normalize_notification,
    _notification_is_read,
    _should_surface_notification,
    mark_all_notifications_read,
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
    assert normalized["incident_status"] == "pending_approval"
    assert normalized["presentation_kind"] == "actionable"


def test_normalize_notification_prefers_live_incident_status_and_message() -> None:
    normalized = _normalize_notification(
        {
            "id": "notif-live-1",
            "incidentId": "INC-5",
            "type": "approval_required",
            "targetRole": "operator",
            "createdAt": "2026-04-20T10:00:00+00:00",
            "message": "Action required",
        },
        incident={
            "id": "INC-5",
            "status": "awaiting_agents",
            "title": "Mixer deviation",
        },
        caller_id="qa.manager",
    )

    assert normalized["title"] == "Mixer deviation"
    assert normalized["incident_status"] == "awaiting_agents"
    assert normalized["presentation_kind"] == "informational"
    assert normalized["message"] == "Additional analysis was requested; agents are preparing an updated recommendation."


def test_normalize_notification_suppresses_terminal_statuses() -> None:
    normalized = _normalize_notification(
        {
            "id": "notif-closed-1",
            "incidentId": "INC-6",
            "type": "approval_required",
            "targetRole": "operator",
            "createdAt": "2026-04-20T10:00:00+00:00",
        },
        incident={"id": "INC-6", "status": "closed"},
        caller_id="ivan.petrenko",
    )

    assert normalized is None


def test_normalize_notification_suppresses_self_requested_more_info() -> None:
    normalized = _normalize_notification(
        {
            "id": "notif-awaiting-1",
            "incidentId": "INC-7",
            "type": "approval_required",
            "targetRole": "operator",
            "createdAt": "2026-04-20T10:00:00+00:00",
        },
        incident={
            "id": "INC-7",
            "status": "awaiting_agents",
            "lastDecision": {
                "action": "more_info",
                "user_id": "ivan.petrenko",
            },
        },
        caller_id="ivan.petrenko",
    )

    assert normalized is None


def test_stale_operator_notification_is_suppressed_after_escalation() -> None:
    should_surface = _should_surface_notification(
        {
            "id": "notif-escalated-1",
            "incidentId": "INC-8",
            "targetRole": "operator",
        },
        incident={"id": "INC-8", "status": "escalated"},
        current_status="escalated",
        caller_id="ivan.petrenko",
    )

    assert should_surface is False


def test_dedupe_notifications_keeps_latest_item_per_incident() -> None:
    deduped = _dedupe_notifications_by_incident([
        {
            "id": "notif-newest",
            "incident_id": "INC-9",
            "created_at": "2026-04-20T10:05:00+00:00",
        },
        {
            "id": "notif-older",
            "incident_id": "INC-9",
            "created_at": "2026-04-20T10:00:00+00:00",
        },
        {
            "id": "notif-other",
            "incident_id": "INC-10",
            "created_at": "2026-04-20T09:55:00+00:00",
        },
    ])

    assert [item["id"] for item in deduped] == ["notif-newest", "notif-other"]


def test_notification_is_read_when_timestamp_or_flag_present() -> None:
    assert _notification_is_read({"isRead": True}) is True
    assert _notification_is_read({"readAt": "2026-04-20T10:00:00+00:00"}) is True
    assert _notification_is_read({"status": "read"}) is True
    assert _notification_is_read({"status": "pending"}) is False


def test_mark_visible_notifications_read_updates_only_visible_unread_items() -> None:
    now_iso = "2026-04-20T10:00:00+00:00"
    visible_unread = {
        "id": "notif-1",
        "incidentId": "INC-1",
        "targetRole": "operator",
        "assignedTo": "ivan.petrenko",
        "status": "unread",
    }
    hidden_unread = {
        "id": "notif-2",
        "incidentId": "INC-2",
        "targetRole": "operator",
        "assignedTo": "other.operator",
    }
    visible_read = {
        "id": "notif-3",
        "incidentId": "INC-3",
        "targetRole": "operator",
        "assignedTo": "ivan.petrenko",
        "isRead": True,
    }

    updated_docs, updated_ids, updated_incident_ids = _mark_visible_notifications_read(
        [visible_unread, hidden_unread, visible_read],
        "Operator",
        "ivan.petrenko",
        now_iso=now_iso,
    )

    assert updated_docs == [visible_unread]
    assert updated_ids == ["notif-1"]
    assert updated_incident_ids == ["INC-1"]
    assert visible_unread["isRead"] is True
    assert visible_unread["readAt"] == now_iso
    assert visible_unread["readBy"] == "ivan.petrenko"
    assert visible_unread["status"] == "read"
    assert "isRead" not in hidden_unread


def test_mark_all_notifications_read_returns_updated_summary(monkeypatch) -> None:
    docs = [
        {
            "id": "notif-1",
            "incidentId": "INC-1",
            "targetRole": "operator",
            "assignedTo": "ivan.petrenko",
            "status": "unread",
        },
        {
            "id": "notif-2",
            "incidentId": "INC-2",
            "targetRole": "operator",
            "assignedTo": "other.operator",
            "status": "unread",
        },
    ]
    upserted = []

    class FakeContainer:
        def query_items(self, query, parameters, enable_cross_partition_query):
            assert query == "SELECT * FROM c"
            assert parameters == []
            assert enable_cross_partition_query is True
            return docs

        def upsert_item(self, doc):
            upserted.append(doc.copy())

    monkeypatch.setattr(http_notifications, "get_caller_roles", lambda req: ["Operator"])
    monkeypatch.setattr(http_notifications, "require_any_role", lambda roles, allowed: None)
    monkeypatch.setattr(http_notifications, "get_primary_role", lambda roles: "Operator")
    monkeypatch.setattr(http_notifications, "get_caller_id", lambda req: "ivan.petrenko")
    monkeypatch.setattr(http_notifications, "get_container", lambda name: FakeContainer())

    req = func.HttpRequest(method="POST", url="http://localhost/api/notifications/read-all", body=b"")
    response = mark_all_notifications_read(req)
    payload = json.loads(response.get_body())

    assert response.status_code == 200
    assert payload["marked_read"] == 1
    assert payload["notification_ids"] == ["notif-1"]
    assert payload["incident_ids"] == ["INC-1"]
    assert len(upserted) == 1
    assert upserted[0]["isRead"] is True
    assert upserted[0]["readBy"] == "ivan.petrenko"