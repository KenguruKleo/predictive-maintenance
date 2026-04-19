"""HTTP Trigger — GET /api/incidents/{id}/agent-telemetry (T-043)."""

from __future__ import annotations

import json
import logging

import azure.functions as func

from utils.auth import AuthError, get_caller_roles, require_any_role

logger = logging.getLogger(__name__)

bp = func.Blueprint()

ADMIN_ROLES = ["QAManager", "ITAdmin", "Auditor"]


@bp.route(
    route="incidents/{incident_id}/agent-telemetry",
    methods=["GET"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def get_incident_agent_telemetry(req: func.HttpRequest) -> func.HttpResponse:
    """Return backend-visible App Insights telemetry for a single incident."""
    try:
        roles = get_caller_roles(req)
        require_any_role(roles, ADMIN_ROLES)
    except AuthError as exc:
        return _error(exc.status_code, exc.message)

    try:
        from shared.agent_telemetry import (
            TelemetryConfigError,
            query_incident_agent_telemetry,
            validate_agent_name,
            validate_incident_id,
            validate_status,
        )
    except ModuleNotFoundError as exc:
        logger.warning("agent telemetry dependencies unavailable: %s", exc)
        return _error(503, "Agent telemetry endpoint is unavailable in this local environment")

    try:
        incident_id = validate_incident_id(req.route_params.get("incident_id", ""))
        agent_name = validate_agent_name(req.params.get("agent_name"))
        status = validate_status(req.params.get("status"))
        round_number = _parse_round(req.params.get("round"))
    except ValueError as exc:
        return _error(400, str(exc))

    try:
        payload = query_incident_agent_telemetry(
            incident_id,
            agent_name=agent_name,
            status=status,
            round_number=round_number,
        )
        return _json(payload)
    except TelemetryConfigError as exc:
        logger.warning("agent telemetry config error for %s: %s", incident_id, exc)
        return _error(500, str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("agent telemetry query failed for %s: %s", incident_id, exc)
        return _error(500, "Internal server error")


def _parse_round(raw_value: str | None) -> int | None:
    if raw_value is None or not str(raw_value).strip():
        return None
    try:
        round_number = int(raw_value)
    except ValueError as exc:
        raise ValueError("round must be an integer") from exc
    if round_number < 0:
        raise ValueError("round must be >= 0")
    return round_number


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