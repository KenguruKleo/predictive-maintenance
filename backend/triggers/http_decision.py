"""
HTTP Trigger — POST /api/incidents/{incident_id}/decision (T-024, T-029)

Resumes a waiting Durable orchestrator with the operator's decision.

Request body:
    {
        "action": "approved" | "rejected" | "more_info",
        "user_id": "jane.smith",
        "role": "operator" | "qa-manager",
        "reason": "Optional free-text justification",
        "question": "Optional — required when action=more_info"
    }

Response:
    202 Accepted — {"status": "decision_received", "instance_id": "..."}
    400 Bad Request — missing required fields
    404 Not Found — no running orchestrator for this incident
    500 Internal Server Error
"""

import json
import logging
import os
from datetime import datetime, timezone

import azure.durable_functions as df
import azure.functions as func
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from shared.cosmos_client import get_cosmos_client
from shared.incident_store import get_incident_by_id, patch_incident_by_id
from shared.signalr_client import notify_incident_status_changed_sync
from utils.auth import AuthError, get_caller_id, get_caller_roles, require_any_role
from utils.validation import normalize_free_text, sanitize_string_fields

logger = logging.getLogger(__name__)

VALID_ACTIONS = {"approved", "rejected", "more_info"}
DB_NAME = os.getenv("COSMOS_DATABASE", "sentinel-intelligence")
ALLOWED_ROLES = ["Operator", "QAManager"]

WORKFLOW_ROLE_BY_APP_ROLE = {
    "Operator": "operator",
    "QAManager": "qa-manager",
}

bp = df.Blueprint()


@bp.route(
    route="incidents/{incident_id}/decision",
    methods=["POST"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
@bp.durable_client_input(client_name="client")
async def http_decision(
    req: func.HttpRequest,
    client,
) -> func.HttpResponse:
    """Accept operator decision and raise external event on Durable orchestrator."""
    incident_id: str = req.route_params.get("incident_id", "")
    if not incident_id:
        return _error(400, "incident_id path parameter is required")

    try:
        roles = get_caller_roles(req)
        require_any_role(roles, ALLOWED_ROLES)
    except AuthError as exc:
        return _error(exc.status_code, exc.message)

    caller_workflow_roles = {
        WORKFLOW_ROLE_BY_APP_ROLE[role]
        for role in roles
        if role in WORKFLOW_ROLE_BY_APP_ROLE
    }
    if not caller_workflow_roles:
        return _error(403, "Access denied. No decision workflow role is assigned to the caller.")

    caller_id = get_caller_id(req).strip()
    if not caller_id:
        return _error(401, "Authentication required")

    # Parse body
    try:
        body: dict = req.get_json()
    except ValueError:
        return _error(400, "Request body must be valid JSON")

    # Sanitize string fields (OWASP LLM01 — prompt injection guard)
    try:
        sanitize_string_fields(body)
    except ValueError as exc:
        return _error(400, str(exc))

    # Validate required fields
    action = body.get("action", "")
    if action not in VALID_ACTIONS:
        return _error(
            400,
            f"'action' must be one of: {', '.join(sorted(VALID_ACTIONS))}",
        )

    reason_text = normalize_free_text(body.get("reason", ""))
    question_text = normalize_free_text(body.get("question", ""))

    if action == "more_info" and not question_text:
        return _error(400, "'question' is required when action=more_info")

    # Parse optional operator-confirmed draft fields
    work_order_draft = body.get("work_order_draft") or None
    audit_entry_draft = body.get("audit_entry_draft") or None
    if work_order_draft is not None and not isinstance(work_order_draft, dict):
        return _error(400, "'work_order_draft' must be an object")
    if audit_entry_draft is not None and not isinstance(audit_entry_draft, dict):
        return _error(400, "'audit_entry_draft' must be an object")
    if action == "approved":
        if not work_order_draft or not str(work_order_draft.get("description", "")).strip():
            return _error(400, "'work_order_draft.description' is required when action=approved")
        if not audit_entry_draft or not str(audit_entry_draft.get("description", "")).strip():
            return _error(400, "'audit_entry_draft.description' is required when action=approved")

    body_user_id = str(body.get("user_id", "") or "").strip()
    if body_user_id and body_user_id != caller_id:
        logger.warning(
            "Decision caller mismatch for incident=%s: body_user_id=%s auth_user_id=%s",
            incident_id,
            body_user_id,
            caller_id,
        )

    try:
        workflow_role = _get_target_workflow_role(incident_id)
    except CosmosResourceNotFoundError:
        return _error(404, f"Incident '{incident_id}' not found")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to load incident decision routing for %s: %s", incident_id, exc)
        return _error(500, "Failed to determine the active decision owner for this incident")

    if workflow_role not in caller_workflow_roles:
        return _error(
            403,
            f"Access denied. Incident is currently awaiting {workflow_role} decision.",
        )

    instance_id = f"durable-{incident_id}"

    # Verify the orchestrator instance exists and is waiting
    status = await client.get_status(instance_id)
    if status is None or status.runtime_status not in (
        df.OrchestrationRuntimeStatus.Running,
        df.OrchestrationRuntimeStatus.Pending,
    ):
        return _error(
            404,
            f"No active orchestrator found for incident '{incident_id}'. "
            f"Status: {status.runtime_status if status else 'NOT_FOUND'}",
        )

    # Raise the operator_decision event to resume the orchestrator
    now_iso = datetime.now(timezone.utc).isoformat()

    # Compute operator_agrees_with_agent
    agent_rec = str(body.get("agent_recommendation") or "").strip().upper() or None
    if agent_rec and agent_rec not in ("APPROVE", "REJECT"):
        agent_rec = None
    if agent_rec and action in ("approved", "rejected"):
        decision_positive = action == "approved"
        agent_positive = agent_rec == "APPROVE"
        operator_agrees = decision_positive == agent_positive
    else:
        operator_agrees = None  # more_info or no agent recommendation

    event_data = {
        "action": action,
        "user_id": caller_id,
        "role": workflow_role,
        "reason": reason_text,
        "question": question_text,
        "agent_recommendation": agent_rec,
        "operator_agrees_with_agent": operator_agrees,
        "work_order_draft": work_order_draft,
        "audit_entry_draft": audit_entry_draft,
    }

    try:
        status_transition = _record_decision(incident_id, event_data, now_iso)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to persist operator decision for %s: %s", incident_id, exc)
        return _error(500, "Failed to persist operator decision. Please retry.")

    await client.raise_event(instance_id, "operator_decision", event_data)

    if status_transition.get("previous_status") != status_transition.get("new_status"):
        notify_incident_status_changed_sync(
            incident_id=incident_id,
            new_status=status_transition.get("new_status", ""),
            previous_status=status_transition.get("previous_status"),
            equipment_id=status_transition.get("equipment_id") or None,
        )

    logger.info(
        "operator_decision raised for incident=%s action=%s user=%s",
        incident_id,
        action,
        caller_id,
    )

    return func.HttpResponse(
        body=json.dumps({"status": "decision_received", "instance_id": instance_id}),
        status_code=202,
        mimetype="application/json",
    )


def _error(status_code: int, message: str) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps({"error": message}),
        status_code=status_code,
        mimetype="application/json",
    )


def _normalize_workflow_role(value: object) -> str:
    normalized = str(value or "").strip().lower().replace("_", "-")
    if normalized == "qamanager":
        return "qa-manager"
    return normalized


def _get_target_workflow_role(incident_id: str) -> str:
    client = get_cosmos_client()
    db = client.get_database_client(DB_NAME)
    incident = get_incident_by_id(db, incident_id)
    workflow_state = incident.get("workflow_state") or {}

    target_role = _normalize_workflow_role(workflow_state.get("target_role"))
    if target_role:
        return target_role

    current_step = str(workflow_state.get("current_step") or "").strip().lower()
    incident_status = str(incident.get("status") or "").strip().lower()
    if current_step == "awaiting_qa_manager_decision" or incident_status == "escalated":
        return "qa-manager"
    return "operator"


def _record_decision(incident_id: str, decision: dict, now_iso: str) -> dict:
    """Persist the user's decision before resuming the Durable instance."""
    action = decision["action"]
    incident_status = {
        "approved": "approved",
        "rejected": "rejected",
        "more_info": "awaiting_agents",
    }[action]
    task_status = {
        "approved": "approved",
        "rejected": "rejected",
        "more_info": "more_info_requested",
    }[action]

    client = get_cosmos_client()
    db = client.get_database_client(DB_NAME)
    incident: dict = {}
    previous_status: str | None = None
    try:
        incident = get_incident_by_id(db, incident_id)
        previous_status = str(incident.get("status") or "").strip() or None
    except Exception:  # noqa: BLE001
        # Live status push is best-effort here; the decision must still persist.
        incident = {}
        previous_status = None

    approval_tasks = db.get_container_client("approval-tasks")
    task_id = f"approval-{incident_id}"
    try:
        _patch_ops = [
                {"op": "set", "path": "/status", "value": task_status},
                {"op": "set", "path": "/decision", "value": decision},
                {"op": "set", "path": "/decidedBy", "value": decision["user_id"]},
                {"op": "set", "path": "/decidedAt", "value": now_iso},
                {"op": "set", "path": "/updatedAt", "value": now_iso},
            ]
        if decision.get("work_order_draft"):
            _patch_ops.append({"op": "set", "path": "/operatorWorkOrderDraft", "value": decision["work_order_draft"]})
        if decision.get("audit_entry_draft"):
            _patch_ops.append({"op": "set", "path": "/operatorAuditEntryDraft", "value": decision["audit_entry_draft"]})
        approval_tasks.patch_item(
            item=task_id,
            partition_key=incident_id,
            patch_operations=_patch_ops,
        )
    except CosmosResourceNotFoundError:
        _create_doc = {
                "id": task_id,
                "incidentId": incident_id,
                "durableInstanceId": f"durable-{incident_id}",
                "status": task_status,
                "decision": decision,
                "decidedBy": decision["user_id"],
                "decidedAt": now_iso,
                "updatedAt": now_iso,
            }
        if decision.get("work_order_draft"):
            _create_doc["operatorWorkOrderDraft"] = decision["work_order_draft"]
        if decision.get("audit_entry_draft"):
            _create_doc["operatorAuditEntryDraft"] = decision["audit_entry_draft"]
        approval_tasks.create_item(_create_doc)

    incident_patch_ops = [
        {"op": "set", "path": "/status", "value": incident_status},
        {"op": "set", "path": "/lastDecision", "value": decision},
        {"op": "set", "path": "/updatedAt", "value": now_iso},
        {"op": "set", "path": "/updated_at", "value": now_iso},
    ]
    if decision.get("work_order_draft"):
        incident_patch_ops.append({"op": "set", "path": "/operatorWorkOrderDraft", "value": decision["work_order_draft"]})
    if decision.get("audit_entry_draft"):
        incident_patch_ops.append({"op": "set", "path": "/operatorAuditEntryDraft", "value": decision["audit_entry_draft"]})
    patch_incident_by_id(db, incident_id, incident_patch_ops)

    events = db.get_container_client("incident_events")
    events.upsert_item(
        {
            "id": f"{incident_id}-decision-{int(datetime.now(timezone.utc).timestamp())}",
            "incidentId": incident_id,
            "incident_id": incident_id,
            "eventType": "operator_decision",
            "action": action,
            "actor": decision["user_id"],
            "actor_type": "human",
            "userId": decision["user_id"],
            "role": decision.get("role", "operator"),
            "incidentStatus": incident_status,
            "reason": decision.get("reason", ""),
            "question": decision.get("question", ""),
            "details": decision.get("question") or decision.get("reason") or f"Operator selected {action}.",
            "timestamp": now_iso,
        }
    )

    return {
        "previous_status": previous_status,
        "new_status": incident_status,
        "equipment_id": str(incident.get("equipment_id") or incident.get("equipmentId") or ""),
    }
