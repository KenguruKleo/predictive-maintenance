"""
Activity: close_incident — set incident status to rejected (T-024)

Called when operator rejects the AI recommendation or the more_info
rounds are exhausted without an approval decision.
"""

import logging
import os
from datetime import datetime, timezone

import azure.durable_functions as df

from shared.cosmos_client import get_cosmos_client

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("COSMOS_DATABASE", "sentinel-intelligence")

bp = df.Blueprint()


@bp.activity_trigger(input_name="input_data")
def close_incident(input_data: dict) -> dict:
    incident_id: str = input_data["incident_id"]
    rejection_reason: str = input_data.get("rejection_reason", "Rejected by operator")
    now_iso = datetime.now(timezone.utc).isoformat()

    client = get_cosmos_client()
    db = client.get_database_client(DB_NAME)
    incidents = db.get_container_client("incidents")

    incidents.patch_item(
        item=incident_id,
        partition_key=incident_id,
        patch_operations=[
            {"op": "set", "path": "/status", "value": "rejected"},
            {"op": "set", "path": "/closedAt", "value": now_iso},
            {"op": "set", "path": "/updatedAt", "value": now_iso},
            {"op": "set", "path": "/rejectionReason", "value": rejection_reason},
        ],
    )

    # Log event
    events = db.get_container_client("incident_events")
    events.upsert_item(
        {
            "id": f"{incident_id}-closed-rejected-{int(datetime.now(timezone.utc).timestamp())}",
            "incidentId": incident_id,
            "eventType": "incident_rejected",
            "rejectionReason": rejection_reason,
            "timestamp": now_iso,
        }
    )

    logger.info("Incident %s closed as rejected. Reason: %s", incident_id, rejection_reason)
    return {"incident_id": incident_id, "status": "rejected", "closed_at": now_iso}
