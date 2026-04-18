"""
POST /api/alerts — SCADA/MES alert ingestion endpoint.

Validates the incoming payload, enriches it with equipment context from Cosmos DB,
classifies severity, and publishes to the Service Bus alert-queue for the
Durable orchestrator to pick up (T-024).
"""

import json
import logging
from datetime import datetime, timezone

import azure.functions as func

from shared.cosmos_client import get_container
from shared.servicebus_client import publish_alert
from utils.id_generator import generate_incident_id
from utils.severity import classify_severity
from utils.validation import sanitize_string_fields, validate_alert_payload

logger = logging.getLogger(__name__)

bp = func.Blueprint()


@bp.route(route="alerts", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def ingest_alert(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/alerts
    Accept a SCADA/MES anomaly alert, create an incident, publish to Service Bus.

    Returns:
        202 Accepted     — alert queued, includes incident_id
        200 OK           — duplicate alert_id, returns existing incident_id
        400 Bad Request  — validation error
        404 Not Found    — unknown equipment_id
        500 Internal     — unexpected error
    """
    # ------------------------------------------------------------------
    # 1. Parse body
    # ------------------------------------------------------------------
    try:
        body = req.get_json()
    except ValueError:
        return _error(400, "Request body must be valid JSON")

    # ------------------------------------------------------------------
    # 2. Validate structure + types
    # ------------------------------------------------------------------
    try:
        validate_alert_payload(body)
    except ValueError as exc:
        return _error(400, str(exc))

    # ------------------------------------------------------------------
    # 3. Prompt injection guard (OWASP LLM01)
    # ------------------------------------------------------------------
    try:
        sanitize_string_fields(body)
    except ValueError as exc:
        logger.warning("Prompt injection attempt blocked: %s", exc)
        return _error(400, str(exc))

    # ------------------------------------------------------------------
    # 4. Idempotency check — if alert_id provided, dedup via Cosmos
    # ------------------------------------------------------------------
    alert_id = body.get("alert_id")
    if alert_id:
        existing = _find_by_source_alert_id(alert_id)
        if existing:
            logger.info("Duplicate alert_id=%s → returning existing incident %s", alert_id, existing["id"])
            return func.HttpResponse(
                body=json.dumps({"incident_id": existing["id"], "status": "already_exists"}),
                status_code=200,
                mimetype="application/json",
            )

    # ------------------------------------------------------------------
    # 5. Equipment lookup (validate exists + fetch context)
    # ------------------------------------------------------------------
    equipment = _get_equipment(body["equipment_id"])
    if equipment is None:
        return _error(404, f"Equipment '{body['equipment_id']}' not found")

    # ------------------------------------------------------------------
    # 6. Generate incident_id + classify severity
    # ------------------------------------------------------------------
    incident_id = generate_incident_id()
    severity = classify_severity(body)

    # ------------------------------------------------------------------
    # 7. Build enriched payload
    # ------------------------------------------------------------------
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    payload = {
        **body,
        "id": incident_id,
        "incident_id": incident_id,
        "incidentId": incident_id,
        "equipmentId": body["equipment_id"],
        "source_alert_id": alert_id,
        "severity": severity,
        "status": "open",
        "reported_at": now,
        "createdAt": now,
        "updatedAt": now,
        "equipment_name": equipment.get("name", body["equipment_id"]),
        "equipment_criticality": equipment.get("criticality", "unknown"),
        "equipment_type": equipment.get("type", "unknown"),
        "location": equipment.get("location", "unknown"),
        "title": _build_incident_title(body),
        "parameter_excursion": _build_parameter_excursion(body),
    }

    # ------------------------------------------------------------------
    # 7b. Persist stub to Cosmos immediately (idempotency + ID counter)
    # ------------------------------------------------------------------
    try:
        _write_incident_stub(payload)
    except Exception as exc:
        logger.exception("Failed to persist incident stub to Cosmos: %s", exc)
        return _error(500, "Failed to persist incident. Please retry.")

    # ------------------------------------------------------------------
    # 8. Publish to Service Bus → Durable orchestrator (T-024) will pick up
    # ------------------------------------------------------------------
    try:
        publish_alert(payload)
    except Exception as exc:
        logger.exception("Failed to publish alert to Service Bus: %s", exc)
        return _error(500, "Failed to queue alert for processing. Please retry.")

    logger.info("Alert queued: incident_id=%s equipment=%s severity=%s", incident_id, body["equipment_id"], severity)

    return func.HttpResponse(
        body=json.dumps({
            "incident_id": incident_id,
            "status": "queued",
            "severity": severity,
            "message": "Alert received and queued for processing",
        }),
        status_code=202,
        mimetype="application/json",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_incident_title(body: dict) -> str:
    """Generate a short human-readable title from raw alert fields."""
    param = body.get("parameter", "")
    measured = body.get("measured_value")
    upper = body.get("upper_limit")
    lower = body.get("lower_limit")
    equip = body.get("equipment_id", "")

    param_label = " ".join(w.capitalize() for w in param.replace("_", " ").split()) if param else ""

    if measured is not None and upper is not None and measured > upper:
        direction = "HIGH"
    elif measured is not None and lower is not None and measured < lower:
        direction = "LOW"
    elif param:
        direction = "Excursion"
    else:
        return f"{body.get('deviation_type', 'Alert')} — {equip}".strip(" —")

    return f"{param_label} {direction} — {equip}"


def _build_parameter_excursion(body: dict) -> dict | None:
    """Build a nested parameter_excursion object from root-level alert fields."""
    param = body.get("parameter")
    measured = body.get("measured_value")
    if param is None and measured is None:
        return None
    return {
        "parameter": param or "",
        "measured_value": measured if measured is not None else 0,
        "unit": body.get("unit", ""),
        "duration_seconds": body.get("duration_seconds", 0),
        "lower_limit": body.get("lower_limit"),
        "upper_limit": body.get("upper_limit"),
    }


def _write_incident_stub(payload: dict) -> None:
    """Persist a minimal incident document to Cosmos so the ID counter advances
    and idempotency queries work. The Durable orchestrator (T-024) will enrich it."""
    from azure.cosmos.exceptions import CosmosResourceExistsError
    container = get_container("incidents")
    try:
        container.create_item(payload, enable_automatic_id_generation=False)
    except CosmosResourceExistsError:
        pass  # concurrent duplicate — idempotent


def _get_equipment(equipment_id: str) -> dict | None:
    """Look up equipment by id. Returns None if not found."""
    try:
        container = get_container("equipment")
        return container.read_item(item=equipment_id, partition_key=equipment_id)
    except Exception as exc:
        logger.error("Equipment lookup failed for '%s': %s", equipment_id, exc)
        return None


def _find_by_source_alert_id(alert_id: str) -> dict | None:
    """Find existing incident by source_alert_id (for idempotency)."""
    try:
        container = get_container("incidents")
        query = "SELECT * FROM c WHERE c.source_alert_id = @alert_id OFFSET 0 LIMIT 1"
        results = list(container.query_items(
            query=query,
            parameters=[{"name": "@alert_id", "value": alert_id}],
            enable_cross_partition_query=True,
        ))
        return results[0] if results else None
    except Exception:
        return None


def _error(status: int, message: str) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps({"error": message}),
        status_code=status,
        mimetype="application/json",
    )
