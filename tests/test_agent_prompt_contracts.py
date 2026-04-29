from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "agents" / "prompts"


def test_research_prompt_uses_foundry_openapi_function_names() -> None:
    prompt = (PROMPTS / "research_system.md").read_text(encoding="utf-8")

    required_names = [
        "sentinel_db_get_equipment",
        "sentinel_db_get_batch",
        "sentinel_db_get_incident",
        "sentinel_db_search_incidents",
        "sentinel_search_search_bpr_documents",
        "sentinel_search_search_sop_documents",
        "sentinel_search_search_gmp_policies",
        "sentinel_search_search_equipment_manuals",
        "sentinel_search_search_incident_history",
    ]
    for name in required_names:
        assert f"`{name}" in prompt

    invalid_aliases = [
        "`get_equipment(",
        "`get_batch(",
        "`get_incident(",
        "`search_incidents(",
        "`search_bpr_documents(",
        "`search_sop_documents(",
        "`search_gmp_policies(",
        "`search_equipment_manuals(",
        "`search_incident_history(",
    ]
    for alias in invalid_aliases:
        assert alias not in prompt


def test_orchestrator_prompt_forbids_simulated_research_logs() -> None:
    prompt = (PROMPTS / "orchestrator_system.md").read_text(encoding="utf-8")

    assert "Do not call connected agents or external tools" in prompt
    assert "Do not write or simulate `tool_calls_log`" in prompt
    assert "Do not invent citations" in prompt
    assert "agent_recommendation_rationale" in prompt
    assert "backend provides a Research Evidence Package" in prompt
    assert "Backend normalization restores the canonical package" in prompt
    assert "severity: critical" in prompt
    assert "Operator dialogue rules" in prompt
    assert "Evidence Synthesizer owns compact evidence briefs" in prompt
    assert "answerability, count/comparison" in prompt
    assert "write `operator_dialogue` yourself" in prompt
    assert "Do not copy" in prompt
    assert "cautious approach" in prompt
    assert "use that synthesized answer as the basis" in prompt
    assert "Do not recompute count/comparison synthesis from scratch" in prompt
    assert "state missing evidence plainly" in prompt
    assert "evidence_synthesis" in prompt
    assert "explicit evidence" in prompt
    assert "supports the decision" in prompt
    assert "not as a" in prompt
    assert "replacement for the canonical Research Evidence Package" in prompt
    assert "full incident, document" in prompt
    assert "Do not turn Synthesizer unknowns into decision facts" in prompt
    assert "analysis, rationale, recommendation, CAPA" in prompt
    assert "Identify the question shape" not in prompt


def test_evidence_synthesizer_prompt_contract() -> None:
    prompt = (PROMPTS / "evidence_synthesizer_system.md").read_text(encoding="utf-8")

    assert "Evidence Synthesizer Agent" in prompt
    assert "Do not make the final GMP approval/rejection decision" in prompt
    assert "Do not infer a fact from silence" in prompt
    assert "explicitly supports the requested attribute" in prompt
    assert "Negative support also requires explicit evidence" in prompt
    assert "explicit support requires source wording" in prompt
    assert "list of other actions is not evidence" in prompt
    assert "count or quantified comparison questions" in prompt
    assert "operator_dialogue` must include the checked count" in prompt
    assert "Do not mention checked/support/unknown counts" in prompt
    assert "change-control questions" in prompt
    assert "changed, unchanged, or not determinable" in prompt
    assert "Do not treat unchanged fields as evidence items" in prompt
    assert "answer every requested part explicitly" in prompt
    assert "source_quote" in prompt
    assert "must not add a negative or absence claim" in prompt
    assert "balanced evidence map for the initial decision" in prompt
    assert "Do not reduce the brief to historical precedent alone" in prompt
    assert "historical approvals alone" in prompt
    assert "concrete and operational" in prompt
    assert "cautious approach" in prompt
    assert "Do not return JSON Schema wrapper keys" in prompt
    assert "count is not determinable from retrieved evidence" in prompt
    assert "Return JSON only" in prompt


def test_orchestrator_agent_has_no_connected_tools() -> None:
    source = (ROOT / "agents" / "create_agents.py").read_text(encoding="utf-8")

    orchestrator_section = source.split("# ── 4. Orchestrator Agent", 1)[1]
    orchestrator_section = orchestrator_section.split("print(\"\\n\" + \"=\" * 60)", 1)[0]
    assert "ConnectedAgentTool" not in orchestrator_section
    assert "research_connected" not in orchestrator_section
    assert "document_connected" not in orchestrator_section


def test_evidence_synthesizer_agent_schema_is_registered() -> None:
    source = (ROOT / "agents" / "create_agents.py").read_text(encoding="utf-8")

    assert "EVIDENCE_SYNTHESIS_SCHEMA" in source
    assert "EVIDENCE_SYNTHESIS_RESPONSE_FORMAT" in source
    assert "sentinel-evidence-synthesizer-agent" in source
    assert "FOUNDRY_EVIDENCE_SYNTHESIZER_AGENT_MODEL" in source
    for field in [
        "answerability",
        "direct_answer",
        "operator_dialogue",
        "source_quote",
        "checked_evidence_count",
        "explicit_support_count",
        "unknown_count",
        "decision_impact_hint",
    ]:
        assert f'"{field}"' in source


def test_foundry_agent_schemas_require_canonical_research_evidence() -> None:
    source = (ROOT / "agents" / "create_agents.py").read_text(encoding="utf-8")

    assert "RESEARCH_OUTPUT_SCHEMA" in source
    assert "response_format=RESEARCH_OUTPUT_RESPONSE_FORMAT" not in source

    for field in [
        "document_id",
        "document_title",
        "section_heading",
        "text_excerpt",
        "source_blob",
        "index_name",
        "chunk_index",
        "score",
        "agent_recommendation_rationale",
    ]:
        assert f'"{field}"' in source
