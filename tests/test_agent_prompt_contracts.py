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

    assert "must call `research_agent`" in prompt
    assert "Do not write or simulate `tool_calls_log`" in prompt
    assert "Do not invent citations" in prompt
