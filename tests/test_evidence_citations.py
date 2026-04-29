from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from activities.run_foundry_agents import (
    _apply_synthesized_operator_dialogue,
    _build_evidence_synthesis_prompt,
    _build_operator_dialogue_revision_prompt,
    _build_orchestrator_research_package,
    _build_prompt,
    _collect_research_evidence_package,
    _citation_applies_to_bpr_reference,
    _citation_applies_to_equipment,
    _normalize_agent_result,
    _normalize_evidence_citations,
    _normalize_evidence_synthesis,
)
from shared.agent_telemetry import _trace_enabled


def test_collect_research_evidence_package_uses_latest_operator_question_in_queries(monkeypatch) -> None:
    from activities import run_foundry_agents as module

    calls: list[tuple[str, str, str | None]] = []

    def fake_search_index(index_name: str, query: str, top_k: int = 0, filter_expr: str | None = None):
        calls.append((index_name, query, filter_expr))
        return []

    monkeypatch.setattr(module, "SEARCH_ENABLED", True)
    monkeypatch.setattr(module, "search_index", fake_search_index)

    package, rag_context = _collect_research_evidence_package(
        {
            "alert_payload": {
                "equipment_id": "GR-204",
                "parameter": "spray_rate",
                "deviation_type": "process_parameter_excursion",
                "measured_value": 138,
                "lower_limit": 90,
                "upper_limit": 130,
            },
            "equipment": {"id": "GR-204", "name": "Granulator GR-204", "type": "granulator"},
            "batch": {"product": "Metformin 500mg", "stage": "granulation", "bpr_reference": "BPR-MET-500-v3.2"},
            "operator_questions": [
                {"round": 1, "question": "Earlier question that should not drive the latest search.", "asked_by": "operator"},
                {"round": 2, "question": "Can you check the impeller seal cleaning SOP and any newer maintenance manual note?", "asked_by": "operator"},
            ],
        },
        current_incident_id="INC-2026-9999",
    )

    assert len(calls) == 5
    assert all("impeller seal cleaning sop" in query.lower() for _, query, _ in calls)
    assert all("earlier question" not in query.lower() for _, query, _ in calls)
    assert "included in backend retrieval" in package["context_summary"].lower()
    assert rag_context["idx-sop-documents"] == []


def test_collect_research_evidence_package_carries_followup_context_and_historical_digest(monkeypatch) -> None:
    from activities import run_foundry_agents as module

    def fake_search_index(index_name: str, query: str, top_k: int = 0, filter_expr: str | None = None):
        if index_name != "idx-incident-history":
            return []
        return [
            {
                "document_id": "INC-2026-0028",
                "document_title": "Prior spray-rate deviation",
                "source": "INC-2026-0028.txt",
                "chunk_index": 0,
                "section_heading": "Incident summary",
                "text": "\n".join(
                    [
                        "Incident ID: INC-2026-0028",
                        "Equipment: GR-204 - Granulator",
                        "Status: closed | Severity: medium | Date: 2026-04-20",
                        "Deviation type: process_parameter_excursion",
                        "Root cause: transient sensor drift",
                        "Agent recommendation: REJECT",
                        "Operator agreed with agent: yes",
                        "HUMAN DECISION: REJECTED - operator dismissed this as a false positive.",
                        "Human decision reason: transient spike without product impact",
                        "Recommendation: No work order required; trend monitoring only.",
                    ]
                ),
                "equipment_ids": ["GR-204"],
                "score": 0.91,
            }
        ]

    monkeypatch.setattr(module, "SEARCH_ENABLED", True)
    monkeypatch.setattr(module, "search_index", fake_search_index)

    package, _rag_context = _collect_research_evidence_package(
        {
            "alert_payload": {
                "equipment_id": "GR-204",
                "parameter": "spray_rate",
                "deviation_type": "process_parameter_excursion",
                "measured_value": 138,
                "lower_limit": 90,
                "upper_limit": 130,
                "severity": "critical",
            },
            "equipment": {"id": "GR-204", "name": "Granulator GR-204"},
            "batch": {"product": "Metformin 500mg", "bpr_reference": "BPR-MET-500-v3.2"},
            "operator_questions": [
                {
                    "round": 2,
                    "question": "Were similar incidents closed without replacement work orders?",
                    "asked_by": "operator",
                }
            ],
        },
        current_incident_id="INC-2026-0117",
    )

    assert package["follow_up_context"]["latest_question"] == "Were similar incidents closed without replacement work orders?"
    assert "answer the latest question" in package["follow_up_context"]["answering_guidance"]
    assert "explicit supported counts" in package["follow_up_context"]["answering_guidance"]
    assert package["follow_up_context"]["retrieved_historical_incident_count"] == 1
    assert package["follow_up_context"]["historical_human_decision_counts"] == {
        "approved": 0,
        "rejected": 1,
        "unknown": 0,
    }
    assert package["historical_pattern_summary"] == "Retrieved historical split: 0 approved, 1 rejected among cited similar incidents."
    assert package["historical_incidents"][0]["incident_id"] == "INC-2026-0028"
    assert package["historical_incidents"][0]["status"] == "closed"
    assert package["historical_incidents"][0]["human_decision"] == "rejected"
    assert "human decision" in package["historical_incidents"][0]["decision_evidence"].lower()
    assert "No work order required" in package["historical_incidents"][0]["evidence_excerpt"]


def test_build_prompt_adds_latest_followup_answer_task() -> None:
    prompt = _build_prompt(
        "INC-2026-0117",
        {
            "alert_payload": {"equipment_id": "GR-204", "parameter": "spray_rate"},
            "equipment": {"id": "GR-204"},
            "batch": {"product": "Metformin 500mg"},
            "operator_questions": [
                {"round": 1, "question": "Earlier question", "asked_by": "operator"},
                {
                    "round": 2,
                    "question": "Were similar incidents closed without replacement work orders?",
                    "asked_by": "operator",
                },
            ],
        },
        more_info_round=2,
        previous_ai_result={"recommendation": "Hold batch pending review."},
        research_package={"follow_up_context": {"latest_question": "Were similar incidents closed without replacement work orders?"}},
    )

    assert "### Latest Operator Question - Answer Task" in prompt
    assert "Were similar incidents closed without replacement work orders?" in prompt
    assert "use it as the evidence answer basis" in prompt
    assert "Do not recompute count/comparison synthesis from scratch" in prompt
    assert "checked/support/unknown counts and evidence gaps" in prompt
    assert "If `evidence_synthesis` is absent" in prompt
    assert "Do not start with a generic recommendation summary" in prompt


def test_build_prompt_tells_orchestrator_to_use_evidence_synthesis_for_decision_explanation() -> None:
    prompt = _build_prompt(
        "INC-2026-0117",
        {
            "alert_payload": {"equipment_id": "GR-204", "parameter": "spray_rate"},
            "equipment": {"id": "GR-204"},
            "batch": {"product": "Metformin 500mg"},
        },
        more_info_round=0,
        research_package={
            "evidence_synthesis": {
                "direct_answer": "The excursion is explicitly supported by SCADA facts.",
                "evidence_gaps": ["No final maintenance record yet."],
            }
        },
    )

    assert "When `evidence_synthesis` is present" in prompt
    assert "navigate explicit support, unknowns" in prompt
    assert "do not let its compact wording replace" in prompt
    assert "write your own concrete operator_dialogue" in prompt
    assert "do not copy evidence_synthesis.operator_dialogue verbatim" in prompt


def test_evidence_synthesis_prompt_is_generic_and_gap_aware() -> None:
    prompt = _build_evidence_synthesis_prompt(
        incident_id="INC-2026-0117",
        latest_operator_question="How many similar deviations were closed without replacement?",
        research_package={
            "follow_up_context": {"retrieved_historical_incident_count": 3},
            "historical_incidents": [
                {
                    "incident_id": "INC-2026-0028",
                    "evidence_excerpt": "Recommendation: inspect tubing and nozzle for blockages.",
                }
            ],
            "evidence_citations": [
                {
                    "type": "historical",
                    "document_id": "INC-2026-0028",
                    "text_excerpt": "Inspect tubing and nozzle for blockages.",
                    "index_name": "idx-incident-history",
                }
            ],
        },
    )

    assert "Evidence Synthesis Request" in prompt
    assert "Distinguish explicit support from unknown" in prompt
    assert "current incident facts" in prompt
    assert "Do not reduce an initial-decision brief to historical precedent alone" in prompt
    assert "concrete and operational" in prompt
    assert "cautious approach" in prompt
    assert "Do not infer that an action did not happen" in prompt
    assert "include those counts in `operator_dialogue`" in prompt
    assert "omission means unknown" in prompt
    assert "explicit support requires source wording" in prompt
    assert "list of other actions is unknown" in prompt
    assert "source_quote" in prompt
    assert "Do not add a negative or absence claim" in prompt
    assert "not JSON Schema" in prompt
    assert "count is not determinable from retrieved evidence" in prompt
    assert "tool_calls_log" not in prompt


def test_normalize_evidence_synthesis_unwraps_schema_shaped_response() -> None:
    synthesis = _normalize_evidence_synthesis(
        {
            "type": "object",
            "properties": {
                "latest_question": "How many cases explicitly support the requested outcome?",
                "question_focus": "Historical comparison",
                "answerability": "partially_answered",
                "direct_answer": "One of two cases explicitly supports the requested outcome.",
                "operator_dialogue": "One of two reviewed cases explicitly supports the requested outcome; the other is unknown.",
                "checked_evidence_count": "2",
                "explicit_support_count": "1",
                "contradiction_count": 0,
                "unknown_count": "1",
                "supporting_evidence": [{"source_id": "INC-1", "source_type": "historical", "fact": "Explicitly supported."}],
                "evidence_gaps": ["Second excerpt does not state the requested outcome."],
                "decision_impact_hint": "Do not change decision from this evidence alone.",
                "reasoning_summary": "One supported, one unknown.",
            },
        },
        "Fallback question",
    )

    assert synthesis["latest_question"] == "How many cases explicitly support the requested outcome?"
    assert synthesis["answerability"] == "partially_answered"
    assert synthesis["checked_evidence_count"] == 2
    assert synthesis["explicit_support_count"] == 1
    assert synthesis["unknown_count"] == 1
    assert synthesis["operator_dialogue"].startswith("One of two reviewed cases")


def test_orchestrator_research_package_frontloads_synthesis_without_dropping_evidence() -> None:
    package = _build_orchestrator_research_package(
        {
            "tool_calls_log": [{"tool": "search", "args": {}, "status": "success"}],
            "evidence_synthesis": {
                "direct_answer": "The count is not determinable.",
                "operator_dialogue": "The count is not determinable from retrieved evidence.",
            },
            "incident_facts": {"incident_id": "INC-2026-0117"},
            "historical_incidents": [
                {
                    "incident_id": "INC-2026-0028",
                    "evidence_excerpt": "Recommendation: inspect tubing and nozzle for blockages.",
                    "extra": "drop me",
                }
            ],
            "evidence_citations": [
                {
                    "type": "historical",
                    "document_id": "INC-2026-0028",
                    "document_title": "Prior deviation",
                    "text_excerpt": "Inspect tubing and nozzle for blockages.",
                    "source_blob": "INC-2026-0028.txt",
                    "index_name": "idx-incident-history",
                    "large_field": "drop me",
                }
            ],
        }
    )

    assert next(iter(package)) == "evidence_synthesis"
    assert package["tool_calls_log"] == [{"tool": "search", "args": {}, "status": "success"}]
    assert package["historical_incidents"][0]["extra"] == "drop me"
    assert package["evidence_citations"][0]["large_field"] == "drop me"


def test_apply_synthesized_operator_dialogue_uses_model_owned_followup_answer(monkeypatch) -> None:
    from activities import run_foundry_agents as module

    traces: list[dict] = []
    monkeypatch.setattr(module, "_log_trace_json", lambda **kwargs: traces.append(kwargs))

    result, applied = _apply_synthesized_operator_dialogue(
        {
            "operator_dialogue": "Old orchestrator answer.",
            "recommendation": "Inspect and recalibrate GR-204.",
        },
        {
            "evidence_synthesis": {
                "operator_dialogue": "Among 3 reviewed incidents, the count is not determinable from retrieved evidence.",
                "answerability": "not_determinable",
                "checked_evidence_count": 3,
                "explicit_support_count": 0,
                "unknown_count": 3,
            }
        },
        incident_id="INC-2026-0117",
        more_info_round=1,
    )

    assert applied is True
    assert result["operator_dialogue"].startswith("Among 3 reviewed incidents")
    assert result["recommendation"] == "Inspect and recalibrate GR-204."
    assert traces[0]["trace_kind"] == "operator_dialogue_synthesis_result"


def test_build_operator_dialogue_revision_prompt_keeps_model_answer_source_grounded() -> None:
    prompt = _build_operator_dialogue_revision_prompt(
        incident_id="INC-2026-0117",
        latest_operator_question="How many similar deviations were closed without tubing replacement?",
        result={
            "incident_id": "INC-2026-0117",
            "operator_dialogue": "Historical evidence indicates all similar deviations closed without replacement.",
            "recommendation": "Inspect and recalibrate GR-204.",
            "risk_level": "critical",
            "root_cause": "Potential calibration drift.",
            "batch_disposition": "hold_pending_review",
        },
        previous_ai_result={"recommendation": "Inspect and recalibrate GR-204."},
        research_package={
            "follow_up_context": {"retrieved_historical_incident_count": 3},
            "historical_incidents": [
                {
                    "incident_id": "INC-2026-0028",
                    "evidence_excerpt": "Recommendation: inspect tubing and nozzle for blockages.",
                }
            ],
        },
    )

    assert "revising only the `operator_dialogue` field" in prompt
    assert "Return JSON only in this exact shape" in prompt
    assert "Original Decision Summary" in prompt
    assert "Revision Evidence" in prompt
    assert "do not infer facts from silence" in prompt
    assert "Count an outcome or attribute only when a cited excerpt explicitly supports" in prompt
    assert "do not treat absence of that action or attribute as proof" in prompt
    assert "count is not determinable from retrieved evidence" in prompt
    assert "N of M" in prompt
    assert "tool_calls_log" not in prompt


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


def test_normalize_evidence_citations_does_not_infer_id_only_sop_refs_without_rag_match() -> None:
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
    assert citations[0]["document_title"] == "Deviation Management"
    assert citations[0]["source_blob"] == ""
    assert citations[0]["url"] == ""
    assert citations[0]["resolution_status"] == "unresolved"


def test_normalize_evidence_citations_uses_canonical_agent_metadata_without_rag_match() -> None:
    citations = _normalize_evidence_citations(
        {
            "evidence_citations": [
                {
                    "type": "sop",
                    "document_id": "SOP-MAN-GR-001-Granulator-Operation",
                    "document_title": "Granulator Operation SOP",
                    "section_heading": "4.2 Impeller Speed Monitoring",
                    "text_excerpt": "Impeller speed below PAR must be documented and reviewed.",
                    "source_blob": "SOP-MAN-GR-001-Granulator-Operation.md",
                    "index_name": "idx-sop-documents",
                    "chunk_index": 4,
                    "score": 0.91,
                }
            ]
        },
        {},
    )

    assert len(citations) == 1
    assert citations[0]["document_id"] == "SOP-MAN-GR-001-Granulator-Operation"
    assert citations[0]["source_blob"] == "SOP-MAN-GR-001-Granulator-Operation.md"
    assert citations[0]["url"] == "/api/documents/blob-sop/SOP-MAN-GR-001-Granulator-Operation.md"
    assert citations[0]["section"] == "4.2 Impeller Speed Monitoring"
    assert citations[0]["resolution_status"] == "resolved"


def test_normalize_agent_result_uses_authoritative_research_package_citations() -> None:
    result = {
        "incident_id": "INC-2026-0084",
        "title": "Impeller Speed Low",
        "risk_level": "medium",
        "confidence": 0.85,
        "recommendation": "Reject transient event.",
        "operator_dialogue": "Reject transient event.",
        "agent_recommendation": "REJECT",
        "evidence_citations": [
            {
                "type": "bpr",
                "document_id": "BPR-MET-500-v3_2-Process-Specification",
                "document_title": "BPR Metformin 500mg Process Specification",
                "section_heading": "5.4 Process Parameter Deviation Matrix",
                "text_excerpt": "Short transient excursions may be assessed against historical process impact.",
                "source_blob": "BPR-MET-500-v3.2-Process-Specification.md",
                "index_name": "idx-bpr-documents",
                "chunk_index": 8,
                "score": 0.92,
            }
        ],
        "tool_calls_log": [],
    }
    research_package = {
        "tool_calls_log": [
            {"tool": "sentinel_search_search_bpr_documents", "args": {"query": "bpr"}, "status": "success"},
            {"tool": "sentinel_search_search_incident_history", "args": {"query": "history"}, "status": "success"},
        ],
        "evidence_citations": [
            result["evidence_citations"][0],
            {
                "type": "bpr",
                "document_id": "BPR-MET-500-v3_2-Process-Specification",
                "document_title": "BPR Metformin 500mg Process Specification",
                "section_heading": "Document header",
                "text_excerpt": "Master batch process specification for Metformin HCl 500mg tablets.",
                "source_blob": "BPR-MET-500-v3.2-Process-Specification.md",
                "index_name": "idx-bpr-documents",
                "chunk_index": 0,
                "score": 0.88,
            },
            {
                "type": "historical",
                "document_id": "INC-2026-0015",
                "document_title": "Historical incident INC-2026-0015",
                "section_heading": "Human decision",
                "text_excerpt": "Human decision: rejected. Similar transient impeller speed deviation on GR-204.",
                "source_blob": "INC-2026-0015.txt",
                "index_name": "idx-incident-history",
                "chunk_index": 0,
                "score": 0.87,
            },
        ],
    }

    normalized = _normalize_agent_result(
        result,
        {},
        more_info_round=0,
        authoritative_research_package=research_package,
    )

    assert [citation["document_id"] for citation in normalized["evidence_citations"]] == [
        "BPR-MET-500-v3_2-Process-Specification",
        "BPR-MET-500-v3_2-Process-Specification",
        "INC-2026-0015",
    ]
    assert [citation["chunk_index"] for citation in normalized["evidence_citations"]] == [8, 0, 0]
    assert normalized["evidence_citations"][2]["url"] == "/incidents/INC-2026-0015"
    assert [entry["tool"] for entry in normalized["tool_calls_log"]] == [
        "sentinel_search_search_bpr_documents",
        "sentinel_search_search_incident_history",
    ]
    assert normalized["agent_recommendation_rationale"].startswith("REJECT because")


def test_citation_applies_to_equipment_filters_other_equipment_specific_sop() -> None:
    citation = {"index_name": "idx-sop-documents"}

    assert not _citation_applies_to_equipment(
        citation,
        {"equipment_ids": ["GR-204"]},
        "MIX-102",
    )
    assert _citation_applies_to_equipment(
        citation,
        {"equipment_ids": ["GR-204"]},
        "GR-204",
    )
    assert _citation_applies_to_equipment(citation, {"equipment_ids": []}, "MIX-102")


def test_citation_applies_to_equipment_filters_specific_sop_without_equipment_ids() -> None:
    assert not _citation_applies_to_equipment(
        {
            "index_name": "idx-sop-documents",
            "document_id": "SOP-MAN-GR-001-Granulator-Operation",
            "document_title": "SOP-MAN-GR-001 · High-Shear Granulator — Operation Procedure",
            "source_blob": "SOP-MAN-GR-001-Granulator-Operation.md",
        },
        {},
        "MIX-102",
    )
    assert _citation_applies_to_equipment(
        {
            "index_name": "idx-sop-documents",
            "document_id": "SOP-MAN-GR-001-Granulator-Operation",
            "document_title": "SOP-MAN-GR-001 · High-Shear Granulator — Operation Procedure",
            "source_blob": "SOP-MAN-GR-001-Granulator-Operation.md",
        },
        {},
        "GR-204",
    )
    assert _citation_applies_to_equipment(
        {
            "index_name": "idx-sop-documents",
            "document_id": "SOP-DEV-001-Deviation-Management",
            "document_title": "SOP-DEV-001 — GMP Deviation Management Procedure",
            "source_blob": "SOP-DEV-001-Deviation-Management.md",
        },
        {},
        "MIX-102",
    )


def test_citation_applies_to_bpr_reference_filters_other_product_specs() -> None:
    assert not _citation_applies_to_bpr_reference(
        {
            "index_name": "idx-bpr-documents",
            "document_id": "BPR-PCT-500-v2_0-Process-Specification",
            "document_title": "Paracetamol 500mg Tablets",
            "source_blob": "BPR-PCT-500-v2.0-Process-Specification.md",
        },
        {},
        "BPR-AML-005-v2.0",
    )
    assert _citation_applies_to_bpr_reference(
        {
            "index_name": "idx-bpr-documents",
            "document_id": "BPR-AML-005-v2_0-Process-Specification",
            "document_title": "Amlodipine 5mg Tablets",
            "source_blob": "BPR-AML-005-v2.0-Process-Specification.md",
        },
        {},
        "BPR-AML-005-v2.0",
    )
    assert _citation_applies_to_bpr_reference(
        {"index_name": "idx-sop-documents", "document_id": "SOP-DEV-001"},
        {},
        "BPR-AML-005-v2.0",
    )


def test_approve_keeps_critical_source_alert_risk_critical() -> None:
    normalized = _normalize_agent_result(
        {
            "incident_id": "INC-2026-0101",
            "title": "Dryer Temperature Low",
            "classification": "process_parameter_excursion",
            "risk_level": "medium",
            "confidence": 0.85,
            "root_cause": "Sustained critical process parameter excursion.",
            "analysis": "The alert severity is critical and corrective action is required.",
            "recommendation": "Investigate and correct the temperature control deviation.",
            "agent_recommendation": "APPROVE",
            "batch_disposition": "hold_pending_review",
            "operator_dialogue": "Approve corrective action.",
            "audit_entry_draft": {"description": "Critical excursion."},
            "work_order_draft": {"title": "Investigate dryer temperature control"},
            "evidence_citations": [],
            "tool_calls_log": [],
        },
        {},
        more_info_round=0,
        authoritative_research_package={
            "incident_facts": {"severity": "critical"},
            "evidence_citations": [],
            "tool_calls_log": [],
        },
    )

    assert normalized["agent_recommendation"] == "APPROVE"
    assert normalized["risk_level"] == "critical"


def test_approve_recommendation_contract_sets_testing_disposition() -> None:
    normalized = _normalize_agent_result(
        {
            "incident_id": "INC-2026-0090",
            "title": "Spray Rate High",
            "risk_level": "critical",
            "confidence": 0.95,
            "analysis": "Sustained spray-rate excursion with product quality risk.",
            "recommendation": "Inspect nozzle and conduct granule distribution testing.",
            "operator_dialogue": "Corrective action and testing are required.",
            "root_cause": "Potential nozzle or flowmeter issue.",
            "agent_recommendation": "APPROVE",
            "batch_disposition": "hold_pending_review",
            "recommendations": [
                {
                    "action": "Conduct granule distribution testing",
                    "priority": "high",
                    "owner": "Quality Control",
                    "deadline_days": 5,
                }
            ],
            "work_order_draft": {
                "title": "Inspect spray system",
                "description": "Inspect nozzle and verify flowmeter calibration.",
                "priority": "high",
                "estimated_hours": 8,
            },
            "audit_entry_draft": {
                "deviation_type": "process_parameter_excursion",
                "description": "Sustained spray-rate excursion.",
                "root_cause": "Potential nozzle or flowmeter issue.",
                "capa_actions": "Inspect nozzle and conduct granule distribution testing.",
            },
            "evidence_citations": [],
            "tool_calls_log": [],
        },
        {},
        more_info_round=0,
    )

    assert normalized["agent_recommendation"] == "APPROVE"
    assert normalized["batch_disposition"] == "conditional_release_pending_testing"
    assert normalized["work_order_draft"] is not None


def test_reject_recommendation_contract_clears_corrective_actions() -> None:
    normalized = _normalize_agent_result(
        {
            "incident_id": "INC-2026-0086",
            "title": "Impeller Speed Low",
            "risk_level": "medium",
            "confidence": 0.85,
            "analysis": "Short transient excursion with no confirmed product quality impact.",
            "recommendation": "Investigate calibration and review operational logs.",
            "operator_dialogue": "Investigate calibration and review operational logs.",
            "root_cause": "Transient operational anomaly.",
            "agent_recommendation": "REJECT",
            "recommendations": [
                {
                    "action": "Perform equipment calibration check",
                    "priority": "medium",
                    "owner": "Maintenance",
                    "deadline_days": 7,
                }
            ],
            "work_order_draft": None,
            "audit_entry_draft": {
                "deviation_type": "process_parameter_excursion",
                "description": "Short transient excursion.",
                "root_cause": "Transient operational anomaly.",
                "capa_actions": "Conduct equipment calibration check.",
            },
            "evidence_citations": [],
            "tool_calls_log": [],
        },
        {},
        more_info_round=0,
    )

    assert normalized["recommendations"] == []
    assert normalized["work_order_draft"] is None
    assert normalized["work_order_id"] is None
    assert normalized["agent_recommendation_rationale"].startswith("REJECT because")
    assert normalized["recommendation"] == normalized["agent_recommendation_rationale"]
    assert normalized["audit_entry_draft"]["capa_actions"].startswith("No CAPA/work order required")


def test_low_confidence_normalization_relabels_risk_without_dropping_recommendation() -> None:
    normalized = _normalize_agent_result(
        {
            "incident_id": "INC-2026-0115",
            "title": "Spray Rate High",
            "risk_level": "critical",
            "confidence": 0.5,
            "analysis": "The spray rate exceeded the validated range, but evidence is incomplete.",
            "recommendation": "Hold the batch pending operator review.",
            "operator_dialogue": "Recommendation remains approve with manual review.",
            "root_cause": "Evidence gap prevents a grounded final decision.",
            "batch_disposition": "hold_pending_review",
            "evidence_citations": [],
            "tool_calls_log": [],
        },
        {},
        more_info_round=0,
    )

    assert normalized["agent_recommendation"] == "APPROVE"
    assert normalized["risk_level"] == "LOW_CONFIDENCE"
    assert normalized["confidence_flag"] == "LOW_CONFIDENCE"


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


def test_normalize_evidence_citations_does_not_append_historical_fallback_from_rag_context() -> None:
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

    assert [citation["type"] for citation in citations] == ["sop"]


def test_normalize_evidence_citations_prefers_authoritative_section_from_excerpt_anchor() -> None:
    citations = _normalize_evidence_citations(
        {
            "evidence_citations": [
                {
                    "source": "EU GMP Annex 15",
                    "section": "§6.3",
                    "text_excerpt": "Application to GR-204: Impeller speed validated PAR: 200–800 RPM.",
                }
            ]
        },
        {
            "idx-gmp-policies": [
                {
                    "document_id": "GMP-Annex15-Excerpt",
                    "document_title": "EU GMP Annex 15",
                    "source": "GMP-Annex15-Excerpt.md",
                    "chunk_index": 1,
                    "section_heading": "§6.1 General Principles",
                    "section_key": "6.1",
                    "section_path": "§6 — Process Validation > §6.1 General Principles",
                    "text": (
                        "Application to GR-204: Impeller speed validated PAR: 200–800 RPM. "
                        "Product-specific NOR may be set at 600–700 RPM in the BPR."
                    ),
                    "score": 0.92,
                },
                {
                    "document_id": "GMP-Annex15-Excerpt",
                    "document_title": "EU GMP Annex 15",
                    "source": "GMP-Annex15-Excerpt.md",
                    "chunk_index": 2,
                    "section_heading": "§6.3 Process Parameter Deviations During Validation and Routine Manufacturing",
                    "section_key": "6.3",
                    "section_path": "§6 — Process Validation > §6.3 Process Parameter Deviations During Validation and Routine Manufacturing",
                    "text": "6.3.1 The deviation shall be detected promptly and documented with exact timestamps.",
                    "score": 0.91,
                },
            ]
        },
    )

    assert citations[0]["section"] == "§6.1 General Principles"
    assert citations[0]["section_key"] == "6.1"
    assert citations[0]["resolution_status"] == "resolved"


def test_normalize_evidence_citations_marks_unverified_section_without_dropping_document() -> None:
    citations = _normalize_evidence_citations(
        {
            "evidence_citations": [
                {
                    "source": "EU GMP Annex 15",
                    "section": "§6.3",
                    "text_excerpt": "generic process validation note",
                }
            ]
        },
        {
            "idx-gmp-policies": [
                {
                    "document_id": "GMP-Annex15-Excerpt",
                    "document_title": "EU GMP Annex 15",
                    "source": "GMP-Annex15-Excerpt.md",
                    "chunk_index": 1,
                    "section_heading": "§6.1 General Principles",
                    "section_key": "6.1",
                    "section_path": "§6 — Process Validation > §6.1 General Principles",
                    "text": "Application to GR-204: Impeller speed validated PAR: 200–800 RPM.",
                    "score": 0.92,
                }
            ]
        },
    )

    assert citations[0]["document_title"] == "EU GMP Annex 15"
    assert citations[0]["section"] == "§6.3"
    assert citations[0]["resolution_status"] == "unresolved"
    assert "authoritative section match" in citations[0]["unresolved_reason"]


def test_normalize_evidence_citations_dedupes_same_document_section_even_if_status_would_differ() -> None:
    citations = _normalize_evidence_citations(
        {
            "evidence_citations": [
                {
                    "source": "EU GMP Annex 15",
                    "section": "§6.3",
                    "text_excerpt": "generic process validation note",
                }
            ],
            "regulatory_refs": [
                {
                    "regulation": "EU GMP Annex 15",
                    "section": "§6.3",
                    "text_excerpt": "6.3.1 The deviation shall be detected promptly and documented with exact timestamps.",
                }
            ],
        },
        {
            "idx-gmp-policies": [
                {
                    "document_id": "GMP-Annex15-Excerpt",
                    "document_title": "EU GMP Annex 15",
                    "source": "GMP-Annex15-Excerpt.md",
                    "chunk_index": 2,
                    "section_heading": "§6.3 Process Parameter Deviations During Validation and Routine Manufacturing",
                    "section_key": "6.3",
                    "section_path": "§6 — Process Validation > §6.3 Process Parameter Deviations During Validation and Routine Manufacturing",
                    "text": "6.3.1 The deviation shall be detected promptly and documented with exact timestamps.",
                    "score": 0.91,
                }
            ]
        },
    )

    assert len(citations) == 1
    assert citations[0]["document_title"] == "EU GMP Annex 15"
    assert citations[0]["section_key"] == "6.3"


def test_normalize_agent_result_omits_unverified_section_from_regulatory_reference() -> None:
    result = {
        "incident_id": "INC-2026-0024",
        "title": "Spray Rate Deviation",
        "recommendation": "Hold the batch pending review.",
        "operator_dialogue": "Hold the batch pending review.",
        "regulatory_reference": "SOP-DEV-001 §4.2; GMP Annex 15 §6.3",
        "evidence_citations": [
            {
                "source": "SOP-DEV-001",
                "section": "§4.2",
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
        "sop_refs": [
            {
                "id": "SOP-DEV-001",
                "title": "Deviation Management",
                "relevant_section": "§4.2",
                "text_excerpt": "Spray Rate: Affects binder distribution.",
            }
        ],
    }
    rag_context = {
        "idx-sop-documents": [
            {
                "document_id": "SOP-DEV-001-Deviation-Management",
                "document_title": "SOP-DEV-001 — GMP Deviation Management Procedure",
                "source": "SOP-DEV-001-Deviation-Management.md",
                "chunk_index": 6,
                "section_heading": "4.2 Process Parameter Excursions — Granulation",
                "section_key": "4.2",
                "section_path": "SOP-DEV-001 — GMP Deviation Management Procedure > 4. Deviation Classification > 4.2 Process Parameter Excursions — Granulation",
                "text": "For High-Shear Granulators (GR series): Spray Rate: Affects binder distribution. Low spray rate increases risk of ungranulated fines.",
                "score": 1.0,
            }
        ],
        "idx-gmp-policies": [
            {
                "document_id": "GMP-Annex15-Excerpt",
                "document_title": "EU GMP Annex 15",
                "source": "GMP-Annex15-Excerpt.md",
                "chunk_index": 2,
                "section_heading": "§6.1 General Principles",
                "section_key": "6.1",
                "section_path": "EU GMP Annex 15 — Process Validation and Deviation Management (Relevant Excerpts) > §6 — Process Validation > §6.1 General Principles",
                "text": "The impact on product quality shall be assessed based on duration of excursion, magnitude of excursion relative to validated limits, and product sensitivity.",
                "score": 0.9,
            }
        ],
    }

    normalized = _normalize_agent_result(result, rag_context, more_info_round=0)

    assert normalized["regulatory_reference"] == "SOP-DEV-001 §4.2; EU GMP Annex 15"
    assert normalized["sop_refs"][0]["relevant_section"] == "§4.2"
    assert normalized["regulatory_refs"][0]["section"] == ""
    assert normalized["regulatory_refs"][0]["section_heading"] == "§6.1 General Principles"
    assert normalized["regulatory_refs"][0]["resolution_status"] == "unresolved"


def test_normalize_agent_result_skips_generic_ghost_labels_in_regulatory_reference() -> None:
    result = {
        "incident_id": "INC-2026-0025",
        "title": "Spray Rate Deviation",
        "recommendation": "Hold the batch pending review.",
        "operator_dialogue": "Hold the batch pending review.",
        "regulatory_reference": "sop §4.2; gmp §15; EU GMP",
        "evidence_citations": [
            {
                "type": "sop",
                "source": "sop",
                "section": "§4.2",
                "text_excerpt": "Spray Rate: Affects binder distribution.",
            },
            {
                "type": "gmp",
                "source": "gmp",
                "section": "Annex 15 §6.3",
                "text_excerpt": "Critical deviations must be investigated and documented to ensure product quality.",
            },
            {
                "type": "gmp",
                "source": "GMP-Annex15-Excerpt",
                "reference": "EU GMP",
                "section": "Annex 15 §6.3",
                "text_excerpt": "The impact on product quality shall be assessed based on duration, magnitude, and product sensitivity.",
            },
        ],
    }
    rag_context = {
        "idx-sop-documents": [
            {
                "document_id": "SOP-DEV-001-Deviation-Management",
                "document_title": "SOP-DEV-001 — GMP Deviation Management Procedure",
                "source": "SOP-DEV-001-Deviation-Management.md",
                "chunk_index": 6,
                "section_heading": "4.2 Process Parameter Excursions — Granulation",
                "section_key": "4.2",
                "section_path": "SOP-DEV-001 — GMP Deviation Management Procedure > 4. Deviation Classification > 4.2 Process Parameter Excursions — Granulation",
                "text": "### 4.2 Process Parameter Excursions — Granulation Spray Rate: Affects binder distribution. Low spray rate increases risk of ungranulated fines.",
                "score": 1.0,
            }
        ],
        "idx-gmp-policies": [
            {
                "document_id": "GMP-Annex15-Excerpt",
                "document_title": "EU GMP Annex 15",
                "source": "GMP-Annex15-Excerpt.md",
                "chunk_index": 2,
                "section_heading": "§6.1 General Principles",
                "section_key": "6.1",
                "section_path": "EU GMP Annex 15 — Process Validation and Deviation Management (Relevant Excerpts) > §6 — Process Validation > §6.1 General Principles",
                "text": "### §6.1 General Principles Process validation shall establish scientific evidence that a manufacturing process can reproducibly produce medicinal product meeting predetermined specifications.",
                "score": 0.9,
            }
        ],
    }

    normalized = _normalize_agent_result(result, rag_context, more_info_round=0)

    assert normalized["regulatory_reference"] == "SOP-DEV-001 §4.2; EU GMP Annex 15"
    assert normalized["regulatory_refs"][0]["section"] == "§6.3"
    assert normalized["regulatory_refs"][1]["section"] == ""
    assert all("§15" not in str(item.get("section") or "") for item in normalized["regulatory_refs"])


def test_normalize_agent_result_does_not_reingest_existing_regulatory_refs_when_gmp_citations_exist() -> None:
    result = {
        "incident_id": "INC-2026-0025",
        "title": "Spray Rate Deviation",
        "recommendation": "Hold the batch pending review.",
        "operator_dialogue": "Hold the batch pending review.",
        "regulatory_reference": "sop §4.2; gmp §15; EU GMP",
        "evidence_citations": [
            {
                "type": "sop",
                "source": "sop",
                "section": "§4.2",
                "text_excerpt": "Spray Rate: Affects binder distribution.",
            },
            {
                "type": "gmp",
                "source": "gmp",
                "section": "Annex 15 §6.3",
                "text_excerpt": "Critical deviations must be investigated and documented to ensure product quality.",
            },
            {
                "type": "gmp",
                "source": "GMP-Annex15-Excerpt",
                "reference": "EU GMP",
                "document_id": "GMP-Annex15-Excerpt",
                "document_title": "EU GMP Annex 15",
                "section": "Annex 15 §6.3",
                "section_heading": "§6.1 General Principles",
                "section_key": "6.1",
                "section_path": "EU GMP Annex 15 — Process Validation and Deviation Management (Relevant Excerpts) > §6 — Process Validation > §6.1 General Principles",
                "text_excerpt": "### §6.1 General Principles Process validation shall establish scientific evidence that a manufacturing process can reproducibly produce medicinal product meeting predetermined specifications.",
                "url": "/api/documents/blob-gmp/GMP-Annex15-Excerpt.md",
            },
        ],
        "regulatory_refs": [
            {
                "type": "gmp",
                "source": "gmp",
                "reference": "",
                "document_id": "",
                "document_title": "gmp",
                "section": "§15",
                "section_heading": "Annex 15 §6.3",
                "section_key": "15",
                "section_path": "Annex 15 §6.3",
                "text_excerpt": "Critical deviations must be investigated and documented to ensure product quality.",
                "url": "",
                "resolution_status": "unresolved",
                "unresolved_reason": "Missing link for gmp citation",
                "regulation": "gmp",
            },
            {
                "type": "gmp",
                "source": "GMP-Annex15-Excerpt",
                "reference": "EU GMP",
                "document_id": "GMP-Annex15-Excerpt",
                "document_title": "EU GMP Annex 15",
                "section": "",
                "section_heading": "§6.1 General Principles",
                "section_key": "6.1",
                "section_path": "EU GMP Annex 15 — Process Validation and Deviation Management (Relevant Excerpts) > §6 — Process Validation > §6.1 General Principles",
                "text_excerpt": "### §6.1 General Principles Process validation shall establish scientific evidence that a manufacturing process can reproducibly produce medicinal product meeting predetermined specifications.",
                "url": "/api/documents/blob-gmp/GMP-Annex15-Excerpt.md",
                "resolution_status": "unresolved",
                "unresolved_reason": "Missing authoritative section match for gmp citation",
                "regulation": "EU GMP",
            },
        ],
    }
    rag_context = {
        "idx-sop-documents": [
            {
                "document_id": "SOP-DEV-001-Deviation-Management",
                "document_title": "SOP-DEV-001 — GMP Deviation Management Procedure",
                "source": "SOP-DEV-001-Deviation-Management.md",
                "chunk_index": 6,
                "section_heading": "4.2 Process Parameter Excursions — Granulation",
                "section_key": "4.2",
                "section_path": "SOP-DEV-001 — GMP Deviation Management Procedure > 4. Deviation Classification > 4.2 Process Parameter Excursions — Granulation",
                "text": "### 4.2 Process Parameter Excursions — Granulation Spray Rate: Affects binder distribution. Low spray rate increases risk of ungranulated fines.",
                "score": 1.0,
            }
        ],
        "idx-gmp-policies": [
            {
                "document_id": "GMP-Annex15-Excerpt",
                "document_title": "EU GMP Annex 15",
                "source": "GMP-Annex15-Excerpt.md",
                "chunk_index": 2,
                "section_heading": "§6.1 General Principles",
                "section_key": "6.1",
                "section_path": "EU GMP Annex 15 — Process Validation and Deviation Management (Relevant Excerpts) > §6 — Process Validation > §6.1 General Principles",
                "text": "### §6.1 General Principles Process validation shall establish scientific evidence that a manufacturing process can reproducibly produce medicinal product meeting predetermined specifications.",
                "score": 0.9,
            },
            {
                "document_id": "GMP-Annex15-Excerpt",
                "document_title": "EU GMP Annex 15",
                "source": "GMP-Annex15-Excerpt.md",
                "chunk_index": 0,
                "section_heading": "Annex 15",
                "section_key": "15",
                "section_path": "Annex 15",
                "text": "# EU GMP Annex 15 — Process Validation and Deviation Management (Relevant Excerpts)",
                "score": 0.5,
            }
        ],
    }

    normalized = _normalize_agent_result(result, rag_context, more_info_round=0)

    assert normalized["regulatory_reference"] == "SOP-DEV-001 §4.2; EU GMP Annex 15 §6.1"
    assert len(normalized["regulatory_refs"]) == 2
    assert all(item.get("regulation") != "GMP-Annex15-Excerpt" for item in normalized["regulatory_refs"])
    assert all("§15" not in str(item.get("section") or "") for item in normalized["regulatory_refs"])


def test_trace_enabled_reads_runtime_env(monkeypatch) -> None:
    monkeypatch.setenv("FOUNDRY_PROMPT_TRACE_ENABLED", "1")
    assert _trace_enabled() is True

    monkeypatch.setenv("FOUNDRY_PROMPT_TRACE_ENABLED", "false")
    assert _trace_enabled() is False