# T-052 · Editable WO / Audit entry forms in HITL UI

← [Backlog](../04-action-plan.md)

> **Мета:** Показувати WO draft та audit entry draft як редаговані multi-line форми в decision package UI. Pre-filled від Document Agent; operator/QA може редагувати перед Approve. При BLOCKED-стані (agent failure) — форми порожні, operator заповнює вручну (обов'язково для Approve).

---

## Контекст

Після approval Execution Agent створює реальні записи в CMMS і QMS. Payload для цих calls береться з форм, які оператор переглянув і підтвердив — це:
1. гарантує що дані в зовнішніх системах відповідають рішенню оператора;
2. вирішує кейс BLOCKED (agent fail = zero confidence) — оператор може вручну внести WO і audit entry, не блокуючи процес;
3. дозволяє QA Manager коригувати drafts при ескалації.

---

## Дані flow (важливо для GxP)

```
DocumentAgentOutput
  └── ai_analysis.work_order_draft    ← AI оригінал (ЗБЕРІГАЄТЬСЯ незмінним в Cosmos)
  └── ai_analysis.audit_entry_draft  ← AI оригінал (ЗБЕРІГАЄТЬСЯ незмінним в Cosmos)
           ↓ pre-fills editable form
      [frontend: operator редагує або заповнює вручну при BLOCKED]
           ↓ POST /api/incidents/{id}/decision
      body.work_order_draft / body.audit_entry_draft  ← operator-confirmed версія
           ↓ зберігається окремо
      incident.operatorWorkOrderDraft     ← operator-final
      incident.operatorAuditEntryDraft    ← operator-final
           ↓
      run_execution_agent читає operator версію, НЕ ai_analysis
```

**Обидві версії залишаються:** `ai_analysis.work_order_draft` = що запропонував AI; `operatorWorkOrderDraft` = що підтвердив/змінив оператор. Auditor бачить обидва — це є документальний trail змін для GMP.

## Affected components

- `frontend/src/components/Approval/` — `WorkOrderPreview.tsx` / `AuditEntryPreview.tsx` → зробити editable (або замінити на нові компоненти)
- `backend/triggers/http_decision.py` — прийняти `work_order_draft` та `audit_entry_draft` у тілі; зберегти як `operatorWorkOrderDraft` / `operatorAuditEntryDraft` на incident
- `backend/activities/run_execution_agent.py` — читати `operatorWorkOrderDraft` / `operatorAuditEntryDraft` замість re-генерації через GPT-4o

---

## UI поведінка

| Стан агента | WO draft | Audit entry draft | Approve доступний |
|---|---|---|---|
| NORMAL (conf ≥ 0.7) | Pre-filled від Document Agent, editable | Pre-filled від Document Agent, editable | Так, без додаткових вимог |
| LOW_CONFIDENCE | Pre-filled, editable | Pre-filled, editable | Так, + mandatory comment |
| BLOCKED (agent fail) | Порожній, **обов'язковий** | Порожній, **обов'язковий** | Тільки після заповнення |

**Доступ до редагування:**
- `operator`, `qa-manager` — може редагувати
- `maint-tech`, `auditor`, `it-admin` — read-only

**UI елементи:**
- `<textarea>` або structured form з мінімальними полями: `description`, `priority` (WO) та `deviation_type`, `gmp_clause` (audit)
- Кнопка Approve disabled якщо BLOCKED + форми порожні
- Hint text в порожніх полях: "Introduce work order description manually (AI was unable to generate a recommendation)"

---

## Backend changes

### `POST /api/incidents/{id}/decision`

Нові поля в request body:
```json
{
  "decision": "approved",
  "comment": "...",
  "work_order_draft": {
    "type": "corrective_maintenance",
    "priority": "urgent",
    "description": "..."
  },
  "audit_entry_draft": {
    "deviation_type": "Equipment",
    "gmp_clause": "21 CFR 211.68",
    "description": "..."
  }
}
```

- Якщо `decision == "approved"`: `work_order_draft` та `audit_entry_draft` обов'язкові (validation).
- Якщо `decision == "rejected"`: поля ігноруються.
- Backend зберігає `operator_edited_draft` у `approval-tasks` → Durable читає при виклику `run_execution_agent`.

### `run_execution_agent.py`

- Читає `work_order_draft` та `audit_entry_draft` з `approval-tasks` container (operator-edited версія).
- Більше **не генерує** payload самостійно з Document Agent output.

---

## Audit trail

Поля у `finalize_audit`:
- `human_override_text` — operator-edited WO/audit drafts (якщо відрізняються від agent draft, або якщо BLOCKED)
- `human_override = true` якщо оператор змінив agent draft або заповнив вручну

---

## Definition of Done

- [ ] WO draft та audit entry draft відображаються як редаговані поля в approval UI
- [ ] Pre-filled від Document Agent у нормальному сценарії
- [ ] Порожні та обов'язкові при BLOCKED
- [ ] Approve disabled якщо BLOCKED + порожні поля
- [ ] Поля read-only для maint-tech, auditor, it-admin
- [ ] Backend зберігає `operatorWorkOrderDraft` + `operatorAuditEntryDraft` окремо від `ai_analysis` (AI оригінал залишається незмінним)
- [ ] `run_execution_agent` читає `operatorWorkOrderDraft` / `operatorAuditEntryDraft`, більше не генерує через GPT-4o
- [ ] `human_override_text` записується у `finalize_audit` якщо оператор змінив або заповнив вручну

---

## Пріоритет

🟠 HIGH — блокує повноцінний BLOCKED-сценарій та GxP-коректність payload для зовнішніх систем.
