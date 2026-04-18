"""
HTTP Trigger — GET /api/batches/current/{equipment_id} (T-031)

Returns the most recent in-progress or latest batch for a given equipment.
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
    route="batches/current/{equipment_id}",
    methods=["GET"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def get_current_batch(req: func.HttpRequest) -> func.HttpResponse:
    """Return the active (in_progress) batch for a piece of equipment."""
    try:
        roles = get_caller_roles(req)
        require_any_role(roles, ALL_ROLES)
    except AuthError as exc:
        return _error(exc.status_code, exc.message)

    equipment_id: str = req.route_params.get("equipment_id", "").strip()
    if not equipment_id:
        return _error(400, "equipment_id is required")

    try:
        container = get_container("batches")

        # Prefer in_progress batch; fall back to most recent
        items = list(container.query_items(
            query=(
                "SELECT * FROM c WHERE c.equipment_id = @equipment_id "
                "AND c.status = 'in_progress' "
                "ORDER BY c.start_time DESC OFFSET 0 LIMIT 1"
            ),
            parameters=[{"name": "@equipment_id", "value": equipment_id}],
            enable_cross_partition_query=True,
        ))

        if not items:
            # Fall back to any most-recent batch
            items = list(container.query_items(
                query=(
                    "SELECT * FROM c WHERE c.equipment_id = @equipment_id "
                    "ORDER BY c.start_time DESC OFFSET 0 LIMIT 1"
                ),
                parameters=[{"name": "@equipment_id", "value": equipment_id}],
                enable_cross_partition_query=True,
            ))

        if not items:
            return _error(404, f"No batch found for equipment '{equipment_id}'")

        return _json(items[0])

    except Exception as exc:  # noqa: BLE001
        logger.exception("get_current_batch %s failed: %s", equipment_id, exc)
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
