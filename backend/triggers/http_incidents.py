"""
HTTP Triggers — GET /api/incidents, GET /api/incidents/{id} (T-031)

Role-based filtering:
  Operator        → only incidents assigned to them
  MaintenanceTech → only approved/closed incidents
  Auditor         → all (read-only)
  QAManager       → all
  ITAdmin         → all
"""

import json
import logging

import azure.functions as func

from shared.cosmos_client import get_container
from utils.auth import AuthError, get_caller_roles, get_primary_role, require_any_role

logger = logging.getLogger(__name__)

bp = func.Blueprint()

ALL_ROLES = ["Operator", "QAManager", "MaintenanceTech", "Auditor", "ITAdmin"]


# ---------------------------------------------------------------------------
# GET /api/incidents
# ---------------------------------------------------------------------------

@bp.route(route="incidents", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def list_incidents(req: func.HttpRequest) -> func.HttpResponse:
    """List incidents with optional role-based filtering and pagination."""
    try:
        roles = get_caller_roles(req)
        require_any_role(roles, ALL_ROLES)
    except AuthError as exc:
        return _error(exc.status_code, exc.message)

    try:
        page = max(1, int(req.params.get("page", "1")))
        page_size = min(100, max(1, int(req.params.get("page_size", "20"))))
        status_filter = req.params.get("status", "")
        severity_filter = req.params.get("severity", "")
    except (ValueError, TypeError):
        return _error(400, "Invalid pagination parameters")

    try:
        container = get_container("incidents")
        query, params = _build_query(roles, status_filter, severity_filter, page, page_size)
        items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

        # Count query (without pagination)
        count_query, count_params = _build_count_query(roles, status_filter, severity_filter)
        count_result = list(container.query_items(query=count_query, parameters=count_params, enable_cross_partition_query=True))
        total = count_result[0] if count_result else len(items)

        # Slim down response for list view
        slim = [_slim_incident(i) for i in items]

        return _json({"items": slim, "total": total, "page": page, "page_size": page_size})

    except Exception as exc:  # noqa: BLE001
        logger.exception("list_incidents failed: %s", exc)
        return _error(500, "Internal server error")


# ---------------------------------------------------------------------------
# GET /api/incidents/{id}
# ---------------------------------------------------------------------------

@bp.route(route="incidents/{incident_id}", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def get_incident(req: func.HttpRequest) -> func.HttpResponse:
    """Get full incident detail including AI analysis."""
    try:
        roles = get_caller_roles(req)
        require_any_role(roles, ALL_ROLES)
    except AuthError as exc:
        return _error(exc.status_code, exc.message)

    incident_id: str = req.route_params.get("incident_id", "").strip()
    if not incident_id:
        return _error(400, "incident_id is required")

    try:
        container = get_container("incidents")
        items = list(container.query_items(
            query="SELECT * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": incident_id}],
            enable_cross_partition_query=True,
        ))

        if not items:
            return _error(404, f"Incident '{incident_id}' not found")

        incident = items[0]

        # Enforce role access: operator can only see their own incidents
        primary_role = get_primary_role(roles)
        if primary_role == "Operator":
            assigned = incident.get("workflow_state", {}).get("assigned_to", "")
            caller_id = _get_caller_id(req)
            if caller_id and assigned and assigned != caller_id:
                return _error(403, "Access denied to this incident")

        return _json(incident)

    except Exception as exc:  # noqa: BLE001
        logger.exception("get_incident %s failed: %s", incident_id, exc)
        return _error(500, "Internal server error")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_query(roles, status_filter, severity_filter, page, page_size) -> tuple[str, list]:
    where_clauses = ["1=1"]
    params = []

    primary_role = get_primary_role(roles)
    if primary_role == "Operator":
        where_clauses.append("c.workflow_state.assigned_to = @caller_id")
        params.append({"name": "@caller_id", "value": _DEMO_USER_ID})
    elif primary_role == "MaintenanceTech":
        where_clauses.append("c.status IN ('approved', 'closed', 'executed', 'completed')")

    if status_filter:
        where_clauses.append("c.status = @status")
        params.append({"name": "@status", "value": status_filter})

    if severity_filter:
        where_clauses.append("c.severity = @severity")
        params.append({"name": "@severity", "value": severity_filter})

    offset = (page - 1) * page_size
    where = " AND ".join(where_clauses)
    query = (
        f"SELECT * FROM c WHERE {where} "
        f"ORDER BY c.reported_at DESC OFFSET {offset} LIMIT {page_size}"
    )
    return query, params


def _build_count_query(roles, status_filter, severity_filter) -> tuple[str, list]:
    where_clauses = ["1=1"]
    params = []

    primary_role = get_primary_role(roles)
    if primary_role == "Operator":
        where_clauses.append("c.workflow_state.assigned_to = @caller_id")
        params.append({"name": "@caller_id", "value": _DEMO_USER_ID})
    elif primary_role == "MaintenanceTech":
        where_clauses.append("c.status IN ('approved', 'closed', 'executed', 'completed')")

    if status_filter:
        where_clauses.append("c.status = @status")
        params.append({"name": "@status", "value": status_filter})
    if severity_filter:
        where_clauses.append("c.severity = @severity")
        params.append({"name": "@severity", "value": severity_filter})

    where = " AND ".join(where_clauses)
    return f"SELECT VALUE COUNT(1) FROM c WHERE {where}", params


def _slim_incident(doc: dict) -> dict:
    """Return a trimmed version of an incident for the list view."""
    ai = doc.get("ai_analysis", {})
    wf = doc.get("workflow_state", {})
    return {
        "id": doc.get("id"),
        "equipment_id": doc.get("equipment_id"),
        "title": doc.get("title"),
        "severity": doc.get("severity"),
        "status": doc.get("status"),
        "reported_at": doc.get("reported_at"),
        "reported_by": doc.get("reported_by"),
        "risk_level": ai.get("risk_level"),
        "confidence": ai.get("confidence"),
        "assigned_to": wf.get("assigned_to"),
        "current_step": wf.get("current_step"),
    }


def _get_caller_id(req: func.HttpRequest) -> str:
    """Extract user ID from mock header (local dev) or leave empty for prod."""
    return req.headers.get("X-Mock-User-Id", "")


# Fallback demo user ID for operator filter when running without auth
_DEMO_USER_ID = "ivan.petrenko"


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
