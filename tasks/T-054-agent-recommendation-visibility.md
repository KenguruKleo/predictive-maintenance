# T-054 · Agent Recommendation Visibility (HITL + Lists + Analytics)

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🟠 HIGH
**Status:** 🔜 TODO
**Depends on:** T-033 (frontend-approval, DONE), T-034 (manager/auditor views, DONE), T-029 (decision API, DONE)

---

## Goal

Show `agent_recommendation` (APPROVE / REJECT) wherever the operator or analyst sees the incident — in the approval UI, in lists, in the audit trail, in QA Manager analytics. This allows:

1. The **operator** can immediately see what the AI ​​recommends even before pressing the button;
2. **QA Manager / Auditor** to analyze patterns of disagreement between AI and human;
3. **IT Admin** monitor the quality of the model and the drift of recommendations over time.

---

## Changes

### Backend

#### 1. `backend/triggers/http_decision.py`

Accept new fields in request body:

```python
# New optional fields
body = {
    "action": "approved",          # existing
    "reason": "...",               # existing
"agent_recommendation": "APPROVE", # NEW — from DocumentAgentOutput
"operator_agrees_with_agent": True, # NEW — calculate: action=="approved" == (agent_rec=="APPROVE")
    "work_order_draft": {...},     # NEW (T-052)
    "audit_entry_draft": {...},    # NEW (T-052)
}
```

Calculation of `operator_agrees_with_agent` (if not explicitly passed):
```python
agent_rec = body.get("agent_recommendation")
if agent_rec:
    decision_positive = body["action"] == "approved"
    agent_positive = agent_rec == "APPROVE"
    operator_agrees = decision_positive == agent_positive
else:
    operator_agrees = None  # agent recommendation not available (BLOCKED state)
```

Save in event at `raise_event`:
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

Add to `patch_incident_by_id` and to the audit doc:

```python
# In patch_operations:
{"op": "set", "path": "/agentRecommendation", "value": decision.get("agent_recommendation")},
{"op": "set", "path": "/operatorAgreesWithAgent", "value": decision.get("operator_agrees_with_agent")},

# In audit_doc:
"agentRecommendation": decision.get("agent_recommendation"),
"operatorAgreesWithAgent": decision.get("operator_agrees_with_agent"),
```

#### 3. `backend/triggers/http_stats.py`

Add to `recent_decisions` items:

```python
{
    ...existing fields...,
    "agent_recommendation": inc.get("agentRecommendation"),          # NEW
    "operator_agrees_with_agent": inc.get("operatorAgreesWithAgent"), # NEW
}
```

#### 4. `backend/activities/run_foundry_agents.py` / normalized result

Make sure `agent_recommendation` of `DocumentAgentOutput` is stored in `ai_analysis` in Cosmos:

```python
# In the normalized result:
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

#### 7. `frontend/src/components/Approval/ApprovalPanel.tsx` (or DecisionPackage.tsx)

Add an expressive **AI Verdict** badge to the decision package — above the Approve/Reject buttons:

```
┌──────────────────────────────────────────────────────────────┐
│  AI ANALYSIS                                                 │
│  Risk: 🟠 MEDIUM   Confidence: ████░░ 84%                   │
│                                                              │
│  AI RECOMMENDATION                                           │
│  ┌────────────────────────────────────────────────────┐     │
│ │ ✅ APPROVE — the action is recommended │ │ ← green if APPROVE
│ │ ⛔ REJECT — false positive / no action required │ │ ← orange if REJECT
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  [Approve]  [Reject]  [More info]                           │
└──────────────────────────────────────────────────────────────┘
```

New component: `AgentRecommendationBadge.tsx`

```tsx
interface Props {
  recommendation: "APPROVE" | "REJECT";
  confidence: number;
}
// Renders a prominent banner: green for APPROVE, amber for REJECT
// Shows rationale snippet from recommendation field
```

When Approve/Reject — pass `agent_recommendation` in the body `POST /api/incidents/{id}/decision`.

#### 8. `frontend/src/components/IncidentList/IncidentTable.tsx`

Add column **AI** after Severity for closed incidents (closed / rejected):

```
ID | Equipment | Title | Severity | AI | Outcome | Batch | Date
```

The AI ​​column shows:
- `✅ APPROVE` / `⛔ REJECT` — what the agent recommended
- If `operator_agrees_with_agent === false` is an additional indicator `⚡ Override`
- If `agent_recommendation` is not available — `—`

**Outcome** column instead of Status for history view (closed incidents):
- `Approved ✓` / `Rejected ✗` — operator decision
- If `operator_agrees_with_agent === false` → tooltip "Operator override AI recommendation"

#### 9. `frontend/src/pages/IncidentHistoryPage.tsx`

CSV export — add two new columns:

```typescript
{ header: "AI Recommendation", value: (i) => i.ai_analysis?.agent_recommendation ?? i.agent_recommendation ?? "" },
{ header: "Operator Agrees With AI", value: (i) => i.operator_agrees_with_agent != null ? String(i.operator_agrees_with_agent) : "" },
```

#### 10. `frontend/src/pages/AuditTrailPage.tsx`

Each line of the audit trail for a closed incident shows:

```
INC-2026-0049 | 22 Apr 2026 | jane.smith (Operator) | Approved
              AI said: ✅ APPROVE → Operator: ✅ Approved   [Agreement ✓]

INC-2026-0051 | 22 Apr 2026 | john.doe (QA Manager) | Rejected
              AI said: ✅ APPROVE → Operator: ✗ Rejected   [Override ⚡]
```

New component: `AiVsHumanBadge.tsx`

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

Expand the `RecentDecision` widget:

Add to each line:
```
INC-0049  jane.smith (Operator)  84%  ✅→✅ Agreed      2 min ago
INC-0051  john.doe (QA Mgr)      62%  ✅→✗ Override     8 min ago
INC-0048  alice.m  (Operator)    —    BLOCKED→✅ Approved  1h ago
```

Legend: `✅→✅` = AI APPROVE, operator Approved. `✅→✗` = AI APPROVE, operator Rejected (override).

Add a small summary KPI under the table:
```
AI–Human agreement rate (last 30 decisions): 78%
```

---

## Wireframe — IncidentTable with AI column

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

## New components

| Component | Where is used |
|---|---|
| `AgentRecommendationBadge.tsx` | ApprovalPanel (HITL) |
| `AiVsHumanBadge.tsx` | AuditTrailPage, IncidentTable |

---

## Definition of Done

**Backend:**
- [ ] `http_decision.py` accepts `agent_recommendation` + calculates `operator_agrees_with_agent`
- [ ] `finalize_audit.py` stores both fields in Cosmos incident + audit event
- [ ] `run_foundry_agents.py` / normalized result stores `agent_recommendation` in `ai_analysis`
- [ ] `http_stats.py` includes `agent_recommendation` + `operator_agrees_with_agent` in `recent_decisions`

**Frontend:**
- [ ] `AgentRecommendationBadge` is shown in the ApprovalPanel — clearly, above the buttons
- [ ] `agent_recommendation` is passed in the body of `POST /decision`
- [ ] `IncidentTable` shows AI column + Override indicator
- [ ] `IncidentHistoryPage` CSV export includes new fields
- [ ] `AuditTrailPage` shows `AiVsHumanBadge` per row
- [ ] `RecentDecisions` widget shows AI→Human pattern + agreement rate KPI
- [ ] `types/incident.ts` and `types/stats.ts` updated

---

## Priority and scope

🟠 HIGH — this feature is a direct demonstration of the value of AI: "this is what the system advised, this is what the operator decided." Critical for the hackathon demo story and for post-demo analytics of recommendation quality.
