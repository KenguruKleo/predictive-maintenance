"""
Incident Orchestrator — Azure Durable Functions (T-024, ADR-002)

Workflow (first half — enrich → agents → notify → HITL loop):
  1. enrich_context         — pull equipment + batch context from Cosmos DB
  2. run_foundry_agents     — Foundry Orchestrator Agent (Research + Document via Connected Agents)
  3. notify_operator        — push SignalR notification to React UI (approval_required)
  4. wait_for_external_event("operator_decision") with 24h timeout + more_info loop
     └ more_info: re-run agents with operator questions (up to MAX_MORE_INFO_ROUNDS)
     └ timeout:   escalate to qa-manager, wait indefinitely

Workflow (second half — T-024 §2):
  5. run_execution_agent    — Execution Agent builds & runs CAPA plan (if approved)
     OR close_incident      — sets status=rejected (if rejected)
  6. finalize_audit         — final audit record + close incident

ADR-002: single run_foundry_agents activity; Connected Agents pattern in Foundry.
"""

import json
import logging
import os
from datetime import timedelta

import azure.durable_functions as df

logger = logging.getLogger(__name__)

MAX_MORE_INFO_ROUNDS = int(os.getenv("MAX_MORE_INFO_ROUNDS", "3"))

bp = df.Blueprint()


def _coerce_dict(value: object, fallback: dict | None = None) -> dict:
    """Normalize Durable payloads across SDK serialization shapes."""
    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        raw: object = value
        for _ in range(2):
            try:
                raw = json.loads(raw) if isinstance(raw, str) else raw
            except json.JSONDecodeError:
                break
            if isinstance(raw, dict):
                return raw

    return fallback or {}


def _coerce_decision(value: object) -> dict:
    """Normalize Durable external event payloads across SDK serialization shapes."""
    decision = _coerce_dict(value)
    if not decision and isinstance(value, str):
        decision = {"action": "rejected", "reason": "Invalid operator decision payload"}
    elif not decision:
        decision = {"action": "rejected", "reason": "Missing operator decision payload"}

    action_aliases = {"approve": "approved", "reject": "rejected"}
    action = str(decision.get("action", "rejected"))
    decision["action"] = action_aliases.get(action, action)
    return decision


@bp.orchestration_trigger(context_name="context")
def incident_orchestrator(context: df.DurableOrchestrationContext):
    """Main stateful workflow triggered by a Service Bus message."""

    input_data: dict = _coerce_dict(context.get_input())
    incident_id: str = input_data["incident_id"]

    if not context.is_replaying:
        logger.info("Orchestrator started for incident %s", incident_id)

    # ── Step 1: Enrich context (equipment + batch from Cosmos) ─────────────
    context_data: dict = _coerce_dict((yield context.call_activity(
        "enrich_context",
        {
            "incident_id": incident_id,
            "equipment_id": input_data.get("equipment_id"),
            "batch_id": input_data.get("batch_id"),
        },
    )))
    context_data["operator_questions"] = []
    # Carry alert payload into context so run_foundry_agents can use it
    context_data["alert_payload"] = input_data

    # ── Step 2: Run Foundry agents (Research + Document via Connected Agents) ─
    ai_result: dict = _coerce_dict((yield context.call_activity(
        "run_foundry_agents",
        {"incident_id": incident_id, "context": context_data},
    )))

    # ── Step 3: Notify operator via SignalR ────────────────────────────────
    yield context.call_activity(
        "notify_operator",
        {
            "incident_id": incident_id,
            "ai_result": ai_result,
            "equipment_id": input_data.get("equipment_id", ""),
            "batch_id": context_data.get("batch", {}).get("id") or input_data.get("batch_id", ""),
            "product": context_data.get("product", ""),
            "production_stage": context_data.get("production_stage", ""),
        },
    )

    # ── Step 4: HITL wait loop ─────────────────────────────────────────────
    more_info_rounds = 0
    decision: dict | None = None

    while True:
        deadline = context.current_utc_datetime + timedelta(hours=24)
        decision_task = context.wait_for_external_event("operator_decision")
        timeout_task = context.create_timer(deadline)

        winner = yield context.task_any([decision_task, timeout_task])

        if winner is timeout_task:
            # 24 h passed → escalate to QA Manager, wait indefinitely
            if not context.is_replaying:
                logger.warning("Incident %s timed out — escalating to qa-manager", incident_id)
            yield context.call_activity(
                "notify_operator",
                {
                    "incident_id": incident_id,
                    "ai_result": ai_result,
                    "escalation": True,
                    "role": "qa-manager",
                },
            )
            decision = _coerce_decision((yield context.wait_for_external_event("operator_decision")))
        else:
            timeout_task.cancel()
            decision = _coerce_decision(decision_task.result)

        action: str = decision.get("action", "rejected")

        if action == "more_info" and more_info_rounds < MAX_MORE_INFO_ROUNDS:
            more_info_rounds += 1
            context_data["operator_questions"].append(
                {
                    "round": more_info_rounds,
                    "question": decision.get("question", ""),
                    "asked_by": decision.get("user_id", "operator"),
                }
            )
            # Re-run Foundry agents with enriched context (new round)
            ai_result = _coerce_dict((yield context.call_activity(
                "run_foundry_agents",
                {
                    "incident_id": incident_id,
                    "context": context_data,
                    "more_info_round": more_info_rounds,
                },
            )))
            yield context.call_activity(
                "notify_operator",
                {
                    "incident_id": incident_id,
                    "ai_result": ai_result,
                    "batch_id": context_data.get("batch", {}).get("id") or input_data.get("batch_id", ""),
                    "product": context_data.get("product", ""),
                    "production_stage": context_data.get("production_stage", ""),
                },
            )
            continue  # loop back to wait for next decision

        # approved / rejected / more_info limit reached → exit loop
        break

    # ── Step 5: Execute or close ───────────────────────────────────────────
    exec_result: dict = {}
    if action == "approved":
        exec_result = _coerce_dict((yield context.call_activity(
            "run_execution_agent",
            {
                "incident_id": incident_id,
                "ai_result": ai_result,
                "approver_id": decision.get("user_id"),
                "approval_notes": decision.get("reason"),
            },
        )))
    else:
        exec_result = _coerce_dict((yield context.call_activity(
            "close_incident",
            {
                "incident_id": incident_id,
                "rejection_reason": decision.get("reason", "auto-rejected"),
            },
        )))

    # ── Step 6: Finalize audit record ──────────────────────────────────────
    yield context.call_activity(
        "finalize_audit",
        {
            "incident_id": incident_id,
            "decision": decision,
            "more_info_rounds": more_info_rounds,
            "ai_result": ai_result,
            "exec_result": exec_result,
        },
    )
