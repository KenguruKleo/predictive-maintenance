"""
Document Agent definition (T-026) — sub-agent in Connected Agents pattern (ADR-002)

This module defines the Document Agent's instructions.
It is imported by create_agents.py to provision the agent in Azure AI Foundry.

The Document Agent is NOT called directly from Durable Functions —
Foundry Orchestrator Agent calls it as a connected sub-agent via AgentTool.
"""

import os
from pathlib import Path

# System prompt loaded from prompts/document_system.md
SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "document_system.md").read_text(
    encoding="utf-8"
)

AGENT_NAME = "sentinel-document-agent"
MODEL = (
    os.getenv("FOUNDRY_DOCUMENT_AGENT_MODEL")
    or os.getenv("FOUNDRY_AGENT_MODEL")
    or "gpt-4o-mini"
).strip()
