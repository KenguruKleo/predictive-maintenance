"""
Service Bus Trigger — start Durable orchestrator from alert-queue (T-024)

Fires when a message arrives on the alert-queue Service Bus queue.
The message payload is the same dict written by http_ingest_alert.py:

    {
        "incident_id": "INC-2026-XXXX",
        "equipment_id": "GR-204",
        "alert_type": "...",
        "severity": "...",
        ... (full alert payload)
    }

The orchestrator instance ID is "durable-{incident_id}" to allow the
http_decision trigger to resume the correct instance.
"""

import json
import logging
import os
from datetime import datetime, timezone

import azure.durable_functions as df
import azure.functions as func

from shared.cosmos_client import get_cosmos_client
from shared.incident_store import get_incident_by_id, patch_incident_by_id
from shared.signalr_client import notify_incident_status_changed_sync

logger = logging.getLogger(__name__)
DB_NAME = os.getenv("COSMOS_DATABASE", "sentinel-intelligence")
_LIVE_DURABLE_STATUSES = {"Running", "Pending", "ContinuedAsNew"}

bp = df.Blueprint()


def _mark_incident_ingested(incident_id: str, equipment_id: str, instance_id: str) -> None:
    """Persist the transition from alert-created to Durable-ingested."""
    db = get_cosmos_client().get_database_client(DB_NAME)
    incident = get_incident_by_id(db, incident_id)
    previous_status = str(incident.get("status") or "").strip() or None
    if previous_status not in {None, "", "open", "queued", "ingested"}:
        return

    workflow_state = incident.get("workflow_state") or {}
    if previous_status == "ingested" and workflow_state.get("durable_instance_id") == instance_id:
        return

    now_iso = datetime.now(timezone.utc).isoformat()

    patch_incident_by_id(
        db,
        incident_id,
        [
            {"op": "set", "path": "/status", "value": "ingested"},
            {
                "op": "set",
                "path": "/workflow_state",
                "value": {
                    **workflow_state,
                    "durable_instance_id": instance_id,
                    "current_step": "ingested",
                },
            },
            {"op": "set", "path": "/updatedAt", "value": now_iso},
            {"op": "set", "path": "/updated_at", "value": now_iso},
        ],
    )

    if previous_status != "ingested":
        notify_incident_status_changed_sync(
            incident_id=incident_id,
            new_status="ingested",
            previous_status=previous_status,
            equipment_id=equipment_id,
        )


@bp.service_bus_queue_trigger(
    arg_name="msg",
    queue_name="alert-queue",
    connection="SERVICEBUS_CONNECTION_STRING",
)
@bp.durable_client_input(client_name="client")
async def service_bus_start_orchestrator(
    msg: func.ServiceBusMessage,
    client,
) -> None:
    """Consume an alert message and start the incident orchestrator."""
    raw_body = msg.get_body().decode("utf-8")
    payload: dict = json.loads(raw_body)

    incident_id: str = payload.get("incident_id", "")
    if not incident_id:
        logger.error("Service Bus message missing incident_id — skipping")
        return

    instance_id = f"durable-{incident_id}"

    # Durable can return a placeholder status object with runtime_status=None
    # for a brand-new instance ID. Treat only non-empty runtime states as real
    # existing instances so fresh alerts can still start normally.
    existing = await client.get_status(instance_id)
    existing_status = getattr(existing, "runtime_status", None) if existing else None
    if existing_status is not None:
        existing_status_name = getattr(existing_status, "name", str(existing_status))
        if existing_status_name in _LIVE_DURABLE_STATUSES:
            try:
                _mark_incident_ingested(
                    incident_id=incident_id,
                    equipment_id=str(payload.get("equipment_id") or payload.get("equipmentId") or ""),
                    instance_id=instance_id,
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Existing live orchestrator for %s but failed to reconcile ingested status: %s",
                    incident_id,
                    exc,
                )
        logger.warning(
            "Orchestrator instance %s already exists (status=%s) — ignoring duplicate Service Bus start",
            instance_id,
            existing_status,
        )
        return

    try:
        await client.start_new(
            orchestration_function_name="incident_orchestrator",
            instance_id=instance_id,
            client_input=payload,
        )
    except Exception as exc:  # noqa: BLE001
        concurrent = await client.get_status(instance_id)
        concurrent_status = getattr(concurrent, "runtime_status", None) if concurrent else None
        if concurrent_status is not None:
            concurrent_status_name = getattr(concurrent_status, "name", str(concurrent_status))
            if concurrent_status_name in _LIVE_DURABLE_STATUSES:
                try:
                    _mark_incident_ingested(
                        incident_id=incident_id,
                        equipment_id=str(payload.get("equipment_id") or payload.get("equipmentId") or ""),
                        instance_id=instance_id,
                    )
                except Exception as reconcile_exc:  # noqa: BLE001
                    logger.exception(
                        "Concurrent orchestrator for %s but failed to reconcile ingested status: %s",
                        incident_id,
                        reconcile_exc,
                    )
            logger.warning(
                "Orchestrator instance %s was created concurrently (status=%s) — ignoring duplicate Service Bus start",
                instance_id,
                concurrent_status,
            )
            return
        raise exc

    try:
        _mark_incident_ingested(
            incident_id=incident_id,
            equipment_id=str(payload.get("equipment_id") or payload.get("equipmentId") or ""),
            instance_id=instance_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Started orchestrator for %s but failed to mark incident as ingested: %s",
            incident_id,
            exc,
        )

    logger.info(
        "Started orchestrator instance_id=%s for incident %s",
        instance_id,
        incident_id,
    )
