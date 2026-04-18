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
from shared.incident_store import patch_incident_by_id
from utils.validation import sanitize_string_fields

logger = logging.getLogger(__name__)

VALID_ACTIONS = {"approved", "rejected", "more_info"}
DB_NAME = os.getenv("COSMOS_DATABASE", "sentinel-intelligence")

bp = df.Blueprint()


@bp.route(
    route="incidents/{incident_id}/decision",
    methods=["POST"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
@bp.durable_client_input(client_name="client")
async def http_decision(
    req: func.HttpRequest,
    client: df.DurableOrchestrationClient,
) -> func.HttpResponse:
    """Accept operator decision and raise external event on Durable orchestrator."""
    incident_id: str = req.route_params.get("incident_id", "")
    if not incident_id:
        return _error(400, "incident_id path parameter is required")

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

    if action == "more_info" and not body.get("question"):
        return _error(400, "'question' is required when action=more_info")

    user_id = body.get("user_id", "")
    if not user_id:
        return _error(400, "'user_id' is required")

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
    event_data = {
        "action": action,
        "user_id": user_id,
        "role": body.get("role", "operator"),
        "reason": body.get("reason", ""),
        "question": body.get("question", ""),
    }

    try:
        _record_decision(incident_id, event_data, now_iso)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to persist operator decision for %s: %s", incident_id, exc)
        return _error(500, "Failed to persist operator decision. Please retry.")

    await client.raise_event(instance_id, "operator_decision", event_data)

    logger.info(
        "operator_decision raised for incident=%s action=%s user=%s",
        incident_id,
        action,
        user_id,
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


def _record_decision(incident_id: str, decision: dict, now_iso: str) -> None:
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

    approval_tasks = db.get_container_client("approval-tasks")
    task_id = f"approval-{incident_id}"
    try:
        approval_tasks.patch_item(
            item=task_id,
            partition_key=incident_id,
            patch_operations=[
                {"op": "set", "path": "/status", "value": task_status},
                {"op": "set", "path": "/decision", "value": decision},
                {"op": "set", "path": "/decidedBy", "value": decision["user_id"]},
                {"op": "set", "path": "/decidedAt", "value": now_iso},
                {"op": "set", "path": "/updatedAt", "value": now_iso},
            ],
        )
    except CosmosResourceNotFoundError:
        approval_tasks.create_item(
            {
                "id": task_id,
                "incidentId": incident_id,
                "durableInstanceId": f"durable-{incident_id}",
                "status": task_status,
                "decision": decision,
                "decidedBy": decision["user_id"],
                "decidedAt": now_iso,
                "updatedAt": now_iso,
            }
        )

    patch_incident_by_id(
        db,
        incident_id,
        [
            {"op": "set", "path": "/status", "value": incident_status},
            {"op": "set", "path": "/lastDecision", "value": decision},
            {"op": "set", "path": "/updatedAt", "value": now_iso},
            {"op": "set", "path": "/updated_at", "value": now_iso},
        ],
    )

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
