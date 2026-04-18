"""
HTTP Trigger — GET /api/negotiate  (T-030)

Returns Azure SignalR Service connection info (hub URL + access token) for the React client.
The client uses this to establish a persistent SignalR connection to the 'deviationHub'.

Hub contract:
  Hub:    deviationHub
  Events: incident_created, incident_pending_approval, incident_status_changed,
          agent_step_completed, incident_escalated, chat_response

Connection string app setting: AzureSignalRConnectionString
"""

import logging

import azure.functions as func

logger = logging.getLogger(__name__)

bp = func.Blueprint()


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
