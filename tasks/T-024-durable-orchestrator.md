# T-024 · Azure Durable Functions — Workflow Orchestrator

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🔴 CRITICAL  
**Статус:** ✅ DONE (18-19 квітня 2026)  
**Блокує:** T-029, T-033  
**Залежить від:** T-020 (Cosmos DB), T-022 (Service Bus), T-025, T-026, T-027

---

## Мета

Реалізувати stateful workflow через Azure Durable Functions (Python) з паузою на human-in-the-loop.  
Агентна логіка (Research → Document pipeline) делегована Foundry Connected Agents — **ADR-002** (дивись [02-architecture §8.10b](../02-architecture.md#810b-adr-002-foundry-connected-agents-vs-ручна-оркестрація)).

---

## Архітектурне рішення (ADR-002)

> **Ключова зміна від початкового плану:**  
> Замість окремих activities `run_research_agent` + `run_document_agent` — одна activity `run_foundry_agents`.  
> Foundry Orchestrator Agent (Connected Agents pattern) керує Research → Document pipeline нативно.  
> `more_info` loop count та reasoning iterations — конфігуруються через `max_iterations` у Foundry та `MAX_MORE_INFO_ROUNDS` env var.

---

## Файли

```
backend/
  function_app.py                    # Azure Functions app entry point
  orchestrators/
    incident_orchestrator.py         # @app.orchestration_trigger — головний workflow
  activities/
    enrich_context.py                # Cosmos DB: fetch equipment + batch context
    run_foundry_agents.py            # Foundry: Orchestrator Agent (Research + Document via Connected Agents)
    notify_operator.py               # SignalR: push notification до React UI
    run_execution_agent.py           # Foundry: Execution Agent (після approval)
    close_incident.py                # Cosmos DB: set status=rejected
    finalize_audit.py                # Cosmos DB: final audit record + status=closed
  triggers/
    service_bus_trigger.py           # @app.service_bus_queue_trigger — start orchestrator
    http_decision.py                 # POST /api/incidents/{id}/decision — resume orchestrator
```

## Workflow — покроково

```python
# incident_orchestrator.py (pseudo-code)
MAX_MORE_INFO_ROUNDS = int(os.getenv("MAX_MORE_INFO_ROUNDS", "3"))

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

## Progress (20 квітня 2026)

- [x] Escalation ownership is now preserved across the `more_info` loop: once a timeout hands review to QA, follow-up rounds stay QA-owned instead of drifting back to the operator lane
- [x] `notify_operator.py` now keeps QA-owned follow-ups in `escalated` / `awaiting_qa_manager_decision` semantics so downstream notifications and SignalR delivery continue targeting QA correctly
- [x] Focused helper coverage was added in `tests/test_incident_orchestrator_roles.py`; `python -m pytest tests/test_http_decision.py tests/test_incident_orchestrator_roles.py tests/test_notifications_api.py` passes locally

## Definition of Done

- [ ] `service_bus_trigger` стартує orchestrator при повідомленні в черзі
- [ ] Orchestrator проходить повний шлях approved (перевірено локально через Azurite)
- [ ] Human approval: `waitForExternalEvent` коректно відновлюється після POST /decision
- [ ] Timeout 24h → escalation event видається (тест з 30-секундним timeout)
- [ ] `more_info` loop працює (максимум 3 ітерації)
- [ ] Всі activities записують події в `incident_events` collection
