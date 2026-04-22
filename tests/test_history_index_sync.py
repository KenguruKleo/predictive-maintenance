from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from shared.history_index import build_history_index_documents
from shared.history_index import sync_historical_incident


class _FakeSearchClient:
    def __init__(self, existing_ids=None):
        self.existing_ids = list(existing_ids or [])
        self.uploaded = []
        self.deleted = []

    def upload_documents(self, documents):
        self.uploaded.extend(documents)

    def search(self, **_kwargs):
        return [{"id": item_id} for item_id in self.existing_ids]

    def delete_documents(self, documents):
        self.deleted.extend(documents)


def test_build_history_index_documents_uses_incident_title_and_equipment(monkeypatch) -> None:
    monkeypatch.setattr("shared.history_index.embed", lambda _text: [0.1, 0.2, 0.3])

    docs = build_history_index_documents(
        {
            "id": "INC-2026-0005",
            "status": "closed",
            "approvedAt": "2026-04-20T10:00:00Z",
            "equipmentId": "GR-204",
            "title": "Spray Rate Deviation on GR-204",
            "severity": "critical",
            "reportedAt": "2026-04-20T09:00:00Z",
            "deviationType": "process_parameter_excursion",
            "ai_analysis": {
                "classification": "process_parameter_excursion",
                "risk_level": "high",
                "recommendation": "Hold batch and inspect spray nozzle.",
            },
            "finalDecision": {"action": "approved"},
        }
    )

    assert len(docs) == 1
    assert docs[0]["id"] == "INC-2026-0005-chunk-000"
    assert docs[0]["document_id"] == "INC-2026-0005"
    assert docs[0]["document_title"] == "Spray Rate Deviation on GR-204"
    assert docs[0]["equipment_ids"] == ["GR-204"]
    assert docs[0]["document_type"] == "incident_history"


def test_sync_historical_incident_upserts_rejected_status_incident(monkeypatch) -> None:
    """Rejected-status incidents (false positives) must be indexed too."""
    fake_client = _FakeSearchClient(existing_ids=[])
    monkeypatch.setattr("shared.history_index._get_search_client", lambda: fake_client)
    monkeypatch.setattr("shared.history_index.embed", lambda text: [0.0] * 3)

    result = sync_historical_incident(
        {
            "id": "INC-2026-0005",
            "status": "rejected",
            "title": "Spray Rate Deviation on GR-204",
            "reported_at": "2026-04-16T09:00:00Z",
            "lastDecision": {"action": "rejected", "reason": "Transient sensor spike"},
        }
    )

    assert result["action"] == "upserted"
    assert result["human_decision"] == "rejected"
    assert len(fake_client.uploaded) == 1
    assert "HUMAN DECISION: REJECTED" in fake_client.uploaded[0]["text"]


def test_sync_historical_incident_deletes_non_final_docs(monkeypatch) -> None:
    """Open/pending incidents that are not finalized should be removed from the index."""
    fake_client = _FakeSearchClient(existing_ids=["INC-2026-0006-chunk-000"])
    monkeypatch.setattr("shared.history_index._get_search_client", lambda: fake_client)

    result = sync_historical_incident(
        {
            "id": "INC-2026-0006",
            "status": "pending_approval",
            "title": "Pending incident",
        }
    )

    assert result["action"] == "deleted"
    assert result["count"] == 1
    assert fake_client.deleted == [{"id": "INC-2026-0006-chunk-000"}]