"""
HTTP Triggers — GET/PUT /api/templates (T-031)

Routes:
  GET  /api/templates            → list all templates   (ITAdmin only)
  GET  /api/templates/{id}       → get single template  (ITAdmin only)
  PUT  /api/templates/{id}       → update template      (ITAdmin only)
"""

import json
import logging
from datetime import datetime, timezone

import azure.functions as func

from shared.cosmos_client import get_container
from utils.auth import AuthError, get_caller_roles, require_any_role
from utils.validation import sanitize_string_fields

logger = logging.getLogger(__name__)

bp = func.Blueprint()

ADMIN_ROLES = ["ITAdmin"]


# ---------------------------------------------------------------------------
# GET /api/templates
# ---------------------------------------------------------------------------

@bp.route(route="templates", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def list_templates(req: func.HttpRequest) -> func.HttpResponse:
    """List all document templates."""
    try:
        roles = get_caller_roles(req)
        require_any_role(roles, ADMIN_ROLES)
    except AuthError as exc:
        return _error(exc.status_code, exc.message)

    try:
        container = get_container("templates")
        items = list(container.query_items(
            query="SELECT * FROM c ORDER BY c.updated_at DESC",
            enable_cross_partition_query=True,
        ))
        return _json({"items": items, "total": len(items)})

    except Exception as exc:  # noqa: BLE001
        logger.exception("list_templates failed: %s", exc)
        return _error(500, "Internal server error")


# ---------------------------------------------------------------------------
# GET /api/templates/{id}
# ---------------------------------------------------------------------------

@bp.route(route="templates/{template_id}", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def get_template(req: func.HttpRequest) -> func.HttpResponse:
    """Get a single template by ID."""
    try:
        roles = get_caller_roles(req)
        require_any_role(roles, ADMIN_ROLES)
    except AuthError as exc:
        return _error(exc.status_code, exc.message)

    template_id: str = req.route_params.get("template_id", "").strip()
    if not template_id:
        return _error(400, "template_id is required")

    try:
        container = get_container("templates")
        items = list(container.query_items(
            query="SELECT * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": template_id}],
            enable_cross_partition_query=True,
        ))

        if not items:
            return _error(404, f"Template '{template_id}' not found")

        return _json(items[0])

    except Exception as exc:  # noqa: BLE001
        logger.exception("get_template %s failed: %s", template_id, exc)
        return _error(500, "Internal server error")


# ---------------------------------------------------------------------------
# PUT /api/templates/{id}
# ---------------------------------------------------------------------------

@bp.route(route="templates/{template_id}", methods=["PUT"], auth_level=func.AuthLevel.FUNCTION)
def update_template(req: func.HttpRequest) -> func.HttpResponse:
    """Update an existing template (ITAdmin only)."""
    try:
        roles = get_caller_roles(req)
        require_any_role(roles, ADMIN_ROLES)
    except AuthError as exc:
        return _error(exc.status_code, exc.message)

    template_id: str = req.route_params.get("template_id", "").strip()
    if not template_id:
        return _error(400, "template_id is required")

    try:
        body = req.get_json()
    except ValueError:
        return _error(400, "Request body must be valid JSON")

    # Validate required fields
    if not isinstance(body.get("fields"), dict):
        return _error(400, "Body must contain 'fields' object")

    # Sanitize string fields (OWASP LLM01)
    try:
        sanitize_string_fields(body)
    except ValueError as exc:
        return _error(400, str(exc))

    try:
        container = get_container("templates")
        items = list(container.query_items(
            query="SELECT * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": template_id}],
            enable_cross_partition_query=True,
        ))

        if not items:
            return _error(404, f"Template '{template_id}' not found")

        existing = items[0]
        existing["fields"] = body["fields"]
        if "name" in body:
            existing["name"] = body["name"]
        existing["updated_at"] = datetime.now(timezone.utc).isoformat()

        container.upsert_item(existing)
        logger.info("Template %s updated", template_id)

        return _json(existing)

    except Exception as exc:  # noqa: BLE001
        logger.exception("update_template %s failed: %s", template_id, exc)
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
