"""
Activity: notify_operator — write SignalR notification record to Cosmos DB (T-024)

SignalR push (T-030) will pick up the `notifications` container.
Also updates the incident record with the latest AI result summary.
"""

import logging
import os
from datetime import datetime, timezone

from shared.cosmos_client import get_cosmos_client

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("COSMOS_DATABASE", "sentinel-intelligence")


def notify_operator(input_data: dict) -> dict:
    client = get_cosmos_client()
    db = client.get_database_client(DB_NAME)

    incident_id: str = input_data["incident_id"]
    ai_result: dict = input_data.get("ai_result", {})
    is_escalation: bool = input_data.get("escalation", False)
    target_role: str = input_data.get("role", "operator")
    now_iso = datetime.now(timezone.utc).isoformat()

    notification_type = "escalation" if is_escalation else "approval_required"

    notification = {
        "id": f"notif-{incident_id}-{int(datetime.now(timezone.utc).timestamp())}",
        "incidentId": incident_id,
        "type": notification_type,
        "targetRole": target_role,
        "message": _build_message(incident_id, ai_result, is_escalation),
        "aiAnalysis": ai_result.get("analysis", ""),
        "recommendations": ai_result.get("recommendations", []),
        "confidence": ai_result.get("confidence", 0.0),
        "status": "pending",
        "createdAt": now_iso,
    }

    # Write to notifications container (T-030 SignalR trigger reads this)
    notif_container = db.get_container_client("notifications")
    notif_container.upsert_item(notification)

    # Also log to incident_events
    events = db.get_container_client("incident_events")
    events.upsert_item(
        {
            "id": f"{incident_id}-notified-{target_role}-{int(datetime.now(timezone.utc).timestamp())}",
            "incidentId": incident_id,
            "eventType": notification_type,
            "targetRole": target_role,
            "timestamp": now_iso,
        }
    )

    logger.info(
        "Notification created for incident %s — type=%s role=%s",
        incident_id,
        notification_type,
        target_role,
    )
    return {"notification_id": notification["id"], "type": notification_type}


def _build_message(incident_id: str, ai_result: dict, is_escalation: bool) -> str:
    prefix = "⚠️ ESCALATION" if is_escalation else "🔔 Action Required"
    analysis = ai_result.get("analysis", "AI analysis pending.")
    return (
        f"{prefix} — Incident {incident_id} requires your decision.\n"
        f"Analysis summary: {analysis[:300]}"
    )
