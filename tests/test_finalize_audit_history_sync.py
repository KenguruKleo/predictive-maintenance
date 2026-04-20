from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from activities.finalize_audit import finalize_audit


class _FakeEventsContainer:
    def __init__(self):
        self.items = []

    def upsert_item(self, item):
        self.items.append(item)


class _FakeDatabase:
    def __init__(self):
        self.events = _FakeEventsContainer()

    def get_container_client(self, name: str):
        assert name == "incident_events"
        return self.events


class _FakeCosmosClient:
    def __init__(self, db):
        self.db = db

    def get_database_client(self, _name: str):
        return self.db


def test_finalize_audit_syncs_history_index_for_approved_incident(monkeypatch) -> None:
    db = _FakeDatabase()
    captured = {}

    monkeypatch.setattr(
        "activities.finalize_audit.get_cosmos_client",
        lambda: _FakeCosmosClient(db),
    )
    monkeypatch.setattr(
        "activities.finalize_audit.patch_incident_by_id",
        lambda database, incident_id, patch_operations: captured.setdefault(
            "patch", (database, incident_id, patch_operations)
        ),
    )
    monkeypatch.setattr(
        "activities.finalize_audit.get_incident_by_id",
        lambda _database, incident_id: {
            "id": incident_id,
            "status": "closed",
            "approvedAt": "2026-04-20T10:00:00Z",
            "equipmentId": "GR-204",
            "title": "Spray Rate Deviation on GR-204",
            "finalDecision": {"action": "approved"},
        },
    )
    monkeypatch.setattr(
        "activities.finalize_audit.sync_historical_incident",
        lambda incident: captured.setdefault("synced", incident),
    )

    result = finalize_audit(
        {
            "incident_id": "INC-2026-0005",
            "decision": {"action": "approved", "user_id": "ivan.petrenko"},
            "exec_result": {},
        }
    )

    assert result["final_status"] == "closed"
    assert captured["patch"][1] == "INC-2026-0005"
    assert captured["synced"]["id"] == "INC-2026-0005"
    assert db.events.items[0]["finalStatus"] == "closed"