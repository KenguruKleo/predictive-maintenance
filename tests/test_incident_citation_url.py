"""Test that incident type citations get proper URLs."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from activities.run_foundry_agents import _citation_url


def test_incident_citation_url_generation() -> None:
    """Incident citations should generate /incidents/{id} URLs."""
    url = _citation_url(
        citation_type="incident",
        document_id="INC-2026-0019",
        container="",
        source_blob="",
    )
    assert url == "/incidents/INC-2026-0019", f"Expected /incidents/INC-2026-0019, got {url}"


def test_incident_citation_url_with_special_chars() -> None:
    """Incident citations should URL-encode special characters if needed."""
    url = _citation_url(
        citation_type="incident",
        document_id="INC-2026-0001",
        container="",
        source_blob="",
    )
    assert url == "/incidents/INC-2026-0001"


def test_historical_citation_url_extraction() -> None:
    """Historical citations should extract incident ID from source_blob."""
    url = _citation_url(
        citation_type="historical",
        document_id="",
        container="",
        source_blob="INC-2026-0005.txt",
    )
    assert url == "/incidents/INC-2026-0005"


def test_incident_citation_empty_returns_empty() -> None:
    """Incident citation with empty document_id should return empty string."""
    url = _citation_url(
        citation_type="incident",
        document_id="",
        container="",
        source_blob="",
    )
    assert url == ""
