# T-052 · Editable WO / Audit entry forms in HITL UI

← [Backlog](../04-action-plan.md)

> **Purpose:** Show WO draft and audit entry draft as editable multi-line forms in decision package UI. Pre-filled by Document Agent; operator/QA can edit before Approve. In the BLOCKED state (agent failure), the forms are empty, the operator fills in manually (required for Approve).

---

## Context

After approval, the Execution Agent creates real records in CMMS and QMS. The payload for these calls is taken from the forms that the operator reviewed and confirmed — these are:
1. guarantees that data in external systems correspond to the operator's decision;
2. resolves the BLOCKED case (agent fail = zero confidence) — the operator can manually enter the WO and audit entry without blocking the process;
3. allows QA Manager to adjust drafts during escalation.

---

## Flow data (important for GxP)

```
DocumentAgentOutput
└── ai_analysis.work_order_draft ← AI original (KEPT constant in Cosmos)
└── ai_analysis.audit_entry_draft ← AI original (KEPT constant in Cosmos)
           ↓ pre-fills editable form
[frontend: operator edits or fills manually when BLOCKED]
           ↓ POST /api/incidents/{id}/decision
body.work_order_draft / body.audit_entry_draft ← operator-confirmed version
↓ is stored separately
      incident.operatorWorkOrderDraft     ← operator-final
      incident.operatorAuditEntryDraft    ← operator-final
           ↓
run_execution_agent reads the operator version, NOT ai_analysis
```

**Both versions remain:** `ai_analysis.work_order_draft` = suggested by AI; `operatorWorkOrderDraft` = what was confirmed/changed by the operator. Auditor sees both — this is a documented change trail for GMP.

## Affected components

- `frontend/src/components/Approval/` — `WorkOrderPreview.tsx` / `AuditEntryPreview.tsx` → make editable (or replace with new components)
- `backend/triggers/http_decision.py` — accept `work_order_draft` and `audit_entry_draft` in the body; save as `operatorWorkOrderDraft` / `operatorAuditEntryDraft` per incident
- `backend/activities/run_execution_agent.py` — read `operatorWorkOrderDraft` / `operatorAuditEntryDraft` instead of re-generation through GPT-4o

---

## UI behavior

| Agent status | WO draft | Audit entry draft Approve is available |
|---|---|---|---|
| NORMAL (conf ≥ 0.7) | Pre-filled by Document Agent, editable | Pre-filled by Document Agent, editable | Yes, without additional requirements
| LOW_CONFIDENCE | Pre-filled, editable | Pre-filled, editable | Yes, + mandatory comment |
| BLOCKED (agent fail) | Empty, **required** | Empty, **required** | Only after filling |

**Editing access:**
- `operator`, `qa-manager` — can edit
- `maint-tech`, `auditor`, `it-admin` — read-only

**UI elements:**
- `<textarea>` or structured form with minimal fields: `description`, `priority` (WO) and `deviation_type`, `gmp_clause` (audit)
- Approve button disabled if BLOCKED + forms are empty
- Hint text in empty fields: "Introduce work order description manually (AI was unable to generate a recommendation)"

---

## Backend changes

### `POST /api/incidents/{id}/decision`

New fields in the request body:
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

- If `decision == "approved"`: `work_order_draft` and `audit_entry_draft` are mandatory (validation).
- If `decision == "rejected"`: Fields are ignored.
- Backend stores `operator_edited_draft` in `approval-tasks` → Durable reads when `run_execution_agent` is called.

### `run_execution_agent.py`

- Reads `work_order_draft` and `audit_entry_draft` from `approval-tasks` container (operator-edited version).
- No longer **generates** payload independently from Document Agent output.

---

## Audit trail

Fields in `finalize_audit`:
- `human_override_text` — operator-edited WO/audit drafts (if different from the agent draft, or if BLOCKED)
- `human_override = true` if the operator changed the agent draft or filled in manually

---

## Definition of Done

- [ ] WO draft and audit entry draft are displayed as editable fields in the approval UI
- [ ] Pre-filled by Document Agent in a normal scenario
- [ ] Empty and mandatory when BLOCKED
- [ ] Approve disabled if BLOCKED + empty fields
- [ ] Read-only fields for maint-tech, auditor, it-admin
- [ ] Backend stores `operatorWorkOrderDraft` + `operatorAuditEntryDraft` separately from `ai_analysis` (AI original remains unchanged)
- [ ] `run_execution_agent` reads `operatorWorkOrderDraft` / `operatorAuditEntryDraft`, no longer generates via GPT-4o
- [ ] `human_override_text` is written to `finalize_audit` if the operator changed or filled in manually

---

## Priority

🟠 HIGH — blocks a full-fledged BLOCKED scenario and GxP payload correctness for external systems.
