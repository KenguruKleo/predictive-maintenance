"""Focused tests for watchdog recovery behavior."""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import triggers.timer_watchdog as timer_watchdog  # noqa: E402

WATCHDOG_FN = timer_watchdog._run_watchdog


class FakeDurableClient:
    def __init__(self, statuses: dict[str, object | None]) -> None:
        self._statuses = statuses
        self.calls: list[str] = []

    async def get_status(self, instance_id: str):
        self.calls.append(instance_id)
        return self._statuses.get(instance_id)


def run_watchdog(client: FakeDurableClient) -> None:
    asyncio.run(
        WATCHDOG_FN(
            timer=SimpleNamespace(past_due=False),
            client=client,
        )
    )


def test_reconstruct_alert_payload_preserves_core_incident_fields() -> None:
    payload = timer_watchdog._reconstruct_alert_payload(
        {
            "id": "INC-2026-0109",
            "equipmentId": "GR-204",
            "batchId": "B-42",
            "alert_id": "ALERT-123",
            "severity": "major",
            "created_at": "2026-04-28T10:00:00Z",
            "title": "Granulator pressure excursion",
            "parameter": "pressure",
            "upper_limit": 7.5,
        }
    )

    assert payload == {
        "id": "INC-2026-0109",
        "incident_id": "INC-2026-0109",
        "incidentId": "INC-2026-0109",
        "equipment_id": "GR-204",
        "equipmentId": "GR-204",
        "severity": "major",
        "status": "open",
        "reported_at": "2026-04-28T10:00:00Z",
        "createdAt": "2026-04-28T10:00:00Z",
        "updatedAt": "2026-04-28T10:00:00Z",
        "equipment_name": "Granulator pressure excursion",
        "equipment_criticality": "unknown",
        "equipment_type": "unknown",
        "location": "unknown",
        "title": "Granulator pressure excursion",
        "parameter": "pressure",
        "upper_limit": 7.5,
        "alert_id": "ALERT-123",
        "source_alert_id": "ALERT-123",
        "batch_id": "B-42",
    }


def test_watchdog_recovers_orphaned_approval_when_durable_completed(monkeypatch) -> None:
    published: list[dict] = []
    incident = {
        "id": "INC-2026-0201",
        "status": "pending_approval",
        "equipment_id": "MIX-102",
        "title": "Mixer vibration high",
        "reported_at": "2026-04-28T10:00:00Z",
    }

    monkeypatch.setattr(timer_watchdog, "_query_stuck_incidents", lambda threshold_seconds: [])
    monkeypatch.setattr(timer_watchdog, "_query_orphaned_approvals", lambda: [incident])
    monkeypatch.setattr(timer_watchdog, "publish_alert", lambda payload: published.append(payload))
    monkeypatch.setattr(timer_watchdog, "_MAX_RECOVER_PER_RUN", 10)

    client = FakeDurableClient(
        {"durable-INC-2026-0201": SimpleNamespace(runtime_status="Completed")}
    )

    run_watchdog(client)

    assert client.calls == ["durable-INC-2026-0201"]
    assert published == [
        {
            "id": "INC-2026-0201",
            "incident_id": "INC-2026-0201",
            "incidentId": "INC-2026-0201",
            "equipment_id": "MIX-102",
            "equipmentId": "MIX-102",
            "severity": "critical",
            "status": "open",
            "reported_at": "2026-04-28T10:00:00Z",
            "createdAt": "2026-04-28T10:00:00Z",
            "updatedAt": "2026-04-28T10:00:00Z",
            "equipment_name": "Mixer vibration high",
            "equipment_criticality": "unknown",
            "equipment_type": "unknown",
            "location": "unknown",
            "title": "Mixer vibration high",
        }
    ]


def test_watchdog_recovers_orphaned_approval_when_durable_is_missing(monkeypatch) -> None:
    published: list[dict] = []
    incident = {
        "id": "INC-2026-0203",
        "status": "pending_approval",
        "equipment_id": "MIX-103",
        "title": "Mixer torque deviation",
        "reported_at": "2026-04-28T10:30:00Z",
    }

    monkeypatch.setattr(timer_watchdog, "_query_stuck_incidents", lambda threshold_seconds: [])
    monkeypatch.setattr(timer_watchdog, "_query_orphaned_approvals", lambda: [incident])
    monkeypatch.setattr(timer_watchdog, "publish_alert", lambda payload: published.append(payload))
    monkeypatch.setattr(timer_watchdog, "_MAX_RECOVER_PER_RUN", 10)

    client = FakeDurableClient({})

    run_watchdog(client)

    assert client.calls == ["durable-INC-2026-0203"]
    assert published == [
        {
            "id": "INC-2026-0203",
            "incident_id": "INC-2026-0203",
            "incidentId": "INC-2026-0203",
            "equipment_id": "MIX-103",
            "equipmentId": "MIX-103",
            "severity": "critical",
            "status": "open",
            "reported_at": "2026-04-28T10:30:00Z",
            "createdAt": "2026-04-28T10:30:00Z",
            "updatedAt": "2026-04-28T10:30:00Z",
            "equipment_name": "Mixer torque deviation",
            "equipment_criticality": "unknown",
            "equipment_type": "unknown",
            "location": "unknown",
            "title": "Mixer torque deviation",
        }
    ]


def test_watchdog_recovers_stuck_incident_when_durable_is_missing(monkeypatch) -> None:
    published: list[dict] = []
    incident = {
        "id": "INC-2026-0204",
        "status": "analyzing",
        "equipment_id": "DRY-303",
        "title": "Dryer inlet temperature low",
        "reported_at": "2026-04-28T11:30:00Z",
    }

    monkeypatch.setattr(timer_watchdog, "_query_stuck_incidents", lambda threshold_seconds: [incident])
    monkeypatch.setattr(timer_watchdog, "_query_orphaned_approvals", lambda: [])
    monkeypatch.setattr(timer_watchdog, "publish_alert", lambda payload: published.append(payload))
    monkeypatch.setattr(timer_watchdog, "_MAX_RECOVER_PER_RUN", 10)

    client = FakeDurableClient({})

    run_watchdog(client)

    assert client.calls == ["durable-INC-2026-0204"]
    assert published == [
        {
            "id": "INC-2026-0204",
            "incident_id": "INC-2026-0204",
            "incidentId": "INC-2026-0204",
            "equipment_id": "DRY-303",
            "equipmentId": "DRY-303",
            "severity": "critical",
            "status": "open",
            "reported_at": "2026-04-28T11:30:00Z",
            "createdAt": "2026-04-28T11:30:00Z",
            "updatedAt": "2026-04-28T11:30:00Z",
            "equipment_name": "Dryer inlet temperature low",
            "equipment_criticality": "unknown",
            "equipment_type": "unknown",
            "location": "unknown",
            "title": "Dryer inlet temperature low",
        }
    ]


def test_watchdog_skips_stuck_incident_with_live_durable_instance(monkeypatch) -> None:
    published: list[dict] = []
    incident = {
        "id": "INC-2026-0202",
        "status": "analyzing",
        "equipment_id": "MIX-204",
        "title": "Granulator drift",
        "reported_at": "2026-04-28T11:00:00Z",
    }

    monkeypatch.setattr(timer_watchdog, "_query_stuck_incidents", lambda threshold_seconds: [incident])
    monkeypatch.setattr(timer_watchdog, "_query_orphaned_approvals", lambda: [])
    monkeypatch.setattr(timer_watchdog, "publish_alert", lambda payload: published.append(payload))
    monkeypatch.setattr(timer_watchdog, "_MAX_RECOVER_PER_RUN", 10)

    client = FakeDurableClient(
        {"durable-INC-2026-0202": SimpleNamespace(runtime_status="Running")}
    )

    run_watchdog(client)

    assert client.calls == ["durable-INC-2026-0202"]
    assert published == []