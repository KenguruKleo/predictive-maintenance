from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.create_search_indexes import build_index, chunk_document, get_blob_client


def test_build_index_includes_authoritative_section_fields() -> None:
    index = build_index("idx-sop-documents")
    field_names = {field.name for field in index.fields}

    assert {"section_heading", "section_key", "section_path"}.issubset(field_names)


def test_chunk_document_tracks_heading_metadata_without_dropping_chunks() -> None:
    text = """
# SOP-DEV-001 — GMP Deviation Management Procedure

## 4. Deviation Classification

### 4.2 Process Parameter Excursions — Granulation

- Spray Rate: Affects binder distribution.
- Product Temperature: Monitor continuously.

### 4.3 Equipment-Related Deviations

1. Immediate: Notify maintenance team via CMMS
2. Equipment tagged out and quarantined
""".strip()

    chunks = chunk_document(text, "standard", default_section_heading="SOP-DEV-001 — GMP Deviation Management Procedure")

    assert len(chunks) >= 3
    assert any(chunk["section_key"] == "4.2" for chunk in chunks)
    assert any(chunk["section_key"] == "4.3" for chunk in chunks)

    process_chunk = next(chunk for chunk in chunks if chunk["section_key"] == "4.2")
    assert process_chunk["section_heading"] == "4.2 Process Parameter Excursions — Granulation"
    assert process_chunk["section_path"].endswith("4.2 Process Parameter Excursions — Granulation")
    assert "Spray Rate" in process_chunk["text"]


def test_chunk_document_uses_incident_summary_for_history_chunks() -> None:
    text = "Incident ID: INC-2026-0005\nRoot cause: flowmeter drift"

    chunks = chunk_document(text, "incidents", default_section_heading="Incident summary")

    assert chunks == [
        {
            "text": text,
            "section_heading": "Incident summary",
            "section_key": "incident-summary",
            "section_path": "Incident summary",
        }
    ]


def test_get_blob_client_falls_back_to_azure_webjobs_storage(monkeypatch) -> None:
    monkeypatch.delenv("AZURE_STORAGE_CONNECTION_STRING", raising=False)
    monkeypatch.setenv("AzureWebJobsStorage", "UseDevelopmentStorage=true")

    captured: dict[str, str] = {}

    class DummyBlobServiceClient:
        @staticmethod
        def from_connection_string(conn: str):
            captured["conn"] = conn
            return {"connection_string": conn}

    monkeypatch.setattr(
        "scripts.create_search_indexes.BlobServiceClient",
        DummyBlobServiceClient,
    )

    client = get_blob_client()

    assert client == {"connection_string": "UseDevelopmentStorage=true"}
    assert captured["conn"] == "UseDevelopmentStorage=true"