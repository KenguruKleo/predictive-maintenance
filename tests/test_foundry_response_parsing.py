from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from activities.run_foundry_agents import _parse_response


def test_parse_response_recovers_truncated_agent_json() -> None:
    raw = (
        '{"incident_id":"INC-2026-0097",'
        '"title":"Impeller Speed Rpm LOW — GR-204",'
        '"classification":"process_parameter_excursion",'
        '"risk_level":"low",'
        '"confidence":0.95,'
        '"confidence_flag":null,'
        '"root_cause":"Transient operational fluctuation.",'
        '"analysis":"The deviation was transient and aligned with prior rejected cases.",'
        '"recommendation":"No corrective action required.",'
        '"agent_recommendation":"REJECT",'
        '"agent_recommendation_rationale":"The event was transient with no product impact.",'
        '"operator_dialogue":"Recommendation remains REJECT.",'
        '"capa_suggestion":"None required.",'
        '"regulatory_reference":"EU GMP Annex 15",'
        '"batch_disposition":"release",'
        '"recommendations":[],'
        '"tool_calls_log":[{"tool":"sentinel_search_search_equipment_manuals",'
        '"args":{"query":"GR-204 impeller speed troubleshooting'
    )

    parsed = _parse_response(raw)

    assert parsed["incident_id"] == "INC-2026-0097"
    assert parsed["risk_level"] == "low"
    assert parsed["confidence"] == 0.95
    assert parsed["analysis"] == "The deviation was transient and aligned with prior rejected cases."
    assert parsed["recommendation"] == "No corrective action required."
    assert parsed["agent_recommendation"] == "REJECT"
    assert parsed["batch_disposition"] == "release"
    assert parsed["tool_calls_log"] == []
    assert parsed["evidence_citations"] == []
    assert "truncated" in parsed["execution_error"]


def test_parse_response_does_not_surface_raw_json_as_analysis_when_unrecoverable() -> None:
    parsed = _parse_response('{"incident_id":"INC-2026-0098","tool_calls_log":[{"tool":"x"')

    assert parsed["analysis"] == "Structured agent response could not be parsed. See raw_response in the audit trace."
    assert parsed["confidence_flag"] == "PARSE_ERROR"