"""SignalR negotiate and connection registration endpoints."""

import json
import logging

import azure.functions as func

from shared.signalr_client import add_connection_to_group_sync
from utils.auth import AuthError, get_caller_roles, require_any_role

logger = logging.getLogger(__name__)

bp = func.Blueprint()
ALL_ROLES = ["Operator", "QAManager", "MaintenanceTech", "Auditor", "ITAdmin"]
ROLE_GROUPS = {
        "Operator": "operator",
        "QAManager": "qa-manager",
        "MaintenanceTech": "maintenance-tech",
        "Auditor": "auditor",
        "ITAdmin": "it-admin",
}


@bp.route(
    route="negotiate",
    methods=["GET", "POST"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
@bp.generic_input_binding(
    arg_name="connection_info",
    type="signalRConnectionInfo",
    hub_name="deviationHub",
    connection="AzureSignalRConnectionString",
)
def negotiate(req: func.HttpRequest, connection_info) -> func.HttpResponse:
    """Return SignalR connection info for the React client hub connection."""
    # connection_info is a JSON string: {"url": "...", "accessToken": "..."}
    body = (
        connection_info
        if isinstance(connection_info, (bytes, bytearray))
        else str(connection_info).encode()
    )
    return func.HttpResponse(
        body,
        mimetype="application/json",
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
    )


@bp.route(
    route="signalr/register",
    methods=["POST"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def register_signalr_connection(req: func.HttpRequest) -> func.HttpResponse:
    """Attach a SignalR connection to the caller's role groups."""
    try:
        roles = get_caller_roles(req)
        require_any_role(roles, ALL_ROLES)
    except AuthError as exc:
        return _error(exc.status_code, exc.message)

    try:
        body = req.get_json()
    except ValueError:
        return _error(400, "Request body must be valid JSON")

    connection_id = str(body.get("connection_id") or body.get("connectionId") or "").strip()
    if not connection_id:
        return _error(400, "connection_id is required")

    requested_incident_ids = body.get("incident_ids") or body.get("incidentIds") or []
    if isinstance(requested_incident_ids, str):
        requested_incident_ids = [requested_incident_ids]

    group_names: list[str] = []
    for role in roles:
        group_suffix = ROLE_GROUPS.get(str(role))
        if not group_suffix:
            continue
        group_name = f"role:{group_suffix}"
        if group_name not in group_names:
            group_names.append(group_name)

    for incident_id in requested_incident_ids:
        normalized_incident_id = str(incident_id or "").strip()
        if not normalized_incident_id:
            continue
        group_name = f"incident:{normalized_incident_id}"
        if group_name not in group_names:
            group_names.append(group_name)

    registered_groups: list[str] = []
    failed_groups: list[str] = []
    for group_name in group_names:
        if add_connection_to_group_sync(connection_id, group_name):
            registered_groups.append(group_name)
        else:
            failed_groups.append(group_name)

    return _json(
        {
            "connection_id": connection_id,
            "registered_groups": registered_groups,
            "failed_groups": failed_groups,
        },
        status_code=200 if not failed_groups else 207,
    )


def _json(data: dict, *, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps(data),
        status_code=status_code,
        mimetype="application/json",
    )


def _error(status_code: int, message: str) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps({"error": message}),
        status_code=status_code,
        mimetype="application/json",
    )
