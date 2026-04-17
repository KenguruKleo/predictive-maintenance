"""
Activity: create_incident — Cosmos DB write (T-024)

Input dict:
  - incident_id: str
  - alert_payload: dict       (on first create)
  - status: str               ("open" | "rejected")
  - rejection_reason: str     (optional)

Returns incident_id (str) so orchestrator can track it through replays.
"""

import logging
import os
from datetime import datetime, timezone

from azure.cosmos.exceptions import CosmosResourceExistsError

from shared.cosmos_client import get_cosmos_client

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("COSMOS_DATABASE", "sentinel-intelligence")
INCIDENTS_CONTAINER = "incidents"
EVENTS_CONTAINER = "incident_events"


def create_incident(input_data: dict) -> str:
    client = get_cosmos_client()
    db = client.get_database_client(DB_NAME)
    incidents = db.get_container_client(INCIDENTS_CONTAINER)
    events = db.get_container_client(EVENTS_CONTAINER)

    incident_id: str = input_data["incident_id"]
    status: str = input_data.get("status", "open")
    now_iso = datetime.now(timezone.utc).isoformat()

    if status == "open" and "alert_payload" in input_data:
        # First-time creation
        alert = input_data["alert_payload"]
        doc = {
            "id": incident_id,
            "incidentId": incident_id,
            "equipmentId": alert.get("equipment_id", ""),
            "alertType": alert.get("alert_type", ""),
            "severity": alert.get("severity", ""),
            "description": alert.get("description", ""),
            "status": "open",
            "createdAt": now_iso,
            "updatedAt": now_iso,
            "alert": alert,
        }
        try:
            incidents.create_item(doc, enable_automatic_id_generation=False)
            logger.info("Created incident %s", incident_id)
        except CosmosResourceExistsError:
            logger.info("Incident %s already exists — idempotent skip", incident_id)
    else:
        # Status update (rejected / re-open)
        patch_ops = [
            {"op": "set", "path": "/status", "value": status},
            {"op": "set", "path": "/updatedAt", "value": now_iso},
        ]
        if "rejection_reason" in input_data:
            patch_ops.append(
                {"op": "set", "path": "/rejectionReason", "value": input_data["rejection_reason"]}
            )
        incidents.patch_item(
            item=incident_id,
            partition_key=incident_id,
            patch_operations=patch_ops,
        )
        logger.info("Updated incident %s → status=%s", incident_id, status)

    # Append event log
    event_doc = {
        "id": f"{incident_id}-{status}-{int(datetime.now(timezone.utc).timestamp())}",
        "incidentId": incident_id,
        "eventType": f"incident_{status}",
        "payload": input_data,
        "timestamp": now_iso,
    }
    events.upsert_item(event_doc)

    return incident_id
