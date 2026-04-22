# T-054 · Agent Recommendation Visibility (HITL + Lists + Analytics)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟠 HIGH  
**Статус:** 🔜 TODO  
**Залежить від:** T-033 (frontend-approval, DONE), T-034 (manager/auditor views, DONE), T-029 (decision API, DONE)

---

## Мета

Показувати `agent_recommendation` (APPROVE / REJECT) скрізь, де оператор або аналітик бачить інцидент — в approval UI, у списках, в audit trail, в аналітиці QA Manager. Це дозволяє:

1. **Оператору** одразу бачити що рекомендує AI ще до натискання кнопки;
2. **QA Manager / Auditor** аналізувати паттерни розбіжності між AI і людиною;
3. **IT Admin** відстежувати якість моделі і дрейф рекомендацій у часі.

---

## Зміни

### Backend

#### 1. `backend/triggers/http_decision.py`

Прийняти нові поля в request body:

```python
# Нові optional поля
body = {
    "action": "approved",          # existing
    "reason": "...",               # existing
    "agent_recommendation": "APPROVE",   # NEW — з DocumentAgentOutput
    "operator_agrees_with_agent": True,  # NEW — обчислити: action=="approved" == (agent_rec=="APPROVE")
    "work_order_draft": {...},     # NEW (T-052)
    "audit_entry_draft": {...},    # NEW (T-052)
}
```

Обчислення `operator_agrees_with_agent` (якщо не передано явно):
```python
agent_rec = body.get("agent_recommendation")
if agent_rec:
    decision_positive = body["action"] == "approved"
    agent_positive = agent_rec == "APPROVE"
    operator_agrees = decision_positive == agent_positive
else:
    operator_agrees = None  # agent recommendation not available (BLOCKED state)
```

Зберегти в event при `raise_event`:
```python
event_data = {
    "action": action,
    "user_id": caller_id,
    "role": ...,
    "reason": ...,
    "agent_recommendation": agent_rec,          # NEW
    "operator_agrees_with_agent": operator_agrees,  # NEW
    ...
}
```

#### 2. `backend/activities/finalize_audit.py`

Додати до `patch_incident_by_id` і до audit doc:

```python
# In patch_operations:
{"op": "set", "path": "/agentRecommendation", "value": decision.get("agent_recommendation")},
{"op": "set", "path": "/operatorAgreesWithAgent", "value": decision.get("operator_agrees_with_agent")},

# In audit_doc:
"agentRecommendation": decision.get("agent_recommendation"),
"operatorAgreesWithAgent": decision.get("operator_agrees_with_agent"),
```

#### 3. `backend/triggers/http_stats.py`

Додати до `recent_decisions` items:

```python
{
    ...existing fields...,
    "agent_recommendation": inc.get("agentRecommendation"),          # NEW
    "operator_agrees_with_agent": inc.get("operatorAgreesWithAgent"), # NEW
}
```

#### 4. `backend/activities/run_foundry_agents.py` / normalized result

Переконатись, що `agent_recommendation` із `DocumentAgentOutput` зберігається в `ai_analysis` в Cosmos:

```python
# У normalized result:
normalized["agent_recommendation"] = raw_output.get("agent_recommendation")  # "APPROVE" | "REJECT"
```

---

### Frontend

#### 5. `frontend/src/types/incident.ts`

```typescript
// In AiAnalysis:
agent_recommendation?: "APPROVE" | "REJECT";

// In Incident (top-level):
agent_recommendation?: "APPROVE" | "REJECT";
operator_agrees_with_agent?: boolean | null;

// In LastDecision:
agent_recommendation?: "APPROVE" | "REJECT";
operator_agrees_with_agent?: boolean | null;
```

#### 6. `frontend/src/types/stats.ts`

```typescript
export interface RecentDecision {
  ...existing fields...,
  agent_recommendation?: "APPROVE" | "REJECT";   // NEW
  operator_agrees_with_agent?: boolean | null;    // NEW
}
```

#### 7. `frontend/src/components/Approval/ApprovalPanel.tsx` (або DecisionPackage.tsx)

Додати виразний **AI Verdict** badge в decision package — над кнопками Approve/Reject:

```
┌──────────────────────────────────────────────────────────────┐
│  AI ANALYSIS                                                 │
│  Risk: 🟠 MEDIUM   Confidence: ████░░ 84%                   │
│                                                              │
│  AI RECOMMENDATION                                           │
│  ┌────────────────────────────────────────────────────┐     │
│  │  ✅  APPROVE — дія рекомендована                   │     │   ← зелений якщо APPROVE
│  │  ⛔  REJECT  — ложно-позитивний / не потрібна дія  │     │   ← помаранчевий якщо REJECT
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  [Approve]  [Reject]  [More info]                           │
└──────────────────────────────────────────────────────────────┘
```

Новий компонент: `AgentRecommendationBadge.tsx`

```tsx
interface Props {
  recommendation: "APPROVE" | "REJECT";
  confidence: number;
}
// Renders a prominent banner: green for APPROVE, amber for REJECT
// Shows rationale snippet from recommendation field
```

При Approve/Reject — передати `agent_recommendation` у тілі `POST /api/incidents/{id}/decision`.

#### 8. `frontend/src/components/IncidentList/IncidentTable.tsx`

Додати колонку **AI** після Severity для закритих інцидентів (closed / rejected):

```
ID | Equipment | Title | Severity | AI | Outcome | Batch | Date
```

Колонка AI показує:
- `✅ APPROVE` / `⛔ REJECT` — що рекомендував агент
- Якщо `operator_agrees_with_agent === false` — додатковий індикатор `⚡ Override`
- Якщо `agent_recommendation` недоступний — `—`

Колонка **Outcome** замість Status для history view (closed incidents):
- `Approved ✓` / `Rejected ✗` — рішення оператора
- Якщо `operator_agrees_with_agent === false` → tooltip "Operator overrode AI recommendation"

#### 9. `frontend/src/pages/IncidentHistoryPage.tsx`

CSV export — додати два нові стовпці:

```typescript
{ header: "AI Recommendation", value: (i) => i.ai_analysis?.agent_recommendation ?? i.agent_recommendation ?? "" },
{ header: "Operator Agrees With AI", value: (i) => i.operator_agrees_with_agent != null ? String(i.operator_agrees_with_agent) : "" },
```

#### 10. `frontend/src/pages/AuditTrailPage.tsx`

Кожен рядок аудит-трейлу для закритого інциденту показує:

```
INC-2026-0049 | 22 Apr 2026 | jane.smith (Operator) | Approved
              AI said: ✅ APPROVE → Operator: ✅ Approved   [Agreement ✓]

INC-2026-0051 | 22 Apr 2026 | john.doe (QA Manager) | Rejected
              AI said: ✅ APPROVE → Operator: ✗ Rejected   [Override ⚡]
```

Новий компонент: `AiVsHumanBadge.tsx`

```tsx
interface Props {
  agentRecommendation?: "APPROVE" | "REJECT";
  operatorDecision: "approved" | "rejected";
  operatorAgreesWithAgent?: boolean | null;
}
// agreement → green checkmark
// override  → amber lightning bolt + tooltip "Human overrode AI"
```

#### 11. `frontend/src/components/Manager/RecentDecisions.tsx`

Розширити `RecentDecision` widget:

До кожного рядка додати:
```
INC-0049  jane.smith (Operator)  84%  ✅→✅ Agreed      2 min ago
INC-0051  john.doe (QA Mgr)      62%  ✅→✗ Override     8 min ago
INC-0048  alice.m  (Operator)    —    BLOCKED→✅ Approved  1h ago
```

Легенда: `✅→✅` = AI APPROVE, оператор Approved. `✅→✗` = AI APPROVE, оператор Rejected (override).

Додати маленький summary KPI під таблицею:
```
AI–Human agreement rate (last 30 decisions): 78%
```

---

## Wireframe — IncidentTable з AI-колонкою

```
┌──────────┬───────────┬────────────────────────────┬──────────┬─────────┬──────────────┐
│ ID       │ Equipment │ Title                      │ Severity │ AI      │ Outcome      │
├──────────┼───────────┼────────────────────────────┼──────────┼─────────┼──────────────┤
│ INC-0049 │ GR-204    │ Impeller Speed Deviation   │ 🟠 MAJOR │ APPROVE │ ✅ Approved  │
│ INC-0051 │ MX-102    │ Temperature Excursion      │ 🔴 CRIT  │ APPROVE │ ✗ Rejected ⚡│
│ INC-0048 │ PK-101    │ Pressure Drop              │ 🟡 MOD   │ REJECT  │ ✅ Approved ⚡│
│ INC-0047 │ GR-204    │ Vibration Anomaly          │ 🟠 MAJOR │ —       │ ✅ Approved  │
└──────────┴───────────┴────────────────────────────┴──────────┴─────────┴──────────────┘
                                                               ⚡ = override (disagree)
```

---

## Нові компоненти

| Компонент | Де використовується |
|---|---|
| `AgentRecommendationBadge.tsx` | ApprovalPanel (HITL) |
| `AiVsHumanBadge.tsx` | AuditTrailPage, IncidentTable |

---

## Definition of Done

**Backend:**
- [ ] `http_decision.py` приймає `agent_recommendation` + обчислює `operator_agrees_with_agent`
- [ ] `finalize_audit.py` зберігає обидва поля в Cosmos incident + audit event
- [ ] `run_foundry_agents.py` / normalized result зберігає `agent_recommendation` в `ai_analysis`
- [ ] `http_stats.py` включає `agent_recommendation` + `operator_agrees_with_agent` у `recent_decisions`

**Frontend:**
- [ ] `AgentRecommendationBadge` показується в ApprovalPanel — виразно, над кнопками
- [ ] `agent_recommendation` передається у тілі `POST /decision`
- [ ] `IncidentTable` показує AI-колонку + Override індикатор
- [ ] `IncidentHistoryPage` CSV export включає нові поля
- [ ] `AuditTrailPage` показує `AiVsHumanBadge` per row
- [ ] `RecentDecisions` widget показує AI→Human pattern + agreement rate KPI
- [ ] `types/incident.ts` та `types/stats.ts` оновлено

---

## Пріоритет і scope

🟠 HIGH — ця фіча пряма демонстрація цінності AI: "ось що порадила система, ось що вирішив оператор". Критично для hackathon demo story та для post-demo аналітики якості рекомендацій.
