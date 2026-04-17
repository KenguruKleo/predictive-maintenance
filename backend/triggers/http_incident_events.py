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
    auth_level=func.AuthLevel.FUNCTION,
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

        # If no events found, check incident exists at all
        if not items:
            inc_container = get_container("incidents")
            exists = list(inc_container.query_items(
                query="SELECT VALUE COUNT(1) FROM c WHERE c.id = @id",
                parameters=[{"name": "@id", "value": incident_id}],
                enable_cross_partition_query=True,
            ))
            if not exists or exists[0] == 0:
                return _error(404, f"Incident '{incident_id}' not found")

        return _json({"incident_id": incident_id, "events": items, "total": len(items)})

    except Exception as exc:  # noqa: BLE001
        logger.exception("get_incident_events %s failed: %s", incident_id, exc)
        return _error(500, "Internal server error")


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
