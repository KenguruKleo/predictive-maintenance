"""
Orchestrator Agent definition (T-024, ADR-002)

Defines the Orchestrator Agent with Research + Document connected sub-agents.
Imported by create_agents.py.
"""

import os
from pathlib import Path

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "orchestrator_system.md").read_text(
    encoding="utf-8"
)

AGENT_NAME = "sentinel-orchestrator-agent"
MODEL = (
    os.getenv("FOUNDRY_ORCHESTRATOR_AGENT_MODEL")
    or os.getenv("FOUNDRY_AGENT_MODEL")
    or "gpt-4o"
).strip()
