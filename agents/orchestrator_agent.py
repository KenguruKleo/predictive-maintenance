"""
Orchestrator Agent definition (T-024, ADR-002)

Defines the Orchestrator Agent with Research + Document connected sub-agents.
Imported by create_agents.py.
"""

from pathlib import Path

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "orchestrator_system.md").read_text(
    encoding="utf-8"
)

AGENT_NAME = "sentinel-orchestrator-agent"
MODEL = "gpt-4o"
