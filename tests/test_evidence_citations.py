from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from activities.run_foundry_agents import _normalize_evidence_citations, _trace_enabled


def test_normalize_evidence_citations_dedupes_canonical_document_identity() -> None:
    result = {
        "evidence_citations": [
            {
                "source": "SOP-DEV-001",
                "section": "§4.2",
                "text_excerpt": "Spray Rate: Affects binder distribution.",
            }
        ],
        "sop_refs": [
            {
                "id": "SOP-DEV-001",
                "title": "Deviation Management",
                "relevant_section": "§4.2",
                "text_excerpt": "Spray Rate: Affects binder distribution.",
            }
        ],
        "regulatory_refs": [
            {
                "regulation": "EU GMP Annex 15",
                "section": "§6.3",
                "text_excerpt": "The impact on product quality shall be assessed based on duration and magnitude.",
            }
        ],
    }
    rag_context = {
        "idx-sop-documents": [
            {
                "document_id": "SOP-DEV-001",
                "document_title": "Deviation Management (SOP-DEV-001)",
                "source": "SOP-DEV-001-Deviation-Management.md",
                "chunk_index": 3,
                "text": (
                    "For High-Shear Granulators (GR series): Spray Rate: Affects binder distribution. "
                    "Low spray rate increases risk of ungranulated fines. Test granule distribution at 3 sampling points."
                ),
                "score": 1.0,
            }
        ],
        "idx-gmp-policies": [
            {
                "document_id": "GMP-ANNEX15",
                "document_title": "EU GMP Annex 15",
                "source": "GMP-Annex15-Excerpt.md",
                "chunk_index": 5,
                "text": (
                    "The impact on product quality shall be assessed based on duration of excursion, "
                    "magnitude of excursion relative to validated limits, and product sensitivity."
                ),
                "score": 0.9,
            }
        ],
    }

    citations = _normalize_evidence_citations(result, rag_context)

    assert len(citations) == 2
    assert citations[0]["document_title"] == "Deviation Management (SOP-DEV-001)"
    assert citations[0]["resolution_status"] == "resolved"
    assert citations[0]["url"] == "/api/documents/blob-sop/SOP-DEV-001-Deviation-Management.md"
    assert citations[1]["document_title"] == "EU GMP Annex 15"
    assert citations[1]["resolution_status"] == "resolved"


def test_normalize_evidence_citations_flags_unresolved_instead_of_placeholder_title() -> None:
    citations = _normalize_evidence_citations(
        {
            "evidence_citations": [
                {
                    "source": "operator note about paragraph 4.2",
                    "section": "§4.2",
                    "text_excerpt": "short note",
                }
            ]
        },
        {},
    )

    assert len(citations) == 1
    assert citations[0]["type"] == "document"
    assert citations[0]["resolution_status"] == "unresolved"
    assert citations[0]["url"] == ""
    assert "link" in citations[0]["unresolved_reason"].lower()
    assert citations[0]["document_title"] == "operator note about paragraph 4.2"


def test_normalize_evidence_citations_drops_primary_incident_entries() -> None:
    citations = _normalize_evidence_citations(
        {
            "evidence_citations": [
                {
                    "type": "incident",
                    "document_id": "INC-2026-0019",
                    "source": "Incident Log",
                    "section": "Incident Details",
                    "text_excerpt": "Impeller speed dropped below the validated range.",
                },
                {
                    "document_id": "INC-2026-0019",
                    "source": "Incident Log",
                    "section": "Incident Details",
                    "text_excerpt": "Current incident context echoed back by the model.",
                },
                {
                    "type": "sop",
                    "document_id": "SOP-DEV-001",
                    "section": "§4.2",
                    "text_excerpt": "Deviation handling requires documented impact assessment.",
                },
            ]
        },
        {
            "idx-sop-documents": [
                {
                    "document_id": "SOP-DEV-001",
                    "document_title": "Deviation Management (SOP-DEV-001)",
                    "source": "SOP-DEV-001-Deviation-Management.md",
                    "chunk_index": 3,
                    "text": "Deviation handling requires documented impact assessment before disposition.",
                    "score": 0.99,
                }
            ]
        },
        current_incident_id="INC-2026-0019",
    )

    assert len(citations) == 1
    assert citations[0]["type"] == "sop"
    assert citations[0]["document_id"] == "SOP-DEV-001"


def test_normalize_evidence_citations_backfills_contextful_excerpt_from_match() -> None:
    citations = _normalize_evidence_citations(
        {
            "evidence_citations": [
                {
                    "source": "SOP-DEV-001",
                    "section": "§4.2",
                    "text_excerpt": "binder distribution",
                }
            ]
        },
        {
            "idx-sop-documents": [
                {
                    "document_id": "SOP-DEV-001",
                    "document_title": "Deviation Management (SOP-DEV-001)",
                    "source": "SOP-DEV-001-Deviation-Management.md",
                    "chunk_index": 3,
                    "text": (
                        "For High-Shear Granulators (GR series): Spray Rate: Affects binder distribution. "
                        "Low spray rate increases risk of ungranulated fines. Test granule distribution at 3 sampling points."
                    ),
                    "score": 1.0,
                }
            ]
        },
    )

    assert len(citations[0]["text_excerpt"]) > len("binder distribution")
    assert len(citations[0]["text_excerpt"]) <= 300
    assert "ungranulated fines" in citations[0]["text_excerpt"].lower()


def test_normalize_evidence_citations_canonicalizes_id_only_sop_refs_without_rag_match() -> None:
    citations = _normalize_evidence_citations(
        {
            "sop_refs": [
                {
                    "id": "SOP-DEV-001",
                    "title": "Deviation Management",
                    "relevant_section": "§4.2",
                    "text_excerpt": "Spray Rate: Affects binder distribution.",
                }
            ]
        },
        {},
    )

    assert len(citations) == 1
    assert citations[0]["document_id"] == "SOP-DEV-001"
    assert citations[0]["document_title"] == "Deviation Management (SOP-DEV-001)"
    assert citations[0]["source_blob"] == "SOP-DEV-001-Deviation-Management.md"
    assert citations[0]["url"] == "/api/documents/blob-sop/SOP-DEV-001-Deviation-Management.md"
    assert citations[0]["resolution_status"] == "resolved"


def test_normalize_evidence_citations_builds_historical_incident_link() -> None:
    citations = _normalize_evidence_citations(
        {
            "evidence_citations": [
                {
                    "source": "INC-2026-0007.txt",
                    "document_title": "incident",
                    "text_excerpt": "Similar deviation with the same equipment.",
                }
            ]
        },
        {
            "idx-incident-history": [
                {
                    "document_id": "INC-2026-0007",
                    "document_title": "incident",
                    "source": "INC-2026-0007.txt",
                    "chunk_index": 0,
                    "text": (
                        "Incident ID: INC-2026-0007 Equipment: GR-204 Status: closed Root cause: flowmeter calibration drift. "
                        "Recommendation: inspect pump and recalibrate the flowmeter before next batch."
                    ),
                    "score": 0.75,
                }
            ]
        },
    )

    assert citations[0]["type"] == "historical"
    assert citations[0]["document_id"] == "INC-2026-0007"
    assert citations[0]["document_title"] == "Similar incident INC-2026-0007"
    assert citations[0]["section"] == "Incident summary"
    assert citations[0]["url"] == "/incidents/INC-2026-0007"
    assert citations[0]["resolution_status"] == "resolved"


def test_normalize_evidence_citations_appends_historical_fallback_from_rag_context() -> None:
    citations = _normalize_evidence_citations(
        {
            "evidence_citations": [
                {
                    "source": "SOP-DEV-001",
                    "section": "§4.2",
                    "text_excerpt": "Immediate investigation is required.",
                }
            ]
        },
        {
            "idx-sop-documents": [
                {
                    "document_id": "SOP-DEV-001",
                    "document_title": "Deviation Management (SOP-DEV-001)",
                    "source": "SOP-DEV-001-Deviation-Management.md",
                    "chunk_index": 0,
                    "text": "Immediate investigation is required for critical equipment deviations.",
                    "score": 0.99,
                }
            ],
            "idx-incident-history": [
                {
                    "document_id": "INC-2026-0006",
                    "document_title": "Spray Rate Deviation on GR-204",
                    "source": "INC-2026-0006.txt",
                    "chunk_index": 0,
                    "text": (
                        "Incident ID: INC-2026-0006 Equipment: GR-204 Status: closed "
                        "Root cause: flowmeter calibration drift. Recommendation: verify calibration and inspect tubing."
                    ),
                    "score": 0.88,
                }
            ],
        },
        current_incident_id="INC-2026-0022",
    )

    assert [citation["type"] for citation in citations] == ["sop", "historical"]
    assert citations[1]["document_id"] == "INC-2026-0006"
    assert citations[1]["document_title"] == "Spray Rate Deviation on GR-204"
    assert citations[1]["url"] == "/incidents/INC-2026-0006"
    assert citations[1]["resolution_status"] == "resolved"


def test_trace_enabled_reads_runtime_env(monkeypatch) -> None:
    monkeypatch.setenv("FOUNDRY_PROMPT_TRACE_ENABLED", "1")
    assert _trace_enabled() is True

    monkeypatch.setenv("FOUNDRY_PROMPT_TRACE_ENABLED", "false")
    assert _trace_enabled() is False