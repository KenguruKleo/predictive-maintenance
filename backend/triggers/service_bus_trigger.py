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

import azure.durable_functions as df
import azure.functions as func

logger = logging.getLogger(__name__)

bp = df.Blueprint()


@bp.service_bus_queue_trigger(
    arg_name="msg",
    queue_name="alert-queue",
    connection="SERVICEBUS_CONNECTION_STRING",
)
@bp.durable_client_input(client_name="client")
async def service_bus_start_orchestrator(
    msg: func.ServiceBusMessage,
    client: df.DurableOrchestrationClient,
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
        logger.warning(
            "Orchestrator instance %s already exists (status=%s) — ignoring duplicate Service Bus start",
            instance_id,
            existing_status,
        )
        return

    await client.start_new(
        orchestration_function_name="incident_orchestrator",
        instance_id=instance_id,
        client_input=payload,
    )

    logger.info(
        "Started orchestrator instance_id=%s for incident %s",
        instance_id,
        incident_id,
    )
