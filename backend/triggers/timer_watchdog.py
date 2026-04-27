"""
Watchdog Timer Trigger — auto-recover stuck Durable orchestrators.

Runs every 5 minutes. Queries Cosmos DB for incidents stuck in an
in-progress state for longer than WATCHDOG_STUCK_THRESHOLD_MINUTES
(default 15 min) that have no live Durable orchestrator instance.

Recovery: republish the original alert payload to Service Bus, which
causes the service_bus_trigger to start a fresh orchestrator instance.

Environment variables:
  WATCHDOG_STUCK_THRESHOLD_MINUTES  — minutes before an in-progress
                                       incident is considered stuck (default 15)
  WATCHDOG_MAX_RECOVER_PER_RUN      — max incidents to requeue per invocation
                                       (default 10, safety cap)
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import azure.durable_functions as df
import azure.functions as func

from shared.cosmos_client import get_container
from shared.servicebus_client import publish_alert

logger = logging.getLogger(__name__)

# Statuses that mean the orchestrator should be running but may have died.
# awaiting_agents is excluded here because watchdog recovery only rebuilds the
# original alert payload and would lose follow-up question context.
_STUCK_STATUSES = frozenset({
    "open",
    "queued",
    "ingested",
    "queued_for_analysis",
    "analyzing",
    "analyzing_agents",
})
_STUCK_STATUS_SQL = "','".join(sorted(_STUCK_STATUSES))

# pending_approval incidents where the durable is NOT_FOUND are orphaned
# (e.g. orchestrator ran on localhost but Cosmos record is shared).
# We recover them without a time threshold — if durable is gone, operator
# can never submit a decision no matter how recent the incident is.
_ORPHANED_APPROVAL_MIN_AGE_SECONDS: int = int(
    os.getenv("WATCHDOG_APPROVAL_ORPHAN_MIN_AGE_SECONDS", "120")
)  # 2 min grace to avoid race with freshly-created instances

# Durable statuses where the orchestrator is still alive — leave them alone.
_LIVE_DURABLE_STATUSES = frozenset({"Running", "Pending", "ContinuedAsNew"})

_STUCK_THRESHOLD_MINUTES: int = int(os.getenv("WATCHDOG_STUCK_THRESHOLD_MINUTES", "15"))
_MAX_RECOVER_PER_RUN: int = int(os.getenv("WATCHDOG_MAX_RECOVER_PER_RUN", "10"))

bp = df.Blueprint()


def _reconstruct_alert_payload(incident: dict[str, Any]) -> dict[str, Any]:
    """Rebuild the alert payload from a stored Cosmos incident document."""
    incident_id = str(
        incident.get("id") or incident.get("incident_id") or incident.get("incidentId") or ""
    )
    equipment_id = str(incident.get("equipment_id") or incident.get("equipmentId") or "")
    batch_id = str(incident.get("batch_id") or incident.get("batchId") or "")
    alert_id = incident.get("alert_id") or incident.get("source_alert_id")

    payload: dict[str, Any] = {
        "id": incident_id,
        "incident_id": incident_id,
        "incidentId": incident_id,
        "equipment_id": equipment_id,
        "equipmentId": equipment_id,
        "severity": incident.get("severity", "critical"),
        "status": "open",
        "reported_at": incident.get("reported_at") or incident.get("createdAt") or incident.get("created_at"),
        "createdAt": incident.get("createdAt") or incident.get("created_at") or incident.get("reported_at"),
        "updatedAt": incident.get("createdAt") or incident.get("created_at") or incident.get("reported_at"),
        "equipment_name": incident.get("equipment_name") or incident.get("title") or equipment_id,
        "equipment_criticality": incident.get("equipment_criticality") or "unknown",
        "equipment_type": incident.get("equipment_type") or "unknown",
        "location": incident.get("location") or "unknown",
        "title": incident.get("title") or incident_id,
    }

    for key in (
        "deviation_type",
        "parameter",
        "measured_value",
        "lower_limit",
        "upper_limit",
        "unit",
        "duration_seconds",
        "detected_by",
        "detected_at",
    ):
        if incident.get(key) is not None:
            payload[key] = incident[key]

    if alert_id:
        payload["alert_id"] = alert_id
        payload["source_alert_id"] = alert_id
    if batch_id:
        payload["batch_id"] = batch_id
    if incident.get("parameter_excursion") is not None:
        payload["parameter_excursion"] = incident["parameter_excursion"]

    return payload


_COSMOS_INCIDENT_FIELDS = (
    "c.id, c.incident_id, c.status, c._ts, c.equipment_id, c.equipmentId, "
    "c.severity, c.title, c.reported_at, c.createdAt, c.created_at, "
    "c.equipment_name, c.equipment_criticality, c.equipment_type, c.location, "
    "c.deviation_type, c.parameter, c.measured_value, c.lower_limit, c.upper_limit, "
    "c.unit, c.duration_seconds, c.detected_by, c.detected_at, "
    "c.alert_id, c.source_alert_id, c.batch_id, c.batchId, c.parameter_excursion"
)


def _query_stuck_incidents(threshold_seconds: int) -> list[dict[str, Any]]:
    """Return incidents in a stuck analysis status older than threshold_seconds."""
    cutoff_ts = int(time.time()) - threshold_seconds
    container = get_container("incidents")
    query = (
        f"SELECT {_COSMOS_INCIDENT_FIELDS} "
        f"FROM c WHERE c.status IN ('{_STUCK_STATUS_SQL}') "
        "AND (NOT IS_DEFINED(c.workflow_state.current_step) OR c.workflow_state.current_step != 'analyzing_followup') "
        f"AND c._ts < {cutoff_ts}"
    )
    return list(container.query_items(query, enable_cross_partition_query=True))


def _query_orphaned_approvals() -> list[dict[str, Any]]:
    """Return pending_approval incidents older than the grace period.

    These may have their durable orchestrator on a different host (e.g. localhost).
    The caller checks whether the durable instance actually exists before recovering.
    """
    cutoff_ts = int(time.time()) - _ORPHANED_APPROVAL_MIN_AGE_SECONDS
    container = get_container("incidents")
    query = (
        f"SELECT {_COSMOS_INCIDENT_FIELDS} "
        f"FROM c WHERE c.status = 'pending_approval' AND c._ts < {cutoff_ts}"
    )
    return list(container.query_items(query, enable_cross_partition_query=True))


@bp.timer_trigger(
    schedule="0 */1 * * * *",
    arg_name="timer",
    run_on_startup=False,
    use_monitor=False,
)
@bp.durable_client_input(client_name="client")
async def orchestrator_watchdog(timer: func.TimerRequest, client) -> None:
    """Check for stuck orchestrators and requeue them to Service Bus."""
    if timer.past_due:
        logger.info("Watchdog timer is running late — proceeding anyway")

    threshold_seconds = _STUCK_THRESHOLD_MINUTES * 60
    stuck = _query_stuck_incidents(threshold_seconds)
    orphaned_approvals = _query_orphaned_approvals()

    candidates = stuck + orphaned_approvals
    if not candidates:
        logger.info(
            "Watchdog: no stuck incidents found (stuck_threshold=%d min, approval_grace=%ds)",
            _STUCK_THRESHOLD_MINUTES,
            _ORPHANED_APPROVAL_MIN_AGE_SECONDS,
        )
        return

    logger.info(
        "Watchdog: candidates — stuck=%d orphaned_approvals=%d",
        len(stuck),
        len(orphaned_approvals),
    )
    recovered = 0

    for incident in candidates[:_MAX_RECOVER_PER_RUN]:
        is_approval = incident.get("status") == "pending_approval"
        incident_id = str(incident.get("id") or incident.get("incident_id") or "")
        if not incident_id:
            continue

        instance_id = f"durable-{incident_id}"
        try:
            status = await client.get_status(instance_id)
            runtime_status = getattr(status, "runtime_status", None) if status else None

            if runtime_status is not None and str(runtime_status) in _LIVE_DURABLE_STATUSES:
                logger.debug(
                    "Watchdog: incident %s has live orchestrator (status=%s) — skipping",
                    incident_id,
                    runtime_status,
                )
                continue

            # For pending_approval, only recover when orchestrator is truly absent
            # (NOT_FOUND). Completed/Failed are handled the same way as stuck.
            if is_approval and runtime_status is not None and str(runtime_status) not in (
                "Failed",
                "Terminated",
                "Canceled",
            ):
                logger.debug(
                    "Watchdog: pending_approval incident %s durable=%s — skipping",
                    incident_id,
                    runtime_status,
                )
                continue

            # Orchestrator is gone (None / NOT_FOUND / Failed / Terminated / Completed)
            payload = _reconstruct_alert_payload(incident)
            publish_alert(payload)
            recovered += 1
            logger.warning(
                "Watchdog: requeued stuck incident %s (cosmos_status=%s, durable_status=%s)",
                incident_id,
                incident.get("status"),
                runtime_status if runtime_status is not None else "NOT_FOUND",
            )

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Watchdog: error processing incident %s — %s", incident_id, exc
            )

    logger.info(
        "Watchdog: run complete — candidates=%d recovered=%d max_cap=%d",
        len(candidates),
        recovered,
        _MAX_RECOVER_PER_RUN,
    )
