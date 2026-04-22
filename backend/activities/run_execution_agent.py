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
import uuid
from datetime import datetime, timedelta, timezone

import azure.durable_functions as df
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from openai import AzureOpenAI

from shared.agent_telemetry import log_trace_json
from shared.cosmos_client import get_cosmos_client
from shared.incident_store import get_incident_by_id, patch_incident_by_id

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
    incident = get_incident_by_id(db, incident_id)
    equipment_id = incident.get("equipment_id") or incident.get("equipmentId") or ai_result.get("equipment_id", "unknown")
    execution_result = _persist_execution_artifacts(
        db=db,
        incident=incident,
        ai_result=ai_result,
        capa_plan=capa_plan,
        approver=approver,
        now_iso=now_iso,
    )

    # Update incident with CAPA plan
    patch_incident_by_id(
        db,
        incident_id,
        patch_operations=[
            {"op": "set", "path": "/status", "value": "in_progress"},
            {"op": "set", "path": "/capaPlans", "value": capa_plan.get("actions", [])},
            {"op": "set", "path": "/approvedBy", "value": approver},
            {"op": "set", "path": "/approvedAt", "value": now_iso},
            {"op": "set", "path": "/executionResult", "value": execution_result},
            {"op": "set", "path": "/workflow_state", "value": {
                **incident.get("workflow_state", {}),
                "current_step": "executing_approved_actions",
                "assigned_to": approver,
                "execution_started_at": now_iso,
                "work_order_id": execution_result.get("work_order_id"),
                "audit_entry_id": execution_result.get("audit_entry_id"),
            }},
            {"op": "set", "path": "/updatedAt", "value": now_iso},
            {"op": "set", "path": "/updated_at", "value": now_iso},
        ],
    )

    _update_approval_task_execution(db, incident_id, execution_result, now_iso)

    # Log event
    events = db.get_container_client("incident_events")
    events.upsert_item(
        {
            "id": f"{incident_id}-approved-{int(datetime.now(timezone.utc).timestamp())}",
            "incidentId": incident_id,
            "incident_id": incident_id,
            "eventType": "decision_approved",
            "action": "execution_started",
            "actor": "Execution Agent",
            "actor_type": "agent",
            "approver": approver,
            "capaActions": capa_plan.get("actions", []),
            "executionResult": execution_result,
            "details": (
                f"Execution started after approval by {approver}. "
                f"Generated {len(capa_plan.get('actions', []))} CAPA actions."
            ),
            "timestamp": now_iso,
        }
    )

    logger.info("CAPA plan created for incident %s — %d actions", incident_id, len(capa_plan.get("actions", [])))
    return {
        "incident_id": incident_id,
        "status": "in_progress",
        "equipment_id": equipment_id,
        "capa_action_count": len(capa_plan.get("actions", [])),
        "capa_plan": capa_plan,
        **execution_result,
    }


def _generate_capa_plan(incident_id: str, ai_result: dict, approver: str) -> dict:
    """Call gpt-4o to produce a structured CAPA action plan."""
    oai = AzureOpenAI(api_key=OPENAI_KEY, azure_endpoint=OPENAI_ENDPOINT, api_version="2024-02-01")

    system_prompt = (
        "You are a GMP CAPA specialist. Given the AI analysis and recommendations, "
        "generate a concrete, numbered CAPA action plan. "
        "Each action must include: title, owner_role, priority (P1/P2/P3), deadline_days (integer), "
        "and description. "
        'Respond with JSON: {"actions": [...], "summary": "..."}.'
    )

    user_prompt = (
        f"Incident: {incident_id}\n"
        f"Approved by: {approver}\n\n"
        f"Root-cause analysis:\n{ai_result.get('analysis', '')}\n\n"
        f"Recommendations:\n" + "\n".join(f"- {r}" for r in ai_result.get("recommendations", []))
    )

    log_trace_json(
        incident_id=incident_id,
        more_info_round=0,
        trace_kind="execution_user_prompt",
        payload={"system_prompt": system_prompt, "user_prompt": user_prompt, "model": GPT4O_DEPLOYMENT},
        metadata={"agent_name": "execution", "status": "started"},
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
        raw_content = response.choices[0].message.content or "{}"
        usage = response.usage
        usage_payload = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
            "model": GPT4O_DEPLOYMENT,
        } if usage is not None else None
        log_trace_json(
            incident_id=incident_id,
            more_info_round=0,
            trace_kind="thread_messages",
            payload={
                "status": "completed",
                "usage": usage_payload,
                "messages": [{"role": "assistant", "content": raw_content}],
            },
            metadata={"agent_name": "execution", "status": "completed"},
        )
        return json.loads(raw_content)
    except Exception as exc:
        logger.error("CAPA plan generation failed: %s", exc)
        log_trace_json(
            incident_id=incident_id,
            more_info_round=0,
            trace_kind="thread_messages",
            payload={"status": "failed", "error": str(exc)},
            metadata={"agent_name": "execution", "status": "failed"},
        )
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


def _persist_execution_artifacts(
    db,
    incident: dict,
    ai_result: dict,
    capa_plan: dict,
    approver: str,
    now_iso: str,
) -> dict:
    """Write demo execution artifacts that stand in for CMMS/QMS MCP calls."""
    incident_id = incident["id"]
    equipment_id = incident.get("equipment_id") or incident.get("equipmentId") or "unknown"
    actions = capa_plan.get("actions", [])
    first_action = actions[0] if actions else {}

    # Prefer operator-confirmed drafts stored in approval-tasks over AI-generated ones
    _ai_wo = ai_result.get("work_order_draft") if isinstance(ai_result.get("work_order_draft"), dict) else {}
    _ai_ae = ai_result.get("audit_entry_draft") if isinstance(ai_result.get("audit_entry_draft"), dict) else {}
    try:
        _approval_tasks = db.get_container_client("approval-tasks")
        _task_doc = _approval_tasks.read_item(f"approval-{incident_id}", partition_key=incident_id)
        work_order_draft = _task_doc.get("operatorWorkOrderDraft") or _ai_wo
        audit_entry_draft = _task_doc.get("operatorAuditEntryDraft") or _ai_ae
    except Exception:  # noqa: BLE001
        work_order_draft = _ai_wo
        audit_entry_draft = _ai_ae

    container = db.get_container_client("capa-plans")
    year = datetime.now(timezone.utc).strftime("%Y")
    work_order_id = f"WO-{year}-{uuid.uuid4().hex[:6].upper()}"
    audit_entry_id = f"AE-{year}-{uuid.uuid4().hex[:6].upper()}"
    capa_plan_id = f"CAPA-{incident_id}"
    deadline_days = _as_int(first_action.get("deadline_days"), 1)
    due_date = (datetime.now(timezone.utc) + timedelta(days=deadline_days)).date().isoformat()

    capa_doc = {
        "id": capa_plan_id,
        "incidentId": incident_id,
        "incident_id": incident_id,
        "type": "capa_plan",
        "status": "approved",
        "actions": actions,
        "summary": capa_plan.get("summary", ""),
        "approved_by": approver,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    work_order_doc = {
        "id": work_order_id,
        "incidentId": incident_id,
        "incident_id": incident_id,
        "equipment_id": equipment_id,
        "type": "work_order",
        "title": work_order_draft.get("title") or first_action.get("title") or f"Corrective maintenance for {equipment_id}",
        "description": work_order_draft.get("description") or first_action.get("description") or ai_result.get("recommendation", ""),
        "priority": work_order_draft.get("priority") or first_action.get("priority") or ai_result.get("risk_level", "high"),
        "assigned_to": first_action.get("owner_role", "maintenance_team"),
        "due_date": due_date,
        "work_type": "corrective",
        "status": "open",
        "source_system": "sentinel-intelligence",
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    audit_entry_doc = {
        "id": audit_entry_id,
        "incidentId": incident_id,
        "incident_id": incident_id,
        "equipment_id": equipment_id,
        "type": "audit_entry",
        "deviation_type": audit_entry_draft.get("deviation_type") or ai_result.get("classification", "process_deviation"),
        "description": audit_entry_draft.get("description") or ai_result.get("analysis", ""),
        "root_cause": audit_entry_draft.get("root_cause") or ai_result.get("root_cause", ""),
        "capa_actions": audit_entry_draft.get("capa_actions") or _format_actions(actions),
        "batch_disposition": audit_entry_draft.get("batch_disposition") or ai_result.get("batch_disposition", "pending_quality_review"),
        "prepared_by": approver,
        "status": "draft",
        "regulatory_framework": "EU GMP Annex 15; GMP Annex - Qualification and Validation",
        "source_system": "sentinel-intelligence",
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    for doc in (capa_doc, work_order_doc, audit_entry_doc):
        container.upsert_item(doc)

    return {
        "capa_plan_id": capa_plan_id,
        "work_order_id": work_order_id,
        "audit_entry_id": audit_entry_id,
        "work_order_url": f"https://cmms.sentinelpharma.local/work-orders/{work_order_id}",
        "audit_entry_url": f"https://qms.sentinelpharma.local/deviations/{audit_entry_id}",
        "created_at": now_iso,
    }


def _update_approval_task_execution(db, incident_id: str, execution_result: dict, now_iso: str) -> None:
    approval_tasks = db.get_container_client("approval-tasks")
    try:
        approval_tasks.patch_item(
            item=f"approval-{incident_id}",
            partition_key=incident_id,
            patch_operations=[
                {"op": "set", "path": "/status", "value": "executed"},
                {"op": "set", "path": "/executionResult", "value": execution_result},
                {"op": "set", "path": "/executedAt", "value": now_iso},
                {"op": "set", "path": "/updatedAt", "value": now_iso},
            ],
        )
    except CosmosResourceNotFoundError:
        approval_tasks.create_item(
            {
                "id": f"approval-{incident_id}",
                "incidentId": incident_id,
                "status": "executed",
                "executionResult": execution_result,
                "executedAt": now_iso,
                "updatedAt": now_iso,
            }
        )


def _format_actions(actions: list[dict]) -> str:
    return "\n".join(
        f"{idx}. {action.get('title') or action.get('action') or action.get('description', '')}"
        for idx, action in enumerate(actions, start=1)
    )


def _as_int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
