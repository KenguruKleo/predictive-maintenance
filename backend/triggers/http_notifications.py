"""
HTTP Triggers — notification feed + unread state (notification MVP)

Endpoints:
  GET   /api/notifications
  GET   /api/notifications/summary
    POST  /api/notifications/read-all
    PATCH /api/notifications/read-all
  POST  /api/incidents/{incident_id}/notifications/read
  PATCH /api/incidents/{incident_id}/notifications/read
"""

import json
import logging
from datetime import datetime, timezone

import azure.functions as func

from shared.cosmos_client import get_container
from utils.auth import AuthError, get_caller_id, get_caller_roles, get_primary_role, require_any_role

logger = logging.getLogger(__name__)

bp = func.Blueprint()

ALL_ROLES = ["Operator", "QAManager", "MaintenanceTech", "Auditor", "ITAdmin"]
ACTIONABLE_NOTIFICATION_STATUSES = {"pending_approval", "escalated"}
INFORMATIONAL_NOTIFICATION_STATUSES = {"awaiting_agents"}
SUPPRESSED_NOTIFICATION_STATUSES = {
    "open",
    "ingested",
    "analyzing",
    "approved",
    "in_progress",
    "executed",
    "completed",
    "rejected",
    "closed",
}

ROLE_TARGETS = {
    "Operator": {"operator"},
    "QAManager": {"qa-manager", "qamanager", "qa_manager"},
    "MaintenanceTech": {"maintenance-tech", "maint-tech", "maintenancetech"},
    "Auditor": {"auditor"},
    "ITAdmin": {"it-admin", "itadmin"},
}


@bp.route(route="notifications", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def list_notifications(req: func.HttpRequest) -> func.HttpResponse:
    """Return a role-filtered notification feed for the current caller."""
    try:
        roles = get_caller_roles(req)
        require_any_role(roles, ALL_ROLES)
    except AuthError as exc:
        return _error(exc.status_code, exc.message)

    primary_role = get_primary_role(roles)
    caller_id = get_caller_id(req)

    try:
        limit = min(50, max(1, int(req.params.get("limit", "20"))))
    except (TypeError, ValueError):
        return _error(400, "Invalid limit parameter")

    status_param = str(req.params.get("status", "unread") or "unread").strip().lower()
    incident_id = str(req.params.get("incident_id", "") or "").strip()
    unread_only = status_param != "all"

    try:
        notifications = _load_visible_notifications(primary_role, caller_id, incident_id=incident_id)
        unread_count = sum(1 for item in notifications if not item["is_read"])
        items = notifications if not unread_only else [item for item in notifications if not item["is_read"]]

        return _json({
            "items": items[:limit],
            "total": len(items),
            "unread_count": unread_count,
        })
    except Exception as exc:  # noqa: BLE001
        logger.exception("list_notifications failed: %s", exc)
        return _error(500, "Internal server error")


@bp.route(route="notifications/summary", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def get_notifications_summary(req: func.HttpRequest) -> func.HttpResponse:
    """Return unread counts plus the incident IDs that should be highlighted in the UI."""
    try:
        roles = get_caller_roles(req)
        require_any_role(roles, ALL_ROLES)
    except AuthError as exc:
        return _error(exc.status_code, exc.message)

    primary_role = get_primary_role(roles)
    caller_id = get_caller_id(req)

    try:
        notifications = _load_visible_notifications(primary_role, caller_id)
        unread_items = [item for item in notifications if not item["is_read"]]

        by_type: dict[str, int] = {}
        unread_incident_ids: list[str] = []
        for item in unread_items:
            item_type = item["type"] or "unknown"
            by_type[item_type] = by_type.get(item_type, 0) + 1
            incident_id = item["incident_id"]
            if incident_id and incident_id not in unread_incident_ids:
                unread_incident_ids.append(incident_id)

        latest_unread_at = unread_items[0]["created_at"] if unread_items else None
        return _json({
            "unread_count": len(unread_items),
            "unread_incident_ids": unread_incident_ids,
            "by_type": by_type,
            "latest_unread_at": latest_unread_at,
        })
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_notifications_summary failed: %s", exc)
        return _error(500, "Internal server error")


@bp.route(route="notifications/read-all", methods=["POST", "PATCH"], auth_level=func.AuthLevel.ANONYMOUS)
def mark_all_notifications_read(req: func.HttpRequest) -> func.HttpResponse:
    """Mark all caller-visible unread notifications as read."""
    try:
        roles = get_caller_roles(req)
        require_any_role(roles, ALL_ROLES)
    except AuthError as exc:
        return _error(exc.status_code, exc.message)

    primary_role = get_primary_role(roles)
    caller_id = get_caller_id(req)
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        container = get_container("notifications")
        docs = list(container.query_items(
            query="SELECT * FROM c",
            parameters=[],
            enable_cross_partition_query=True,
        ))

        updated_docs, updated_ids, updated_incident_ids = _mark_visible_notifications_read(
            docs,
            primary_role,
            caller_id,
            now_iso=now_iso,
        )
        for doc in updated_docs:
            container.upsert_item(doc)

        return _json({
            "marked_read": len(updated_ids),
            "notification_ids": updated_ids,
            "incident_ids": updated_incident_ids,
        })
    except Exception as exc:  # noqa: BLE001
        logger.exception("mark_all_notifications_read failed: %s", exc)
        return _error(500, "Internal server error")


@bp.route(
    route="incidents/{incident_id}/notifications/read",
    methods=["POST", "PATCH"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def mark_incident_notifications_read(req: func.HttpRequest) -> func.HttpResponse:
    """Mark all caller-visible notifications for an incident as read."""
    try:
        roles = get_caller_roles(req)
        require_any_role(roles, ALL_ROLES)
    except AuthError as exc:
        return _error(exc.status_code, exc.message)

    incident_id = str(req.route_params.get("incident_id", "") or "").strip()
    if not incident_id:
        return _error(400, "incident_id is required")

    primary_role = get_primary_role(roles)
    caller_id = get_caller_id(req)
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        container = get_container("notifications")
        docs = list(container.query_items(
            query="SELECT * FROM c WHERE c.incidentId = @incident_id",
            parameters=[{"name": "@incident_id", "value": incident_id}],
            enable_cross_partition_query=True,
        ))

        updated_docs, updated_ids, _updated_incident_ids = _mark_visible_notifications_read(
            docs,
            primary_role,
            caller_id,
            now_iso=now_iso,
        )
        for doc in updated_docs:
            container.upsert_item(doc)

        return _json({
            "incident_id": incident_id,
            "marked_read": len(updated_ids),
            "notification_ids": [item_id for item_id in updated_ids if item_id],
        })
    except Exception as exc:  # noqa: BLE001
        logger.exception("mark_incident_notifications_read failed: %s", exc)
        return _error(500, "Internal server error")


def _load_visible_notifications(
    primary_role: str,
    caller_id: str,
    *,
    incident_id: str = "",
) -> list[dict]:
    notifications_container = get_container("notifications")
    query = "SELECT * FROM c"
    parameters = []

    if incident_id:
        query += " WHERE c.incidentId = @incident_id"
        parameters.append({"name": "@incident_id", "value": incident_id})

    docs = list(notifications_container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True,
    ))

    visible_docs = [doc for doc in docs if _is_visible_to_caller(doc, primary_role, caller_id)]
    incident_map = _load_incident_map(_collect_incident_ids(visible_docs))

    items = []
    for doc in visible_docs:
        incident = incident_map.get(str(doc.get("incidentId") or doc.get("incident_id") or ""))
        normalized = _normalize_notification(doc, incident=incident, caller_id=caller_id)
        if normalized:
            items.append(normalized)

    items.sort(key=lambda item: item["created_at"] or "", reverse=True)
    return _dedupe_notifications_by_incident(items)


def _normalize_notification(
    doc: dict,
    *,
    incident: dict | None = None,
    caller_id: str = "",
) -> dict | None:
    incident_id = str(doc.get("incidentId") or doc.get("incident_id") or "")
    current_status = _get_current_incident_status(doc, incident)

    if not _should_surface_notification(doc, incident, current_status, caller_id):
        return None

    title = str(
        (incident or {}).get("title")
        or doc.get("title")
        or doc.get("incidentTitle")
        or ""
    )

    return {
        "id": str(doc.get("id") or ""),
        "incident_id": incident_id,
        "type": str(doc.get("type") or ""),
        "message": _build_notification_message(current_status, doc=doc),
        "target_role": str(doc.get("targetRole") or doc.get("target_role") or ""),
        "assigned_to": str(doc.get("assignedTo") or doc.get("assigned_to") or ""),
        "equipment_id": str(
            (incident or {}).get("equipment_id")
            or (incident or {}).get("equipmentId")
            or doc.get("equipmentId")
            or doc.get("equipment_id")
            or ""
        ),
        "title": title,
        "incident_status": current_status,
        "status_label": _format_status_label(current_status),
        "presentation_kind": _get_notification_presentation_kind(current_status),
        "confidence": float(doc.get("confidence") or 0.0),
        "risk_level": str(doc.get("riskLevel") or doc.get("risk_level") or ""),
        "created_at": str(doc.get("createdAt") or doc.get("created_at") or ""),
        "updated_at": str(doc.get("updatedAt") or doc.get("updated_at") or ""),
        "is_read": _notification_is_read(doc),
        "read_at": doc.get("readAt") or doc.get("read_at"),
        "read_by": doc.get("readBy") or doc.get("read_by"),
    }


def _notification_is_read(doc: dict) -> bool:
    if doc.get("isRead") is True:
        return True
    read_at = doc.get("readAt") or doc.get("read_at")
    if isinstance(read_at, str) and read_at.strip():
        return True
    status = str(doc.get("status") or "").strip().lower()
    return status == "read"


def _load_incident_map(incident_ids: list[str]) -> dict[str, dict]:
    if not incident_ids:
        return {}

    incidents_container = get_container("incidents")
    incident_map: dict[str, dict] = {}
    for incident_id in incident_ids:
        rows = list(incidents_container.query_items(
            query="SELECT * FROM c WHERE c.id = @incident_id",
            parameters=[{"name": "@incident_id", "value": incident_id}],
            enable_cross_partition_query=True,
        ))
        if rows:
            incident_map[incident_id] = rows[0]

    return incident_map


def _collect_incident_ids(docs: list[dict]) -> list[str]:
    incident_ids: list[str] = []
    for doc in docs:
        incident_id = str(doc.get("incidentId") or doc.get("incident_id") or "")
        if incident_id and incident_id not in incident_ids:
            incident_ids.append(incident_id)
    return incident_ids


def _get_current_incident_status(doc: dict, incident: dict | None) -> str:
    status = (
        (incident or {}).get("status")
        or doc.get("incidentStatus")
        or doc.get("incident_status")
        or _infer_incident_status(doc)
    )
    return _normalize_status_value(status)


def _infer_incident_status(doc: dict) -> str:
    notification_type = str(doc.get("type") or "").strip().lower()
    if notification_type == "escalation":
        return "escalated"
    if notification_type == "approval_required":
        return "pending_approval"
    return ""


def _should_surface_notification(
    doc: dict,
    incident: dict | None,
    current_status: str,
    caller_id: str,
) -> bool:
    if current_status in SUPPRESSED_NOTIFICATION_STATUSES:
        return False

    normalized_target_role = _normalize_role_value(doc.get("targetRole") or doc.get("target_role"))
    expected_target_roles = {
        "pending_approval": {"operator"},
        "escalated": ROLE_TARGETS["QAManager"],
    }.get(current_status)

    if expected_target_roles and normalized_target_role and normalized_target_role not in expected_target_roles:
        return False

    if current_status == "awaiting_agents":
        last_decision = (incident or {}).get("lastDecision") or {}
        last_action = str(last_decision.get("action") or "").strip().lower()
        last_actor = str(last_decision.get("user_id") or last_decision.get("userId") or "").strip()
        if last_action == "more_info" and caller_id and last_actor == caller_id:
            return False

    return True


def _get_notification_presentation_kind(current_status: str) -> str:
    if current_status in ACTIONABLE_NOTIFICATION_STATUSES:
        return "actionable"
    return "informational"


def _build_notification_message(current_status: str, *, doc: dict) -> str:
    if current_status == "pending_approval":
        return "Decision required: review the recommendation and record your decision."
    if current_status == "escalated":
        return "Escalated for QA manager review and decision."
    if current_status == "awaiting_agents":
        return "Additional analysis was requested; agents are preparing an updated recommendation."
    if current_status == "approved":
        return "Recommendation approved; execution is starting."
    if current_status == "in_progress":
        return "Approved actions are currently in progress."
    if current_status == "executed":
        return "Approved actions have been executed."
    if current_status == "completed":
        return "Incident workflow completed."
    if current_status == "rejected":
        return "Recommendation rejected; incident closed."
    if current_status == "closed":
        return "Incident closed; audit finalized."

    fallback_message = str(doc.get("message") or "").strip()
    if fallback_message and "action required" not in fallback_message.lower():
        return fallback_message
    return "Incident status updated; review the latest activity."


def _format_status_label(current_status: str) -> str:
    if not current_status:
        return "Unknown"
    return current_status.replace("_", " ").title()


def _normalize_status_value(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _dedupe_notifications_by_incident(items: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen_incident_ids: set[str] = set()

    for item in items:
        incident_id = str(item.get("incident_id") or item.get("id") or "")
        if incident_id in seen_incident_ids:
            continue
        seen_incident_ids.add(incident_id)
        deduped.append(item)

    return deduped


def _mark_visible_notifications_read(
    docs: list[dict],
    primary_role: str,
    caller_id: str,
    *,
    now_iso: str,
) -> tuple[list[dict], list[str], list[str]]:
    updated_docs: list[dict] = []
    updated_ids: list[str] = []
    updated_incident_ids: list[str] = []

    for doc in docs:
        if not _is_visible_to_caller(doc, primary_role, caller_id):
            continue
        if _notification_is_read(doc):
            continue

        doc["isRead"] = True
        doc["readAt"] = now_iso
        doc["readBy"] = caller_id or primary_role
        doc["updatedAt"] = now_iso
        if str(doc.get("status") or "").strip().lower() == "unread":
            doc["status"] = "read"

        updated_docs.append(doc)

        notification_id = str(doc.get("id") or "")
        if notification_id:
            updated_ids.append(notification_id)

        incident_id = str(doc.get("incidentId") or doc.get("incident_id") or "")
        if incident_id and incident_id not in updated_incident_ids:
            updated_incident_ids.append(incident_id)

    return updated_docs, updated_ids, updated_incident_ids


def _is_visible_to_caller(doc: dict, primary_role: str, caller_id: str) -> bool:
    if primary_role == "ITAdmin":
        return True

    target_role = _normalize_role_value(doc.get("targetRole") or doc.get("target_role"))
    if target_role not in ROLE_TARGETS.get(primary_role, set()):
        return False

    if primary_role == "Operator":
        assigned_to = str(doc.get("assignedTo") or doc.get("assigned_to") or "").strip()
        return not assigned_to or not caller_id or assigned_to == caller_id

    return True


def _normalize_role_value(value: object) -> str:
    return str(value or "").strip().lower().replace("_", "-")


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