"""
Activity: enrich_context — pull equipment info + active batch from Cosmos DB (T-024)

Returns a dict with:
  - incident_id, equipment_id
  - equipment: equipment document
  - batch: most recent active batch for this equipment (or None)
  - recent_incidents: last 5 incidents for this equipment
"""

import logging
import os

import azure.durable_functions as df

from shared.cosmos_client import get_cosmos_client
from shared.incident_store import patch_incident_by_id

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("COSMOS_DATABASE", "sentinel-intelligence")

bp = df.Blueprint()


@bp.activity_trigger(input_name="input_data")
def enrich_context(input_data: dict) -> dict:
    client = get_cosmos_client()
    db = client.get_database_client(DB_NAME)

    incident_id: str = input_data["incident_id"]
    equipment_id: str = input_data.get("equipment_id", "")
    batch_id: str = input_data.get("batch_id", "")

    context: dict = {
        "incident_id": incident_id,
        "equipment_id": equipment_id,
        "batch_id": batch_id,
    }

    # ── Equipment ───────────────────────────────────────────────────────────
    try:
        eq_container = db.get_container_client("equipment")
        if equipment_id:
            eq_doc = eq_container.read_item(item=equipment_id, partition_key=equipment_id)
            context["equipment"] = {k: v for k, v in eq_doc.items() if not k.startswith("_")}
            logger.info("Enriched equipment for %s", equipment_id)
    except Exception as exc:
        logger.warning("Could not fetch equipment %s: %s", equipment_id, exc)
        context["equipment"] = {}

    # ── Active batch ────────────────────────────────────────────────────────
    try:
        batches = db.get_container_client("batches")
        results = []
        if batch_id:
            batch_query = (
                "SELECT * FROM c WHERE "
                "c.id = @batchId OR c.batch_id = @batchId OR c.batch_number = @batchId"
            )
            results = list(
                batches.query_items(
                    query=batch_query,
                    parameters=[{"name": "@batchId", "value": batch_id}],
                    enable_cross_partition_query=True,
                )
            )

        if not results:
            query = (
                "SELECT * FROM c "
                "WHERE (c.equipmentId = @eqId OR c.equipment_id = @eqId) "
                "AND c.status IN ('active', 'in-progress', 'in_progress')"
            )
            params = [{"name": "@eqId", "value": equipment_id}]
            results = sorted(
                batches.query_items(query=query, parameters=params, enable_cross_partition_query=True),
                key=lambda item: item.get("startDate") or item.get("start_time") or "",
                reverse=True,
            )
        context["batch"] = results[0] if results else None
    except Exception as exc:
        logger.warning("Could not fetch active batch: %s", exc)
        context["batch"] = None

    batch = context.get("batch") or {}
    product = batch.get("product") or batch.get("product_name") or batch.get("productName")
    production_stage = (
        batch.get("production_stage")
        or batch.get("stage_step")
        or batch.get("stage")
    )
    if product:
        context["product"] = product
    if production_stage:
        context["production_stage"] = production_stage

    if product or production_stage:
        patch_operations = []
        if batch_id:
            patch_operations.append({"op": "set", "path": "/batch_id", "value": batch_id})
        if product:
            patch_operations.append({"op": "set", "path": "/product", "value": product})
        if production_stage:
            patch_operations.append(
                {"op": "set", "path": "/production_stage", "value": production_stage}
            )
        try:
            patch_incident_by_id(db, incident_id, patch_operations)
        except Exception as exc:
            logger.warning("Could not patch incident %s with batch context: %s", incident_id, exc)

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
        context["recent_incidents"] = recent
    except Exception as exc:
        logger.warning("Could not fetch recent incidents: %s", exc)
        context["recent_incidents"] = []

    logger.info(
        "Context enriched for incident %s — batch=%s, recent=%d",
        incident_id,
        context["batch"].get("id") if context.get("batch") else "none",
        len(context.get("recent_incidents", [])),
    )
    return context
