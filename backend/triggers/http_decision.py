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

import azure.durable_functions as df
import azure.functions as func

from utils.validation import sanitize_string_fields

logger = logging.getLogger(__name__)

VALID_ACTIONS = {"approved", "rejected", "more_info"}

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
    event_data = {
        "action": action,
        "user_id": user_id,
        "role": body.get("role", "operator"),
        "reason": body.get("reason", ""),
        "question": body.get("question", ""),
    }
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
