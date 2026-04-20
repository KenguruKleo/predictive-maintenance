from importlib import reload
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import shared.search_utils as search_utils


def test_get_search_client_falls_back_to_admin_key(monkeypatch) -> None:
    monkeypatch.delenv("AZURE_SEARCH_KEY", raising=False)
    monkeypatch.setenv("AZURE_SEARCH_ADMIN_KEY", "admin-key")

    module = reload(search_utils)
    client = module._get_search_client("idx-incident-history")

    assert module.SEARCH_KEY == "admin-key"
    assert client._credential.key == "admin-key"

    monkeypatch.delenv("AZURE_SEARCH_ADMIN_KEY", raising=False)
    reload(search_utils)


def test_search_index_returns_section_metadata(monkeypatch) -> None:
    monkeypatch.setattr(search_utils, "embed", lambda _text: [0.0])

    class DummyClient:
        def search(self, **kwargs):
            assert "section_heading" in kwargs["select"]
            assert "section_key" in kwargs["select"]
            assert "section_path" in kwargs["select"]
            return [
                {
                    "document_id": "SOP-DEV-001",
                    "document_title": "Deviation Management (SOP-DEV-001)",
                    "document_type": "sop",
                    "chunk_index": 1,
                    "section_heading": "4.2 Process Parameter Excursions — Granulation",
                    "section_key": "4.2",
                    "section_path": "SOP-DEV-001 — GMP Deviation Management Procedure > 4.2 Process Parameter Excursions — Granulation",
                    "text": "Spray Rate: Affects binder distribution.",
                    "keywords": [],
                    "source_blob": "SOP-DEV-001-Deviation-Management.md",
                    "@search.score": 0.9,
                }
            ]

    monkeypatch.setattr(search_utils, "_get_search_client", lambda _index_name: DummyClient())

    hits = search_utils.search_index("idx-sop-documents", "spray rate deviation", top_k=1)

    assert hits == [
        {
            "document_id": "SOP-DEV-001",
            "document_title": "Deviation Management (SOP-DEV-001)",
            "document_type": "sop",
            "chunk_index": 1,
            "section_heading": "4.2 Process Parameter Excursions — Granulation",
            "section_key": "4.2",
            "section_path": "SOP-DEV-001 — GMP Deviation Management Procedure > 4.2 Process Parameter Excursions — Granulation",
            "text": "Spray Rate: Affects binder distribution.",
            "keywords": [],
            "source": "SOP-DEV-001-Deviation-Management.md",
            "score": 0.9,
        }
    ]