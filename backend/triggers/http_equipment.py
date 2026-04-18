"""
HTTP Trigger — GET /api/equipment/{id} (T-031)

Returns equipment master data from the 'equipment' Cosmos container.
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
    route="equipment/{equipment_id}",
    methods=["GET"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def get_equipment(req: func.HttpRequest) -> func.HttpResponse:
    """Return equipment master data by ID."""
    try:
        roles = get_caller_roles(req)
        require_any_role(roles, ALL_ROLES)
    except AuthError as exc:
        return _error(exc.status_code, exc.message)

    equipment_id: str = req.route_params.get("equipment_id", "").strip()
    if not equipment_id:
        return _error(400, "equipment_id is required")

    try:
        container = get_container("equipment")
        items = list(container.query_items(
            query="SELECT * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": equipment_id}],
            enable_cross_partition_query=True,
        ))

        if not items:
            return _error(404, f"Equipment '{equipment_id}' not found")

        return _json(items[0])

    except Exception as exc:  # noqa: BLE001
        logger.exception("get_equipment %s failed: %s", equipment_id, exc)
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
