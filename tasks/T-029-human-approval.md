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
  "reason": "Optional justification",
  "question": "What was the batch moisture at T+0?"  // only for more_info
}

Response 202:
{
  "status": "decision_received",
  "instance_id": "durable-INC-2026-0001"
}
```

> Примітка: caller identity і app role беруться з JWT claims або local mock headers (`USE_LOCAL_MOCK_AUTH=true`). Legacy/e2e payload fields `user_id` / `role` можуть бути присутні, але backend не довіряє їм як authoritative source.

---

## Logic

```python
# backend/triggers/http_decision.py

@app.route(route="incidents/{incident_id}/decision", methods=["POST"])
@app.durable_client_input(client_name="client")
async def record_decision(req: func.HttpRequest, client: df.DurableOrchestrationClient, incident_id: str):
  # 1. Auth: verify user has Operator or QAManager app role
  roles = get_caller_roles(req)
  require_any_role(roles, ["Operator", "QAManager"])
  caller_id = get_caller_id(req)
  workflow_role = map_role(get_primary_role(roles))

    # 2. Parse body
    body = req.get_json()
    validate_decision_body(body)

  # 3. Persist decision to approval-tasks + incidents + incident_events
  decision = {
    "action": body["action"],
    "user_id": caller_id,
    "role": workflow_role,
    "reason": body.get("reason", ""),
    "question": body.get("question", ""),
  }
  _record_decision(incident_id, decision, now_iso)

  # 4. Resume Durable orchestrator
  await client.raise_event(instance_id, "operator_decision", decision)

  return func.HttpResponse(status_code=202, body=json.dumps({
    "status": "decision_received",
    "instance_id": instance_id,
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
    auth.py          # get_caller_roles(), get_caller_id(), require_any_role()
```

## Progress (18 квітня 2026)

- [x] Visible AI replies are now persisted into `incident_events` for both the initial recommendation and `more_info` follow-ups via `backend/activities/notify_operator.py`
- [x] `/api/incidents/{id}/events` now preserves transcript metadata (`round`, `message_kind`) needed by the approval chat UI
- [x] Backend slice passes `python -m py_compile` for the touched files and `python -m pytest tests/test_smoke.py`

## Progress (20 квітня 2026)

- [x] `backend/triggers/http_decision.py` now enforces RBAC via `get_caller_roles()` / `require_any_role()` and derives caller identity from auth instead of trusting body-supplied `user_id`
- [x] Focused backend coverage was added in `tests/test_http_decision.py`; `python -m pytest tests/test_http_decision.py tests/test_notifications_api.py` passes locally
- [x] Live stale-state issue for `INC-2026-0019` was diagnosed: incident stayed in `pending_approval` while Durable status returned `null`; `scripts/recover_live_incident.py --skip-more-info-replay --yes` recreated a fresh `durable-INC-2026-0019` instance and `/decision` succeeded on that recovered instance
- [x] Post-deploy unauthorized smoke check now returns `401 Authentication required` from the live Function App, confirming the RBAC hardening is active in Azure
- [ ] Full bearer-token approval proof in Azure is still blocked from the current CLI session because `az account get-access-token --scope api://38843d08-f211-4445-bcef-a07d383f2ee6/.default` requires tenant consent for the Azure CLI app

## Definition of Done

- [ ] `POST /decision` з valid operator token → 202 Accepted, Durable instance resumes
- [x] `POST /decision` з невалідною роллю → 403 Forbidden
- [ ] `action: "more_info"` → incident status → `awaiting_agents`, orchestrator loops
- [ ] `action: "rejected"` → incident status → `rejected`, orchestrator closes
- [x] Decision записується в `incident_events` collection
- [ ] SignalR notification відправляється при зміні статусу
