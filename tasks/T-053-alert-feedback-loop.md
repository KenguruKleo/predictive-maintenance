# T-053 · Alert feedback loop

← [Backlog](../04-action-plan.md)

> **Мета:** Коли оператор відхиляє incident (Reject), система надсилає async feedback-подію до alerting-системи (SCADA/MES). Це дозволяє джерелу сигналів навчатись на false positive кейсах і краще фільтрувати шум.

---

## Контекст

Кожен `rejected` decision — потенційний false positive від SCADA/MES. Якщо таких кейсів накопичується, система-джерело може адаптуватись (threshold adjustment, model retraining тощо). Зворотній зв'язок не блокує основний flow — fire-and-forget із базовим retry.

---

## Affected components

- `backend/activities/` — нова activity `send_alert_feedback.py`
- `backend/` — `local.settings.json` + Bicep: `ALERT_FEEDBACK_URL` env var (optional)
- `backend/orchestrators/deviation_orchestrator.py` — виклик `send_alert_feedback` після `close_incident` при rejected
- `backend/shared/cosmos_service.py` або `incident_events` — запис feedback event

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
     ├─ якщо ALERT_FEEDBACK_URL задано:
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
     └─ незалежно від результату:
          incident_events ← { event_type: "feedback_sent", status: "ok"|"skipped"|"failed" }
```

---

## Configuration

| Env var | Default | Опис |
|---|---|---|
| `ALERT_FEEDBACK_URL` | `""` (empty) | URL для POST feedback. Якщо порожній — feedback skipped, лише local event записується |
| `ALERT_FEEDBACK_TIMEOUT_S` | `5` | HTTP timeout для feedback call |

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
- `true` — оператор відхилив і агент теж рекомендував REJECT (підтвердження false positive)
- `false` — оператор відхилив, але агент рекомендував APPROVE (оператор overrode)

---

## UI

- В incident timeline (`incident_events`) показується подія: `Feedback sent to monitoring system` / `Feedback skipped (no URL configured)` / `Feedback failed (retries exhausted)`.
- Auditor бачить у agent telemetry view.

---

## Безпека

- `ALERT_FEEDBACK_URL` зберігається в Azure Key Vault (не в `local.settings.json` у production).
- Payload не містить PII, тільки технічні ідентифікатори та метрики.
- Non-blocking: помилка відправки feedback не впливає на стан incident.

---

## Definition of Done

- [ ] Activity `send_alert_feedback` реалізована в `backend/activities/`
- [ ] Викликається з `deviation_orchestrator` після `close_incident` при `rejected`
- [ ] Якщо `ALERT_FEEDBACK_URL` порожній — feedback skipped, event записується як `"status": "skipped"`
- [ ] Retry: 3 спроби з exponential backoff
- [ ] `incident_events` отримує feedback event незалежно від результату
- [ ] Bicep: `ALERT_FEEDBACK_URL` як Key Vault secret reference (optional, default empty)
- [ ] Frontend: feedback status відображається в incident timeline

---

## Пріоритет

🟡 MEDIUM — не блокує demo, але важливий для production learning loop.
