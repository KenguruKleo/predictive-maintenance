"""
HTTP Trigger — GET /api/incidents/{id}/events (T-031)

Returns the chronological audit event timeline for an incident.
Events are stored in the canonical `incident_events` Cosmos container, but
legacy documents may still use mixed field names. This endpoint normalizes
those shapes for the React approval and audit UI.
"""

import json
import logging
from datetime import datetime

import azure.functions as func

from shared.cosmos_client import get_container
from utils.auth import AuthError, get_caller_roles, require_any_role

logger = logging.getLogger(__name__)

bp = func.Blueprint()

ALL_ROLES = ["Operator", "QAManager", "MaintenanceTech", "Auditor", "ITAdmin"]


@bp.route(
    route="incidents/{incident_id}/events",
    methods=["GET"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def get_incident_events(req: func.HttpRequest) -> func.HttpResponse:
    """Return chronological event timeline for an incident."""
    try:
        roles = get_caller_roles(req)
        require_any_role(roles, ALL_ROLES)
    except AuthError as exc:
        return _error(exc.status_code, exc.message)

    incident_id: str = req.route_params.get("incident_id", "").strip()
    if not incident_id:
        return _error(400, "incident_id is required")

    try:
        container = get_container("incident_events")
        items = list(container.query_items(
            query=(
                "SELECT * FROM c WHERE (c.incident_id = @incident_id OR c.incidentId = @incident_id) "
                "ORDER BY c.timestamp ASC"
            ),
            parameters=[{"name": "@incident_id", "value": incident_id}],
            enable_cross_partition_query=True,
        ))
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "incident_events query failed for %s (container may not exist yet): %s",
            incident_id,
            exc,
        )
        items = []

    normalized = sorted(
        (_normalize_event(item, incident_id) for item in items),
        key=lambda item: _sort_key(item.get("timestamp", "")),
    )

    return _json({"incident_id": incident_id, "events": normalized, "total": len(normalized)})


def _normalize_event(item: dict, incident_id: str) -> dict:
    timestamp = item.get("timestamp") or item.get("createdAt") or item.get("closedAt") or ""
    action = _normalize_action(item)
    actor = _normalize_actor(item, action)
    actor_type = _normalize_actor_type(item, action)
    details = _normalize_details(item, action)

    return {
        "id": item.get("id") or f"{incident_id}-{action}-{timestamp}",
        "incident_id": item.get("incident_id") or item.get("incidentId") or incident_id,
        "timestamp": timestamp,
        "actor": actor,
        "actor_type": actor_type,
        "action": action,
        "details": details,
        "updated_fields": item.get("updated_fields") or item.get("updatedFields") or [],
        "status": item.get("incidentStatus") or item.get("finalStatus") or item.get("status"),
    }


def _normalize_action(item: dict) -> str:
    raw_action = str(item.get("action") or "").strip()
    event_type = str(item.get("eventType") or item.get("type") or "").strip()

    if raw_action == "more_info" and item.get("question"):
        return "operator_question"

    if raw_action:
        return raw_action

    mapping = {
        "approval_required": "approval_requested",
        "escalation": "escalated",
        "decision_approved": "execution_started",
        "incident_rejected": "incident_rejected",
        "audit_finalized": "audit_finalized",
    }
    return mapping.get(event_type, event_type or "status_updated")


def _normalize_actor(item: dict, action: str) -> str:
    if item.get("actor"):
        return str(item["actor"])

    if item.get("userId"):
        return str(item["userId"])

    if item.get("approver"):
        return str(item["approver"])

    if action == "agent_response":
        return "AI Agent"

    if action in {"approval_requested", "escalated", "audit_finalized", "incident_rejected"}:
        return "System"

    if action == "execution_started":
        return "Execution Agent"

    target_role = item.get("targetRole")
    if target_role:
        return str(target_role)

    return "System"


def _normalize_actor_type(item: dict, action: str) -> str:
    actor_type = str(item.get("actor_type") or item.get("actorType") or "").strip().lower()
    if actor_type in {"system", "agent", "human"}:
        return actor_type

    if action in {"operator_question", "approved", "rejected", "more_info"}:
        return "human"

    if action in {"agent_response", "execution_started"}:
        return "agent"

    return "system"


def _normalize_details(item: dict, action: str) -> str:
    if item.get("details"):
        return str(item["details"])

    if item.get("message"):
        return str(item["message"])

    if action == "operator_question":
        return str(item.get("question") or "Operator requested additional analysis.")

    if action == "approved":
        reason = item.get("reason")
        return str(reason or "Operator approved the recommendation.")

    if action == "rejected":
        reason = item.get("reason") or item.get("rejectionReason")
        return str(reason or "Operator rejected the recommendation.")

    if action == "approval_requested":
        target_role = item.get("targetRole") or "operator"
        return f"Approval requested from {target_role}."

    if action == "escalated":
        target_role = item.get("targetRole") or "qa-manager"
        return f"Incident escalated to {target_role}."

    if action == "execution_started":
        execution_result = item.get("executionResult") or {}
        work_order_id = execution_result.get("work_order_id") if isinstance(execution_result, dict) else None
        if work_order_id:
            return f"Execution agent started CAPA workflow and created work order {work_order_id}."
        return "Execution agent started the approved CAPA workflow."

    if action == "incident_rejected":
        return str(item.get("rejectionReason") or "Incident was closed as rejected.")

    if action == "audit_finalized":
        final_status = item.get("finalStatus") or "closed"
        return f"Audit finalized. Incident status set to {final_status}."

    if item.get("incidentStatus"):
        return f"Incident status changed to {item['incidentStatus']}."

    return "Audit event recorded."


def _sort_key(timestamp: str) -> tuple[int, str]:
    if not timestamp:
        return (1, "")

    try:
        return (0, datetime.fromisoformat(timestamp.replace("Z", "+00:00")).isoformat())
    except ValueError:
        return (1, timestamp)


def _json(data) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps(data, default=str),
        status_code=200,
        mimetype="application/json",
    )


def _error(status: int, message: str) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps({"error": message}),
        status_code=status,
        mimetype="application/json",
    )
