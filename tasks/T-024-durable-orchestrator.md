# T-024 · Azure Durable Functions — Workflow Orchestrator

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🔴 CRITICAL
**Status:** ✅ DONE (April 18-19, 2026)
**Blocks:** T-029, T-033
**Depends on:** T-020 (Cosmos DB), T-022 (Service Bus), T-025, T-026, T-027

---

## Goal

Implement stateful workflow through Azure Durable Functions (Python) with pause on human-in-the-loop.
Agent logic (Research → Document pipeline) is delegated to Foundry Connected Agents — **ADR-002** (see [02-architecture §8.10b](../02-architecture.md#810b-adr-002-foundry-connected-agents-vs-manual-orchestration)).

---

## Architectural solution (ADR-002)

> **Key change from original plan:**
> Instead of separate activities `run_research_agent` + `run_document_agent` — one activity `run_foundry_agents`.
> Foundry Orchestrator Agent (Connected Agents pattern) manages the Research → Document pipeline natively.
> `more_info` loop count and reasoning iterations — configured via `max_iterations` in Foundry and `MAX_MORE_INFO_ROUNDS` env var.

---

## Files

```
backend/
  function_app.py                    # Azure Functions app entry point
  orchestrators/
incident_orchestrator.py # @app.orchestration_trigger is the main workflow
  activities/
    enrich_context.py                # Cosmos DB: fetch equipment + batch context
    run_foundry_agents.py            # Foundry: Orchestrator Agent (Research + Document via Connected Agents)
notify_operator.py # SignalR: push notification to React UI
run_execution_agent.py # Foundry: Execution Agent (after approval)
    close_incident.py                # Cosmos DB: set status=rejected
    finalize_audit.py                # Cosmos DB: final audit record + status=closed
  triggers/
    service_bus_trigger.py           # @app.service_bus_queue_trigger — start orchestrator
    http_decision.py                 # POST /api/incidents/{id}/decision — resume orchestrator
```

## Workflow — step by step

```python
# incident_orchestrator.py (pseudo-code)
MAX_MORE_INFO_ROUNDS = int(os.getenv("MAX_MORE_INFO_ROUNDS", "10"))

async def incident_orchestrator(context: df.DurableOrchestrationContext):
    input_data = context.get_input()  # { alert_payload, incident_id }
    incident_id = input_data["incident_id"]

    # Step 1: Enrich context (equipment + batch from Cosmos)
    context_data = await context.call_activity("enrich_context", incident_id)
    context_data["operator_questions"] = []

    # Step 2: Run Foundry agents (Research + Document via Connected Agents)
    ai_result = await context.call_activity("run_foundry_agents", {
        "incident_id": incident_id,
        "context": context_data,
    })

    # Step 3: Notify operator via SignalR
    await context.call_activity("notify_operator", {
        "incident_id": incident_id,
        "ai_result": ai_result,
    })

    # Step 4: Wait for operator decision OR 24h timeout → escalate
    more_info_rounds = 0
    decision = None

    while True:
        deadline = context.current_utc_datetime + timedelta(hours=24)
        decision_task = context.wait_for_external_event("operator_decision")
        timeout_task = context.create_timer(deadline)
        winner = await first([decision_task, timeout_task])

        if winner is timeout_task:
            # 24h passed — escalate to QA Manager
            await context.call_activity("notify_operator", {
                "incident_id": incident_id,
                "escalation": True,
                "role": "qa-manager",
            })
            # Wait indefinitely for QA Manager
            decision = await context.wait_for_external_event("operator_decision")
        else:
            decision = winner

        action = decision.get("action")

        if action == "more_info" and more_info_rounds < MAX_MORE_INFO_ROUNDS:
            # Append operator question to context — Foundry gets full history
            context_data["operator_questions"].append({
                "round": more_info_rounds + 1,
                "question": decision.get("question"),
                "asked_by": decision.get("user_id"),
            })
            more_info_rounds += 1

            # Re-run Foundry agents with enriched context (new round)
            ai_result = await context.call_activity("run_foundry_agents", {
                "incident_id": incident_id,
                "context": context_data,
                "more_info_round": more_info_rounds,
            })
            await context.call_activity("notify_operator", {
                "incident_id": incident_id,
                "ai_result": ai_result,
            })
            # Loop back to wait for next decision
            continue

        # Approved / Rejected / more_info limit reached → exit loop
        break

    # Step 5: Execute or close
    if action == "approved":
        await context.call_activity("run_execution_agent", {
            "incident_id": incident_id,
            "ai_result": ai_result,
            "approver_id": decision.get("user_id"),
            "approval_notes": decision.get("reason"),
        })
    else:
        await context.call_activity("close_incident", {
            "incident_id": incident_id,
            "rejection_reason": decision.get("reason"),
        })

    # Step 6: Finalize audit record
    await context.call_activity("finalize_audit", {
        "incident_id": incident_id,
        "decision": decision,
        "more_info_rounds": more_info_rounds,
        "ai_result": ai_result,
    })
```

## Service Bus Trigger

```python
# triggers/service_bus_trigger.py
@app.service_bus_queue_trigger(
    arg_name="msg",
    queue_name="alert-queue",
    connection="SERVICE_BUS_NAMESPACE"
)
@app.durable_client_input(client_name="client")
async def service_bus_start_orchestrator(msg, client):
    payload = json.loads(msg.get_body())
    instance_id = f"durable-{payload['incident_id']}"
    await client.start_new("incident_orchestrator", instance_id, payload)
```

## HTTP Decision API (resume)

```python
# triggers/http_decision.py → POST /api/incidents/{id}/decision
# Body: { "action": "approved"|"rejected"|"more_info", "user_id": "...", "reason": "..." }
# → raises external event "operator_decision" on Durable instance
```

## Progress (April 20, 2026)

- [x] Escalation ownership is now preserved across the `more_info` loop: once a timeout hands review to QA, follow-up rounds stay QA-owned instead of drifting back to the operator lane
- [x] `notify_operator.py` now keeps QA-owned follow-ups in `escalated` / `awaiting_qa_manager_decision` semantics so downstream notifications and SignalR delivery continue targeting QA correctly
- [x] Focused helper coverage was added in `tests/test_incident_orchestrator_roles.py`; `python -m pytest tests/test_http_decision.py tests/test_incident_orchestrator_roles.py tests/test_notifications_api.py` passes locally
- [x] Backend evidence retrieval now incorporates the latest operator follow-up question during `more_info` rounds, so clarification requests can widen Azure AI Search retrieval without re-enabling pre-approval tool writes

## Definition of Done

- [ ] `service_bus_trigger` starts the orchestrator when a message is in the queue
- [ ] Orchestrator passes full path approved (verified locally via Azurite)
- [ ] Human approval: `waitForExternalEvent` is correctly restored after POST /decision
- [ ] Timeout 24h → escalation event is issued (test with 30-second timeout)
- [ ] `more_info` loop works (maximum 3 iterations)
- [ ] All activities record events in the `incident_events` collection
