from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from create_search_indexes import documents_from_incidents


class _FakeContainer:
    def __init__(self, items):
        self._items = items

    def read_all_items(self):
        return list(self._items)


class _FakeDatabase:
    def __init__(self, items):
        self._items = items

    def get_container_client(self, name: str):
        assert name == "incidents"
        return _FakeContainer(self._items)


class _FakeCosmosClient:
    def __init__(self, items):
        self._items = items

    def get_database_client(self, _name: str):
        return _FakeDatabase(self._items)


def test_documents_from_incidents_indexes_all_finalized_cases() -> None:
    docs = documents_from_incidents(
        _FakeCosmosClient(
            [
                {
                    "id": "INC-2026-0001",
                    "status": "closed",
                    "approvedAt": "2026-04-18T10:00:00Z",
                    "equipment_id": "GR-204",
                    "title": "Approved historical case",
                    "severity": "major",
                    "reported_at": "2026-04-18T09:00:00Z",
                    "deviation_type": "spray_rate",
                    "ai_analysis": {"recommendation": "Hold batch and inspect pump."},
                },
                {
                    "id": "INC-2026-0002",
                    "status": "completed",
                    "approvedBy": "qa.manager",
                    "equipment_id": "GR-204",
                    "title": "Completed approved case",
                    "severity": "major",
                    "reported_at": "2026-04-17T09:00:00Z",
                    "deviation_type": "spray_rate",
                    "ai_analysis": {"recommendation": "Recalibrate flowmeter."},
                },
                {
                    "id": "INC-2026-0003",
                    "status": "rejected",
                    "lastDecision": {"action": "rejected", "reason": "Transient sensor spike"},
                    "equipment_id": "GR-204",
                    "title": "Rejected false-positive case",
                    "severity": "major",
                    "reported_at": "2026-04-16T09:00:00Z",
                    "deviation_type": "spray_rate",
                    "ai_analysis": {"recommendation": "Investigate sensor."},
                },
                {
                    "id": "INC-2026-0004",
                    "status": "closed",
                    "equipment_id": "GR-204",
                    "title": "Closed without explicit approval signal",
                    "severity": "major",
                    "reported_at": "2026-04-15T09:00:00Z",
                    "deviation_type": "spray_rate",
                    "ai_analysis": {"recommendation": "Should still be indexed."},
                },
                {
                    "id": "INC-2026-0005",
                    "status": "open",
                    "equipment_id": "GR-204",
                    "title": "Still open",
                    "severity": "minor",
                    "reported_at": "2026-04-20T09:00:00Z",
                },
            ]
        )
    )

    filenames = {doc["filename"] for doc in docs}

    # All closed/completed/rejected are indexed
    assert filenames == {"INC-2026-0001.txt", "INC-2026-0002.txt", "INC-2026-0003.txt", "INC-2026-0004.txt"}
    # Open incident is NOT indexed
    assert "INC-2026-0005.txt" not in filenames
    # Rejected case text contains the human decision label
    rejected_doc = next(d for d in docs if d["filename"] == "INC-2026-0003.txt")
    assert "HUMAN DECISION: REJECTED" in rejected_doc["text"]
    assert "Transient sensor spike" in rejected_doc["text"]