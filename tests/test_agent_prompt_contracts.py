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
    assert "Follow-up dialogue rules" in prompt
    assert "Answer that concrete question first" in prompt
    assert "Never hide an evidence gap behind a generic phrase" in prompt
    assert "For count or comparison questions" in prompt
    assert "absence of a detail in an excerpt is unknown" in prompt
    assert "is not determinable from retrieved evidence" in prompt


def test_orchestrator_agent_has_no_connected_tools() -> None:
    source = (ROOT / "agents" / "create_agents.py").read_text(encoding="utf-8")

    orchestrator_section = source.split("# ── 3. Orchestrator Agent", 1)[1]
    orchestrator_section = orchestrator_section.split("print(\"\\n\" + \"=\" * 60)", 1)[0]
    assert "ConnectedAgentTool" not in orchestrator_section
    assert "research_connected" not in orchestrator_section
    assert "document_connected" not in orchestrator_section


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
