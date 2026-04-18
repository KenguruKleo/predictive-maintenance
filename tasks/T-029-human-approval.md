# T-029 · Human Approval Mechanism (waitForExternalEvent + SignalR + Decision API)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🔴 CRITICAL  
**Статус:** 🟡 IN PROGRESS  
**Блокує:** T-033 (approval UX), demo flow  
**Залежить від:** T-024 (Durable orchestrator), T-030 (SignalR), T-031 (backend API)

---

## Мета

Реалізувати human-in-the-loop механізм: operator натискає кнопку в UI → POST /api/incidents/{id}/decision → Durable orchestrator відновлюється.

---

## Endpoint

```
POST /api/incidents/{incident_id}/decision
Authorization: Bearer {token}  (operator або qa-manager role required)

Body:
{
  "action": "approved" | "rejected" | "more_info",
  "user_id": "ivan.petrenko",
  "reason": "Optional justification",
  "question": "What was the batch moisture at T+0?"  // only for more_info
}

Response 200:
{
  "incident_id": "INC-2026-0001",
  "decision_recorded": true,
  "new_status": "approved" | "rejected" | "awaiting_agents"
}
```

---

## Logic

```python
# backend/triggers/http_decision.py

@app.route(route="incidents/{incident_id}/decision", methods=["POST"])
@app.durable_client_input(client_name="client")
async def record_decision(req: func.HttpRequest, client: df.DurableOrchestrationClient, incident_id: str):
    # 1. Auth: verify user has operator or qa-manager role
    user = get_current_user(req)
    require_role(user, ["operator", "qa-manager"])

    # 2. Parse body
    body = req.get_json()
    validate_decision_body(body)

    # 3. Log decision event to Cosmos DB
    await log_incident_event(incident_id, {
        "event_type": "operator_decision",
        "action": body["action"],
        "user_id": body["user_id"],
        "reason": body.get("reason"),
        "timestamp": datetime.utcnow().isoformat()
    })

    # 4. Update incident status in Cosmos DB
    new_status = {
        "approved": "executing",
        "rejected": "rejected",
        "more_info": "awaiting_agents"
    }[body["action"]]
    await update_incident_status(incident_id, new_status)

    # 5. Resume Durable orchestrator
    instance_id = f"durable-{incident_id}"
    await client.raise_event(instance_id, "operator_decision", body)

    # 6. Notify via SignalR (status change to manager view)
    await notify_signalr(f"incident_updated:{incident_id}:{new_status}")

    return func.HttpResponse(status_code=200, body=json.dumps({
        "incident_id": incident_id,
        "decision_recorded": True,
        "new_status": new_status
    }))
```

---

## Timeout + Escalation

Реалізовано в Durable orchestrator (T-024):
- 24-годинний timer → якщо не було рішення → SignalR push до qa-manager role
- QA Manager бачить escalation badge на incident
- Той самий `/decision` endpoint (qa-manager роль)

---

## Files

```
backend/
  triggers/
    http_decision.py
  utils/
    auth.py          # get_current_user(), require_role()
```

## Progress (18 квітня 2026)

- [x] Visible AI replies are now persisted into `incident_events` for both the initial recommendation and `more_info` follow-ups via `backend/activities/notify_operator.py`
- [x] `/api/incidents/{id}/events` now preserves transcript metadata (`round`, `message_kind`) needed by the approval chat UI
- [x] Backend slice passes `python -m py_compile` for the touched files and `python -m pytest tests/test_smoke.py`

## Definition of Done

- [ ] `POST /decision` з valid operator token → 200, Durable instance resumes
- [ ] `POST /decision` з невалідною роллю → 403 Forbidden
- [ ] `action: "more_info"` → incident status → `awaiting_agents`, orchestrator loops
- [ ] `action: "rejected"` → incident status → `rejected`, orchestrator closes
- [ ] Decision записується в `incident_events` collection
- [ ] SignalR notification відправляється при зміні статусу
