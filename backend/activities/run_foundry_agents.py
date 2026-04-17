"""
Activity: run_foundry_agents — call Foundry Orchestrator Agent (T-024, ADR-002)

Orchestrator Agent manages the Research → Document pipeline natively via
Connected Agents (AgentTool). This activity creates a thread, sends the full
incident context as a user message, and waits for the agent to produce a
structured JSON analysis.

Returns:
    {
        "analysis": str,
        "root_cause": str,
        "recommendations": list[dict],
        "regulatory_refs": list[str],
        "sop_refs": list[str],
        "confidence": float,          # 0.0–1.0
        "risk_level": str,
        "classification": str,
        "batch_disposition": str,
        "evidence_citations": list,
        "work_order_draft": dict,
        "audit_entry_draft": dict,
        "raw_response": str,          # always present for audit trail
    }
"""

import json
import logging
import os
import re
from datetime import datetime, timezone

import azure.durable_functions as df
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    AgentThreadCreationOptions,
    MessageRole,
    ThreadMessageOptions,
)
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

ORCHESTRATOR_AGENT_ID = os.environ.get("ORCHESTRATOR_AGENT_ID", "")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))

bp = df.Blueprint()


@bp.activity_trigger(input_name="input_data")
def run_foundry_agents(input_data: dict) -> dict:
    incident_id: str = input_data["incident_id"]
    context_data: dict = input_data["context"]
    more_info_round: int = input_data.get("more_info_round", 0)

    logger.info(
        "run_foundry_agents: incident=%s round=%d", incident_id, more_info_round
    )

    if not ORCHESTRATOR_AGENT_ID:
        raise EnvironmentError(
            "ORCHESTRATOR_AGENT_ID env var is not set. "
            "Run agents/create_agents.py first to provision Foundry agents."
        )

    prompt = _build_prompt(incident_id, context_data, more_info_round)
    result = _call_orchestrator_agent(prompt)

    # Confidence gate (RAI Gap #4): log warning but still return result
    confidence = result.get("confidence", 0.0)
    if confidence < CONFIDENCE_THRESHOLD:
        logger.warning(
            "Low confidence %.2f for incident %s (threshold=%.2f). "
            "Consider requesting more_info.",
            confidence,
            incident_id,
            CONFIDENCE_THRESHOLD,
        )
        result["confidence_flag"] = "LOW_CONFIDENCE"

    return result


# ── Internal helpers ──────────────────────────────────────────────────────


def _call_orchestrator_agent(prompt: str) -> dict:
    """Create a Foundry thread, run the Orchestrator Agent, return parsed result."""
    # Use the connection string directly for Hub-based ML projects.
    # AgentsClient activates the legacy ML workspace endpoint when
    # AZURE_AI_AGENTS_TESTS_IS_TEST_RUN=True is set.
    endpoint = os.environ.get(
        "AZURE_AI_FOUNDRY_AGENTS_ENDPOINT",
        os.environ.get("AZURE_AI_FOUNDRY_PROJECT_CONNECTION_STRING", ""),
    )
    os.environ.setdefault("AZURE_AI_AGENTS_TESTS_IS_TEST_RUN", "True")
    client = AgentsClient(endpoint=endpoint, credential=DefaultAzureCredential())

    with client:
        run = client.create_thread_and_process_run(
            agent_id=ORCHESTRATOR_AGENT_ID,
            thread=AgentThreadCreationOptions(
                messages=[
                    ThreadMessageOptions(role=MessageRole.USER, content=prompt)
                ]
            ),
        )

        if run.status == "failed":
            raise RuntimeError(
                f"Foundry Orchestrator run failed: {getattr(run, 'last_error', run.status)}"
            )

        messages = client.list_messages(thread_id=run.thread_id)

        # list_messages returns newest-first; first ASSISTANT message is the answer
        raw_text = ""
        for msg in messages:
            if msg.role == MessageRole.ASSISTANT:
                for block in msg.content:
                    if hasattr(block, "text"):
                        raw_text += block.text.value
                break

        logger.debug(
            "Foundry raw response (first 500 chars): %s", raw_text[:500]
        )
        return _parse_response(raw_text)


def _build_prompt(incident_id: str, context_data: dict, more_info_round: int) -> str:
    """Build the user message that drives the Orchestrator Agent."""
    equipment = context_data.get("equipment", {})
    batch = context_data.get("batch", {})
    recent_incidents = context_data.get("recent_incidents", [])
    alert_payload = context_data.get("alert_payload", {})
    operator_questions = context_data.get("operator_questions", [])

    lines = [
        f"## GMP Deviation Analysis Request — Incident {incident_id}",
        f"**Timestamp:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "### Alert Payload",
        "```json",
        json.dumps(alert_payload, indent=2, default=str),
        "```",
        "",
        "### Equipment Context",
        "```json",
        json.dumps(equipment, indent=2, default=str),
        "```",
        "",
        "### Active Batch",
        "```json",
        json.dumps(batch, indent=2, default=str),
        "```",
        "",
        f"### Recent Incidents (last {len(recent_incidents)} on this equipment)",
        "```json",
        json.dumps(recent_incidents, indent=2, default=str),
        "```",
    ]

    if operator_questions:
        lines += [
            "",
            f"### Operator Follow-up Questions (round {more_info_round})",
        ]
        for q in operator_questions:
            lines.append(
                f"- **Round {q['round']}** ({q.get('asked_by', 'operator')}): {q['question']}"
            )

    lines += [
        "",
        "---",
        "### Instructions",
        (
            "Use your Research sub-agent to gather equipment history, batch context, "
            "BPR constraints, relevant SOPs, GMP regulations, and similar past cases. "
            "Then use your Document sub-agent to produce the final analysis."
        ),
        "",
        "Return your response as a **single JSON block** using this exact schema:",
        "```json",
        json.dumps(
            {
                "incident_id": incident_id,
                "classification": "process_parameter_excursion | equipment_malfunction | ...",
                "risk_level": "low | medium | high | critical",
                "confidence": 0.85,
                "root_cause": "Primary root cause in one sentence",
                "analysis": "Detailed root cause analysis with evidence.",
                "recommendation": "Recommended immediate action.",
                "capa_suggestion": "1. ...\n2. ...",
                "regulatory_reference": "SOP-DEV-001 §4.2; GMP Annex 15 §6.3",
                "batch_disposition": "conditional_release_pending_testing | rejected | release",
                "recommendations": [
                    {
                        "action": "...",
                        "priority": "critical|high|medium|low",
                        "owner": "...",
                        "deadline_days": 0,
                    }
                ],
                "regulatory_refs": ["21 CFR Part 211.xx"],
                "sop_refs": ["SOP-DEV-001"],
                "evidence_citations": [
                    {"source": "SOP-DEV-001", "section": "§4.2", "text_excerpt": "..."}
                ],
                "work_order_draft": {
                    "title": "...",
                    "description": "...",
                    "priority": "high",
                    "estimated_hours": 4,
                },
                "audit_entry_draft": {
                    "deviation_type": "...",
                    "description": "...",
                    "root_cause": "...",
                    "capa_actions": "...",
                },
            },
            indent=2,
        ),
        "```",
        "",
        "Never fabricate data. Cite all sources. If confidence is below 0.75, "
        "set risk_level to 'LOW_CONFIDENCE' and explain what additional information "
        "would raise confidence.",
    ]

    return "\n".join(lines)


def _parse_response(raw_text: str) -> dict:
    """Extract JSON block from agent response, with graceful fallback."""
    # Try ```json ... ``` block first
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            data.setdefault("raw_response", raw_text)
            return data
        except json.JSONDecodeError:
            pass

    # Try to parse the whole response as JSON
    try:
        data = json.loads(raw_text.strip())
        data.setdefault("raw_response", raw_text)
        return data
    except json.JSONDecodeError:
        pass

    # Fallback — unstructured response (shouldn't happen in production)
    logger.warning("Could not parse structured JSON from Foundry agent response")
    return {
        "analysis": raw_text[:2000] if raw_text else "Analysis not available.",
        "root_cause": "Could not determine root cause automatically.",
        "classification": "unknown",
        "risk_level": "unknown",
        "confidence": 0.5,
        "confidence_flag": "PARSE_ERROR",
        "recommendations": [],
        "regulatory_refs": [],
        "sop_refs": [],
        "evidence_citations": [],
        "work_order_draft": {},
        "audit_entry_draft": {},
        "batch_disposition": "hold_pending_review",
        "raw_response": raw_text,
    }
