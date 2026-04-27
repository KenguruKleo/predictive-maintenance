# T-053 · Alert feedback loop

← [Backlog](../04-action-plan.md)

> **Purpose:** When the operator rejects the incident (Reject), the system sends an async feedback event to the alerting system (SCADA/MES). This allows the signal source to learn from false positive cases and better filter noise.

---

## Context

Every `rejected` decision is a potential false positive from SCADA/MES. If such cases accumulate, the source system can adapt (threshold adjustment, model retraining, etc.). Feedback does not block the main flow — fire-and-forget with a basic retry.

---

## Affected components

- `backend/activities/` — new activity `send_alert_feedback.py`
- `backend/` — `local.settings.json` + Bicep: `ALERT_FEEDBACK_URL` env var (optional)
- `backend/orchestrators/deviation_orchestrator.py` — call `send_alert_feedback` after `close_incident` when rejected
- `backend/shared/cosmos_service.py` or `incident_events` — feedback event record

---

## Flow

```
operator → Reject
     │
     ▼
close_incident  →  Cosmos: status = "rejected"
     │
     ▼
send_alert_feedback (Durable Activity, non-blocking)
     │
├─ if ALERT_FEEDBACK_URL is set:
     │    POST {ALERT_FEEDBACK_URL}
     │    {
     │      "source_alert_id": "...",
     │      "incident_id": "...",
     │      "outcome": "rejected",
     │      "operator_agrees_with_agent": true/false,
     │      "timestamp": "...",
     │      "equipment_id": "...",
     │      "alert_type": "..."
     │    }
     │    retry: 3 attempts, exponential backoff
     │
└─ regardless of the result:
          incident_events ← { event_type: "feedback_sent", status: "ok"|"skipped"|"failed" }
```

---

## Configuration

| Env var | Default | Description |
|---|---|---|
| `ALERT_FEEDBACK_URL` | `""` (empty) | URL for POST feedback. If empty - feedback skipped, only local event is recorded |
| `ALERT_FEEDBACK_TIMEOUT_S` | `5` | HTTP timeout for feedback call |

---

## Feedback payload schema

```json
{
  "source_alert_id": "ALERT-2026-0049",
  "incident_id": "INC-2026-0049",
  "outcome": "rejected",
  "operator_agrees_with_agent": true,
  "agent_recommendation": "REJECT",
  "equipment_id": "GR-204",
  "alert_type": "vibration_anomaly",
  "confidence": 0.84,
  "timestamp": "2026-04-22T10:15:30Z",
  "sentinel_version": "1.0"
}
```

`operator_agrees_with_agent`:
- `true` — the operator rejected and the agent also recommended REJECT (false positive confirmation)
- `false` — the operator rejected, but the agent recommended APPROVE (overrode operator)

---

## UI

- The incident timeline (`incident_events`) shows the event: `Feedback sent to monitoring system` / `Feedback skipped (no URL configured)` / `Feedback failed (retries exhausted)`.
- Auditor sees in the agent telemetry view.

---

## Security

- `ALERT_FEEDBACK_URL` is stored in Azure Key Vault (not `local.settings.json` in production).
- Payload contains no PII, only technical identifiers and metrics.
- Non-blocking: the error of sending feedback does not affect the status of the incident.

---

## Definition of Done

- [ ] Activity `send_alert_feedback` is implemented in `backend/activities/`
- [ ] Called from `deviation_orchestrator` after `close_incident` at `rejected`
- [ ] If `ALERT_FEEDBACK_URL` is empty — feedback skipped, event is recorded as `"status": "skipped"`
- [ ] Retry: 3 attempts with exponential backoff
- [ ] `incident_events` receives a feedback event regardless of the result
- [ ] Bicep: `ALERT_FEEDBACK_URL` as Key Vault secret reference (optional, default empty)
- [ ] Frontend: feedback status is displayed in the incident timeline

---

## Priority

🟡 MEDIUM — does not block the demo, but is important for the production learning loop.
