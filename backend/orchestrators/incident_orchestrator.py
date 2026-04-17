"""
Incident Orchestrator — Azure Durable Functions (T-024)

Workflow:
  1. create_incident    — persist initial incident record to Cosmos DB
  2. enrich_context     — pull equipment history + active batch from Cosmos DB
  3. run_agents         — Research Agent + Document Agent via Azure AI Foundry
  4. notify_operator    — push SignalR event to React UI
  5. wait_for_decision  — waitForExternalEvent("operator_decision") with 24h timeout
  6. execute_decision   — Execution Agent (if approved) or close (if rejected)
  7. finalize_audit     — write final audit record

Human-in-the-loop loop supports "more_info" up to MAX_LOOPS times.
On 24h timeout → escalate to QA Manager role; wait indefinitely for their decision.
"""

import json
import logging
from datetime import timedelta

import azure.durable_functions as df

logger = logging.getLogger(__name__)

MAX_LOOPS = 3


def incident_orchestrator(context: df.DurableOrchestrationContext):
    """Main stateful workflow triggered by a Service Bus message."""

    input_data: dict = context.get_input()
    incident_id: str = input_data["incident_id"]
    alert_payload: dict = input_data.get("alert_payload", input_data)

    if not context.is_replaying:
        logger.info("Orchestrator started for incident %s", incident_id)

    # ── Step 1: Create initial incident record ──────────────────────────────
    incident_id = yield context.call_activity(
        "create_incident",
        {"incident_id": incident_id, "alert_payload": alert_payload, "status": "open"},
    )

    # ── Step 2: Enrich context ──────────────────────────────────────────────
    context_data: dict = yield context.call_activity(
        "enrich_context",
        {"incident_id": incident_id, "equipment_id": alert_payload.get("equipment_id")},
    )

    # ── Human-in-the-loop ───────────────────────────────────────────────────
    loop_count = 0
    decision = None
    ai_result = None

    while decision is None and loop_count < MAX_LOOPS:
        # Step 3: Run agents
        ai_result = yield context.call_activity(
            "run_agents",
            {
                "incident_id": incident_id,
                "context": context_data,
                "loop_count": loop_count,
            },
        )

        # Step 4: Notify operator via SignalR
        yield context.call_activity(
            "notify_operator",
            {
                "incident_id": incident_id,
                "ai_result": ai_result,
                "escalation": False,
                "role": "operator",
            },
        )

        # Step 5: Wait for decision or 24h timeout
        deadline = context.current_utc_datetime + timedelta(hours=24)
        decision_event = context.wait_for_external_event("operator_decision")
        timeout_event = context.create_timer(deadline)

        winner = yield context.task_any([decision_event, timeout_event])

        if winner == timeout_event:
            # Escalate to QA Manager
            if not context.is_replaying:
                logger.warning("Incident %s timed out — escalating to QA Manager", incident_id)
            yield context.call_activity(
                "notify_operator",
                {
                    "incident_id": incident_id,
                    "ai_result": ai_result,
                    "escalation": True,
                    "role": "qa-manager",
                },
            )
            # Wait indefinitely for QA Manager
            decision = yield context.wait_for_external_event("operator_decision")
        else:
            decision = winner.result

        # Handle "more_info" loop
        if isinstance(decision, dict) and decision.get("action") == "more_info":
            context_data["extra_info_request"] = decision.get("question", "")
            loop_count += 1
            decision = None  # Reset → loop again

    # If we exhausted loops without a decision, auto-reject
    if decision is None:
        decision = {"action": "rejected", "reason": "Max info-request loops exceeded"}

    # ── Step 6: Execute or close ────────────────────────────────────────────
    exec_result = None
    if isinstance(decision, dict) and decision.get("action") == "approved":
        exec_result = yield context.call_activity(
            "execute_decision",
            {
                "incident_id": incident_id,
                "ai_result": ai_result,
                "approver": decision.get("user_id"),
            },
        )
    else:
        yield context.call_activity(
            "create_incident",
            {
                "incident_id": incident_id,
                "status": "rejected",
                "rejection_reason": decision.get("reason", ""),
            },
        )

    # ── Step 7: Finalize audit ──────────────────────────────────────────────
    yield context.call_activity(
        "finalize_audit",
        {
            "incident_id": incident_id,
            "decision": decision,
            "exec_result": exec_result,
        },
    )

    if not context.is_replaying:
        logger.info(
            "Orchestrator completed for incident %s — action: %s",
            incident_id,
            decision.get("action") if isinstance(decision, dict) else decision,
        )

    return {
        "incident_id": incident_id,
        "final_action": decision.get("action") if isinstance(decision, dict) else "unknown",
    }
