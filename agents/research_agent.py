"""
Research Agent definition (T-025) — sub-agent in Connected Agents pattern (ADR-002)

This module defines the Research Agent's tools and instructions.
It is imported by create_agents.py to provision the agent in Azure AI Foundry.

The Research Agent is NOT called directly from Durable Functions —
Foundry Orchestrator Agent calls it as a connected sub-agent (AgentTool).
"""

import os
from pathlib import Path

# System prompt loaded from prompts/research_system.md
SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "research_system.md").read_text(
    encoding="utf-8"
)

AGENT_NAME = "sentinel-research-agent"
MODEL = (
    os.getenv("FOUNDRY_RESEARCH_AGENT_MODEL")
    or os.getenv("FOUNDRY_AGENT_MODEL")
    or "gpt-4o-mini"
).strip()

# AI Search index names (created by T-037)
SEARCH_INDEXES = [
    "idx-sop-documents",
    "idx-equipment-manuals",
    "idx-gmp-policies",
    "idx-bpr-documents",
    "idx-incident-history",
]
