"""
HTTP Trigger — GET /api/incidents/{id}/events (T-031)

Returns the chronological audit event timeline for an incident.
Events are stored in the 'audit_events' Cosmos container with partition key = incident_id.
"""

import json
import logging

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
        container = get_container("audit_events")
        items = list(container.query_items(
            query=(
                "SELECT * FROM c WHERE c.incident_id = @incident_id "
                "ORDER BY c.timestamp ASC"
            ),
            parameters=[{"name": "@incident_id", "value": incident_id}],
            enable_cross_partition_query=True,
        ))
    except Exception as exc:  # noqa: BLE001
        # audit_events container may not exist yet — return empty timeline
        logger.warning("audit_events query failed for %s (container may not exist yet): %s", incident_id, exc)
        items = []

    return _json({"incident_id": incident_id, "events": items, "total": len(items)})


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
