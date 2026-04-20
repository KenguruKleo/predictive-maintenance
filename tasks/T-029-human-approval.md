# T-029 · Human Approval Mechanism (waitForExternalEvent + Decision API)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🔴 CRITICAL  
**Статус:** ✅ DONE  
**Блокує:** —  
**Залежить від:** T-024 (Durable orchestrator), T-031 (backend API)

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
- [x] Live authorized proof is now confirmed in Azure through the deployed frontend: both `rejected` and `more_info` operator actions succeeded via the same protected `POST /api/incidents/{id}/decision` endpoint after Entra role assignment and delegated token setup were corrected
- [x] T-029 is now treated as closed; the former SignalR notification follow-up was handled separately in T-030 so this task stays scoped to the protected decision API + Durable resume flow

## Definition of Done

- [x] `POST /decision` з valid operator token → 202 Accepted, Durable instance resumes
- [x] `POST /decision` з невалідною роллю → 403 Forbidden
- [x] `action: "more_info"` → incident status → `awaiting_agents`, orchestrator loops
- [x] `action: "rejected"` → incident status → `rejected`, orchestrator closes
- [x] Decision записується в `incident_events` collection

> SignalR notification scope and bell UX were finalized in [T-030](./T-030-signalr.md); T-029 remains limited to the protected decision API + Durable resume path.
