"""
Activity: enrich_context — pull equipment info + active batch from Cosmos DB (T-024)

Returns a dict with:
  - equipment: equipment document
  - activeBatch: most recent batch for this equipment (if any)
  - recentIncidents: last 5 incidents for this equipment
  - extra_info_request: populated by orchestrator if operator asked for more detail
"""

import logging
import os

from shared.cosmos_client import get_cosmos_client

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("COSMOS_DATABASE", "sentinel-intelligence")


def enrich_context(input_data: dict) -> dict:
    client = get_cosmos_client()
    db = client.get_database_client(DB_NAME)

    incident_id: str = input_data["incident_id"]
    equipment_id: str = input_data.get("equipment_id", "")

    context: dict = {"incident_id": incident_id, "equipment_id": equipment_id}

    # ── Equipment ───────────────────────────────────────────────────────────
    try:
        eq_container = db.get_container_client("equipment")
        if equipment_id:
            eq_doc = eq_container.read_item(item=equipment_id, partition_key=equipment_id)
            context["equipment"] = eq_doc
            logger.info("Enriched equipment for %s", equipment_id)
    except Exception as exc:
        logger.warning("Could not fetch equipment %s: %s", equipment_id, exc)
        context["equipment"] = {}

    # ── Active batch ────────────────────────────────────────────────────────
    try:
        batches = db.get_container_client("batches")
        query = (
            "SELECT TOP 1 * FROM c "
            "WHERE c.equipmentId = @eqId "
            "AND c.status IN ('active', 'in-progress') "
            "ORDER BY c.startDate DESC"
        )
        params = [{"name": "@eqId", "value": equipment_id}]
        results = list(
            batches.query_items(query=query, parameters=params, enable_cross_partition_query=True)
        )
        context["activeBatch"] = results[0] if results else None
    except Exception as exc:
        logger.warning("Could not fetch active batch: %s", exc)
        context["activeBatch"] = None

    # ── Recent incidents ────────────────────────────────────────────────────
    try:
        incidents = db.get_container_client("incidents")
        query = (
            "SELECT TOP 5 c.id, c.alertType, c.severity, c.status, c.createdAt "
            "FROM c WHERE c.equipmentId = @eqId AND c.id != @self "
            "ORDER BY c.createdAt DESC"
        )
        params = [
            {"name": "@eqId", "value": equipment_id},
            {"name": "@self", "value": incident_id},
        ]
        recent = list(
            incidents.query_items(query=query, parameters=params, enable_cross_partition_query=True)
        )
        context["recentIncidents"] = recent
    except Exception as exc:
        logger.warning("Could not fetch recent incidents: %s", exc)
        context["recentIncidents"] = []

    logger.info(
        "Context enriched for incident %s — batch=%s, recent=%d",
        incident_id,
        context["activeBatch"].get("id") if context.get("activeBatch") else "none",
        len(context.get("recentIncidents", [])),
    )
    return context
