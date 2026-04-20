# T-033 · React Frontend — Approval UX (Decision Package + Approve/Reject/More Info)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🔴 CRITICAL  
**Статус:** ✅ DONE  
**Блокує:** finals demo  
**Залежить від:** T-032 (core frontend), T-029 (decision API), T-030 (SignalR)

---

## Мета

Operator approval flow — ключова UX частина для demo. Оператор бачить повний decision package від AI і приймає рішення.

---

## Компоненти

```
src/components/
  ApprovalPanel/
    ApprovalPanel.tsx          # Головний компонент — показується якщо status=pending_approval + assigned_to=currentUser
    DecisionPackage.tsx        # AI analysis summary (risk, confidence, recommendation)
    ConfidenceMeter.tsx        # Visual confidence bar (red if < 0.7 → LOW_CONFIDENCE banner)
    WorkOrderPreview.tsx       # Pre-filled WO draft
    AuditEntryPreview.tsx      # Pre-filled audit entry draft
    EvidenceList.tsx           # Citations (SOP refs + historical case links)
    DecisionButtons.tsx        # [✅ Approve] [❌ Reject] [❓ Need More Info]
    RejectModal.tsx            # Modal: requires rejection reason (text input)
    AgentChat.tsx              # Inline transcript + multiline question composer
    ApprovalSuccess.tsx        # Post-approval confirmation with WO/AE IDs
```

---

## Decision Package wireframe

```
┌──────────────────────────────────────────────────────────────┐
│  ⚠️  ACTION REQUIRED                                          │
│  GR-204 — Impeller Speed Deviation    ← auto-assigned to you│
├──────────────────────────────────────────────────────────────┤
│  PARAMETER EXCURSION                                         │
│  ████████████░░  580 RPM              Limit: 600–800 RPM     │
│  Duration: 4 min 7 sec  |  Severity: 🟠 MAJOR               │
├──────────────────────────────────────────────────────────────┤
│  AI RISK ASSESSMENT                                          │
│  Risk Level: 🟠 MEDIUM                                       │
│  Confidence: ████████████████░░░░  84%                       │
│                                                              │
│  Root Cause: Motor load fluctuation during binder addition.  │
│  Batch integrity likely maintained based on duration.        │
│                                                              │
│  CAPA Actions:                                               │
│  ✦ 1. Immediate: moisture check (target 8–12%)               │
│  ✦ 2. Short-term: motor current review + calibration WO      │
│  ✦ 3. Long-term: reduce filter replacement interval to 30d   │
│                                                              │
│  Batch Disposition: Conditional release pending testing      │
├──────────────────────────────────────────────────────────────┤
│  EVIDENCE                                                    │
│  📄 SOP-DEV-001 §4.2 — "Impeller speed deviations > 10%..."  │
│  📋 INC-2026-0003 — Similar spray rate deviation (resolved)  │
│  📖 GMP Annex 15 §6.3 — Process Parameter Deviations        │
├──────────────────────────────────────────────────────────────┤
│  WORK ORDER PREVIEW                          [Edit]          │
│  GR-204 — Motor Load Calibration Check                       │
│  Priority: High  |  Est. 4 hours  |  Assigned: Maintenance  │
├──────────────────────────────────────────────────────────────┤
│           [✅ APPROVE]  [❌ REJECT]  [❓ NEED MORE INFO]      │
│           (approval logs your name + timestamp in QMS)       │
└──────────────────────────────────────────────────────────────┘
```

## LOW_CONFIDENCE state

```
┌──────────────────────────────────────────────────────────────┐
│  🔴 AI LOW CONFIDENCE — QA MANAGER REVIEW REQUIRED           │
│  AI Confidence: 52% — insufficient evidence for auto-assist  │
│  Please consult QA Manager before making a decision.         │
└──────────────────────────────────────────────────────────────┘
```

---

## Decision submission

```typescript
// POST /api/incidents/{id}/decision
const submitDecision = async (action: 'approved' | 'rejected' | 'more_info', reason?: string) => {
  await api.incidents.submitDecision(incidentId, {
    action,
    user_id: currentUser.id,
    reason,
    question: action === 'more_info' ? moreInfoQuestion : undefined
  });
  navigate(`/incidents/${incidentId}`);  // redirect to updated detail view
};
```

## Progress (18 квітня 2026)

- [x] Approval panel no longer uses sticky positioning or its own internal scroll; the whole incident page scrolls as one document
- [x] `Ask question` is now an inline multiline textarea instead of a single-line field
- [x] Latest recommendation card stays separate from the transcript, while operator questions and agent replies remain visible as chronological dialog bubbles
- [x] `npm run lint` and `npm run build` pass in `frontend/`

## Progress (20 квітня 2026)

- [x] Approval UX now preserves unread attention when a new update arrives on an already open incident; the operator must explicitly acknowledge it from the bell or the left incident rail
- [x] Bell/dropdown click path still clears the unread marker for that incident, and re-clicking the same incident in the left rail now works as an explicit acknowledge action too

## Progress (21 квітня 2026)

- [x] Approval actions are now gated by the active decision owner from `incident.workflow_state`: operators only see buttons on operator-owned reviews, QA managers only on QA-owned escalations/follow-ups, and non-owning roles stay read-only
- [x] Read-only users still retain the decision summary / transcript surface when it exists, but the composer and approve/reject/more-info buttons are hidden unless the caller owns the active review step
- [x] `npm run build` passes in `frontend/`

---

## Definition of Done

- [ ] ApprovalPanel renders correctly for INC-2026-0001 (GR-204 pending incident)
- [ ] Clicking [✅ Approve] → POST /decision, incident status → "executing", success message
- [ ] Clicking [❌ Reject] → modal opens, requires reason text, then POST /decision
- [ ] Clicking [❓ Need More Info] → inline multiline composer focuses, question submits, re-analysis starts
- [ ] LOW_CONFIDENCE banner shown when confidence < 0.7
- [ ] Panel hidden for closed/rejected incidents
- [x] Non-operator roles see read-only decision package (no action buttons)
- [x] Notification-center click path lands in the same approval surface and clears unread state for that incident
