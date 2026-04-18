"""
Activity: finalize_audit — write final audit record and close incident (T-024)

Writes a complete audit trail document to `incident_events` and
transitions the incident to 'closed' or 'rejected'.
"""

import logging
import os
from datetime import datetime, timezone

import azure.durable_functions as df

from shared.cosmos_client import get_cosmos_client
from shared.incident_store import patch_incident_by_id

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("COSMOS_DATABASE", "sentinel-intelligence")

bp = df.Blueprint()


@bp.activity_trigger(input_name="input_data")
def finalize_audit(input_data: dict) -> dict:
    incident_id: str = input_data["incident_id"]
    decision: dict = input_data.get("decision", {})
    exec_result: dict = input_data.get("exec_result") or {}
    now_iso = datetime.now(timezone.utc).isoformat()

    action = decision.get("action", "unknown") if isinstance(decision, dict) else "unknown"
    final_status = "closed" if action == "approved" else "rejected"

    client = get_cosmos_client()
    db = client.get_database_client(DB_NAME)

    # Close the incident
    patch_incident_by_id(
        db,
        incident_id,
        patch_operations=[
            {"op": "set", "path": "/status", "value": final_status},
            {"op": "set", "path": "/closedAt", "value": now_iso},
            {"op": "set", "path": "/updatedAt", "value": now_iso},
            {"op": "set", "path": "/finalDecision", "value": decision},
        ],
    )

    # Write final audit record to incident_events
    events = db.get_container_client("incident_events")
    audit_doc = {
        "id": f"{incident_id}-audit-final",
        "incidentId": incident_id,
        "incident_id": incident_id,
        "eventType": "audit_finalized",
        "action": "audit_finalized",
        "actor": "System",
        "actor_type": "system",
        "finalStatus": final_status,
        "decision": decision,
        "executionResult": exec_result,
        "details": f"Audit finalized. Incident status set to {final_status}.",
        "closedAt": now_iso,
        "timestamp": now_iso,
    }
    events.upsert_item(audit_doc)

    logger.info("Incident %s finalized — status=%s", incident_id, final_status)
    return {"incident_id": incident_id, "final_status": final_status, "closed_at": now_iso}
