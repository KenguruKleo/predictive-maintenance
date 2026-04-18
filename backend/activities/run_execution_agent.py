"""
Activity: run_execution_agent — Execution Agent runs CAPA actions (T-024 §2)

Generates a structured CAPA execution plan via gpt-4o, writes it to Cosmos DB,
and transitions the incident to 'in_progress'.

Note: This is the second half of T-024. Will be replaced by a full Foundry
Execution Agent (T-027) in a future iteration.
"""

import json
import logging
import os
from datetime import datetime, timezone

import azure.durable_functions as df
from openai import AzureOpenAI

from shared.cosmos_client import get_cosmos_client
from shared.incident_store import patch_incident_by_id

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("COSMOS_DATABASE", "sentinel-intelligence")
OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
OPENAI_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
GPT4O_DEPLOYMENT = os.getenv("AZURE_OPENAI_GPT4O_DEPLOYMENT", "gpt-4o")

bp = df.Blueprint()


@bp.activity_trigger(input_name="input_data")
def run_execution_agent(input_data: dict) -> dict:
    incident_id: str = input_data["incident_id"]
    ai_result: dict = input_data.get("ai_result", {})
    approver: str = input_data.get("approver_id", input_data.get("approver", "unknown"))
    now_iso = datetime.now(timezone.utc).isoformat()

    logger.info("execute_decision for incident %s approved by %s", incident_id, approver)

    # ── Generate CAPA execution plan ───────────────────────────────────────
    capa_plan = _generate_capa_plan(incident_id, ai_result, approver)

    # ── Persist to Cosmos DB ───────────────────────────────────────────────
    client = get_cosmos_client()
    db = client.get_database_client(DB_NAME)

    # Update incident with CAPA plan
    patch_incident_by_id(
        db,
        incident_id,
        patch_operations=[
            {"op": "set", "path": "/status", "value": "in_progress"},
            {"op": "set", "path": "/capaPlans", "value": capa_plan.get("actions", [])},
            {"op": "set", "path": "/approvedBy", "value": approver},
            {"op": "set", "path": "/approvedAt", "value": now_iso},
            {"op": "set", "path": "/updatedAt", "value": now_iso},
        ],
    )

    # Log event
    events = db.get_container_client("incident_events")
    events.upsert_item(
        {
            "id": f"{incident_id}-approved-{int(datetime.now(timezone.utc).timestamp())}",
            "incidentId": incident_id,
            "eventType": "decision_approved",
            "approver": approver,
            "capaActions": capa_plan.get("actions", []),
            "timestamp": now_iso,
        }
    )

    logger.info("CAPA plan created for incident %s — %d actions", incident_id, len(capa_plan.get("actions", [])))
    return {
        "incident_id": incident_id,
        "status": "in_progress",
        "capa_action_count": len(capa_plan.get("actions", [])),
        "capa_plan": capa_plan,
    }


def _generate_capa_plan(incident_id: str, ai_result: dict, approver: str) -> dict:
    """Call gpt-4o to produce a structured CAPA action plan."""
    oai = AzureOpenAI(api_key=OPENAI_KEY, azure_endpoint=OPENAI_ENDPOINT, api_version="2024-02-01")

    system_prompt = (
        "You are a GMP CAPA specialist. Given the AI analysis and recommendations, "
        "generate a concrete, numbered CAPA action plan. "
        "Each action must include: title, owner_role, priority (P1/P2/P3), deadline_days (integer), "
        "and description. "
        "Respond with JSON: {\"actions\": [...], \"summary\": \"...\"}."
    )

    user_prompt = (
        f"Incident: {incident_id}\n"
        f"Approved by: {approver}\n\n"
        f"Root-cause analysis:\n{ai_result.get('analysis', '')}\n\n"
        f"Recommendations:\n" + "\n".join(f"- {r}" for r in ai_result.get("recommendations", []))
    )

    try:
        response = oai.chat.completions.create(
            model=GPT4O_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1000,
        )
        return json.loads(response.choices[0].message.content or "{}")
    except Exception as exc:
        logger.error("CAPA plan generation failed: %s", exc)
        return {
            "actions": [
                {
                    "title": "Manual CAPA required",
                    "owner_role": "qa-engineer",
                    "priority": "P1",
                    "deadline_days": 7,
                    "description": f"AI generation failed: {exc}",
                }
            ],
            "summary": "CAPA plan could not be auto-generated.",
        }
