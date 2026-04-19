"""
Activity: notify_operator — create operator approval task and notification (T-024)

Creates the pending human-in-the-loop task, updates the incident state, and
pushes a SignalR notification to the React UI.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

import azure.durable_functions as df

from shared.cosmos_client import get_cosmos_client
from shared.incident_store import patch_incident_by_id
from shared.signalr_client import notify_signalr_sync

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("COSMOS_DATABASE", "sentinel-intelligence")

bp = df.Blueprint()


@bp.activity_trigger(input_name="input_data")
def notify_operator(input_data: dict) -> dict:
    client = get_cosmos_client()
    db = client.get_database_client(DB_NAME)

    incident_id: str = input_data["incident_id"]
    ai_result: dict = input_data.get("ai_result", {})
    is_escalation: bool = input_data.get("escalation", False)
    target_role: str = input_data.get("role", "operator")
    equipment_id: str = input_data.get("equipment_id", "")
    batch_id: str = input_data.get("batch_id", "")
    product: str = input_data.get("product", "")
    production_stage: str = input_data.get("production_stage", "")
    assigned_to: str = input_data.get("assigned_to", "ivan.petrenko")
    response_round: int = int(input_data.get("response_round", 0) or 0)
    now_iso = datetime.now(timezone.utc).isoformat()
    due_at_iso = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

    notification_type = "escalation" if is_escalation else "approval_required"
    incident_status = "escalated" if is_escalation else "pending_approval"
    current_step = "awaiting_qa_manager_decision" if is_escalation else "awaiting_operator_decision"

    approval_task = {
        "id": f"approval-{incident_id}",
        "incidentId": incident_id,
        "durableInstanceId": f"durable-{incident_id}",
        "type": notification_type,
        "status": "pending",
        "targetRole": target_role,
        "assignedTo": assigned_to if target_role == "operator" else target_role,
        "aiAnalysis": ai_result,
        "confidence": ai_result.get("confidence", 0.0),
        "riskLevel": ai_result.get("risk_level", "unknown"),
        "createdAt": now_iso,
        "updatedAt": now_iso,
        "dueAt": due_at_iso,
    }
    if is_escalation:
        approval_task["escalatedAt"] = now_iso

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

    # Create/update the active HITL task for the React approval UX.
    approval_tasks = db.get_container_client("approval-tasks")
    try:
        approval_tasks.upsert_item(approval_task)
    except Exception as e:
        logger.error("Failed to upsert approval task for incident %s: %s", incident_id, e, exc_info=True)
        raise

    # Move incident from open/queued into the human decision state.
    try:
        patch_operations = [
            {"op": "set", "path": "/status", "value": incident_status},
            {"op": "set", "path": "/ai_analysis", "value": ai_result},
            {"op": "set", "path": "/title", "value": ai_result.get("title") or _fallback_title(ai_result)},
            {"op": "set", "path": "/workflow_state", "value": {
                "durable_instance_id": f"durable-{incident_id}",
                "current_step": current_step,
                "assigned_to": assigned_to,
                "target_role": target_role,
                "approval_task_id": approval_task["id"],
                "escalation_deadline": due_at_iso,
            }},
            {"op": "set", "path": "/updatedAt", "value": now_iso},
            {"op": "set", "path": "/updated_at", "value": now_iso},
        ]
        if batch_id:
            patch_operations.append({"op": "set", "path": "/batch_id", "value": batch_id})
        if product:
            patch_operations.append({"op": "set", "path": "/product", "value": product})
        if production_stage:
            patch_operations.append({"op": "set", "path": "/production_stage", "value": production_stage})

        patch_incident_by_id(
            db,
            incident_id,
            patch_operations,
        )
    except Exception as e:
        logger.error("Failed to update incident %s to %s: %s", incident_id, incident_status, e, exc_info=True)
        raise

    # Write to notifications container (T-030 SignalR trigger reads this)
    notif_container = db.get_container_client("notifications")
    try:
        notif_container.upsert_item(notification)
    except Exception as e:
        logger.error("Failed to upsert notification for incident %s: %s", incident_id, e, exc_info=True)
        raise

    # Also log to incident_events
    events = db.get_container_client("incident_events")
    try:
        if ai_result and not is_escalation:
            events.upsert_item(
                {
                    "id": f"{incident_id}-agent-response-{response_round}-{int(datetime.now(timezone.utc).timestamp())}",
                    "incidentId": incident_id,
                    "incident_id": incident_id,
                    "eventType": "agent_response",
                    "action": "agent_response",
                    "actor": "AI Agent",
                    "actor_type": "agent",
                    "round": response_round,
                    "messageKind": (
                        "initial_recommendation"
                        if response_round == 0
                        else "follow_up_response"
                    ),
                    "details": _build_transcript_message(ai_result),
                    "timestamp": now_iso,
                }
            )

        events.upsert_item(
            {
                "id": f"{incident_id}-notified-{target_role}-{int(datetime.now(timezone.utc).timestamp())}",
                "incidentId": incident_id,
                "incident_id": incident_id,
                "eventType": notification_type,
                "action": "escalated" if is_escalation else "approval_requested",
                "actor": "System",
                "actor_type": "system",
                "targetRole": target_role,
                "approvalTaskId": approval_task["id"],
                "incidentStatus": incident_status,
                "details": (
                    f"Incident escalated to {target_role}."
                    if is_escalation
                    else f"Approval requested from {target_role}."
                ),
                "timestamp": now_iso,
            }
        )
    except Exception as e:
        logger.error("Failed to upsert incident_event for incident %s: %s", incident_id, e, exc_info=True)
        raise

    logger.info(
        "Notification created for incident %s — type=%s role=%s",
        incident_id,
        notification_type,
        target_role,
    )

    # Push real-time notification via SignalR (T-030)
    signalr_event = "incident_escalated" if is_escalation else "incident_pending_approval"
    signalr_payload = {
        "incident_id": incident_id,
        "equipment_id": equipment_id,
        "type": notification_type,
        "risk_level": ai_result.get("risk_level", "unknown"),
        "created_at": now_iso,
    }
    notify_signalr_sync(
        hub="deviationHub",
        event=signalr_event,
        payload=signalr_payload,
        target_role=target_role,
        incident_id=incident_id,
    )

    return {
        "notification_id": notification["id"],
        "approval_task_id": approval_task["id"],
        "type": notification_type,
        "incident_status": incident_status,
    }


def _build_message(incident_id: str, ai_result: dict, is_escalation: bool) -> str:
    prefix = "Escalation" if is_escalation else "Action required"
    analysis = ai_result.get("analysis", "AI analysis pending.")
    return (
        f"{prefix} — Incident {incident_id} requires your decision.\n"
        f"Analysis summary: {analysis[:300]}"
    )


def _fallback_title(ai_result: dict) -> str:
    classification = str(ai_result.get("classification") or ai_result.get("deviation_classification") or "").strip()
    if classification:
        return classification.replace("_", " ").title()
    return "Deviation Review Required"


def _build_transcript_message(ai_result: dict) -> str:
    operator_dialogue = str(ai_result.get("operator_dialogue") or "").strip()
    if operator_dialogue:
        return operator_dialogue[:800]

    recommendation = str(ai_result.get("recommendation") or "").strip()
    analysis = str(ai_result.get("analysis") or "").strip()

    if recommendation and analysis and analysis != recommendation:
        return f"{recommendation}\n\n{analysis[:500]}".strip()

    message = recommendation or analysis or "AI agent updated the recommendation."
    return message[:800]
