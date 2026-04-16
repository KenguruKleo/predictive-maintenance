# T-024 · Azure Durable Functions — Workflow Orchestrator

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🔴 CRITICAL  
**Статус:** 🔜 TODO  
**Блокує:** T-029, T-033  
**Залежить від:** T-020 (Cosmos DB), T-022 (Service Bus), T-025, T-026, T-027

---

## Мета

Реалізувати stateful workflow через Azure Durable Functions (Python) з паузою на human-in-the-loop.

---

## Файли

```
backend/
  function_app.py                    # Azure Functions app entry point
  orchestrators/
    incident_orchestrator.py         # @app.orchestration_trigger — головний workflow
  activities/
    create_incident.py               # Cosmos DB: create/update incident document
    enrich_context.py                # Cosmos DB: fetch equipment + batch context
    run_agents.py                    # Azure AI Foundry: Research + Document agents
    notify_operator.py               # SignalR: push notification до React UI
    execute_decision.py              # Azure AI Foundry: Execution Agent
    finalize_audit.py                # Cosmos DB: final audit record + status=closed
  triggers/
    service_bus_trigger.py           # @app.service_bus_queue_trigger — start orchestrator
    http_decision.py                 # POST /api/incidents/{id}/decision — resume orchestrator
```

## Workflow — покроково

```python
# incident_orchestrator.py (pseudo-code)
async def incident_orchestrator(context: df.DurableOrchestrationContext):
    input = context.get_input()  # { alert_payload, incident_id }

    # Step 1: Create incident record
    incident_id = await context.call_activity("create_incident", input)

    # Step 2: Enrich context
    context_data = await context.call_activity("enrich_context", incident_id)

    # Loop for "more_info" requests
    loop_count = 0
    decision = None
    while decision not in ["approved", "rejected"] and loop_count < 3:
        # Step 3: Run agents
        ai_result = await context.call_activity("run_agents", {
            "incident_id": incident_id,
            "context": context_data,
            "loop_count": loop_count
        })

        # Step 4: Notify operator via SignalR
        await context.call_activity("notify_operator", {
            "incident_id": incident_id,
            "ai_result": ai_result
        })

        # Step 5: Wait for operator decision OR 24h timeout → escalate
        deadline = context.current_utc_datetime + timedelta(hours=24)
        decision_event = context.wait_for_external_event("operator_decision")
        timeout_event = context.create_timer(deadline)
        winner = await first([decision_event, timeout_event])

        if winner == timeout_event:
            # Escalate to QA Manager
            await context.call_activity("notify_operator", {
                "incident_id": incident_id,
                "escalation": True,
                "role": "qa-manager"
            })
            decision = None  # Keep waiting (QA manager will decide)
            # second wait with no timeout for QA manager
            decision = await context.wait_for_external_event("operator_decision")
        else:
            decision = winner  # Already a decision payload

        if decision.get("action") == "more_info":
            context_data["extra_info"] = decision.get("question")
            loop_count += 1
            decision = None  # Reset to loop

    # Step 6: Execute or close
    if decision.get("action") == "approved":
        exec_result = await context.call_activity("execute_decision", {
            "incident_id": incident_id,
            "ai_result": ai_result,
            "approver": decision.get("user_id")
        })
    else:
        await context.call_activity("create_incident", {
            "incident_id": incident_id,
            "status": "rejected",
            "rejection_reason": decision.get("reason")
        })

    # Step 7: Finalize audit record
    await context.call_activity("finalize_audit", {
        "incident_id": incident_id,
        "decision": decision
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

## Definition of Done

- [ ] `service_bus_trigger` стартує orchestrator при повідомленні в черзі
- [ ] Orchestrator проходить повний шлях approved (перевірено локально через Azurite)
- [ ] Human approval: `waitForExternalEvent` коректно відновлюється після POST /decision
- [ ] Timeout 24h → escalation event видається (тест з 30-секундним timeout)
- [ ] `more_info` loop працює (максимум 3 ітерації)
- [ ] Всі activities записують події в `incident_events` collection
