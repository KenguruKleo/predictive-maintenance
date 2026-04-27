# T-027 · Execution Agent (Azure AI Foundry + MCP-QMS + MCP-CMMS)

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🔴 CRITICAL
**Status:** 🔜 TODO
**Blocks:** T-024 (step 6a — execute_decision activity)
**Depends on:** T-028 (MCP servers — qms-mock, cmms-mock), T-026 (Document Agent output schema)

---

## Goal

Execution Agent performs actions AFTER human approval: creates work order in mock CMMS and audit entry in mock QMS. Called only when `operator_decision == "approved"`.

---

## Tools that the Execution Agent has

| Tool | Source | Purpose |
|---|---|---|
| `create_work_order` | MCP mcp-cmms | Create corrective WO in CMMS |
| `create_audit_entry` | MCP mcp-qms | Create GMP-compliant audit entry in QMS |
| `get_template` | MCP mcp-sentinel-db | Fetch WO / audit templates |
| `update_incident_status` | MCP mcp-sentinel-db | Mark incident as closed with WO/AE IDs |

---

## Input (from Durable activity execute_decision)

```json
{
  "incident_id": "INC-2026-0001",
  "ai_result": { ... Document Agent output ... },
  "approver_id": "ivan.petrenko",
  "approval_notes": "Approved with enhanced sampling"
}
```

## Output

```json
{
  "work_order_id": "WO-2026-0123",
  "cmms_url": "mock://cmms/work-orders/WO-2026-0123",
  "audit_entry_id": "AE-2026-0089",
  "qms_url": "mock://qms/audit-entries/AE-2026-0089",
  "executed_at": "2026-04-17T09:15:00Z"
}
```

## System Prompt highlight

```
You are the Execution Agent. You ONLY run after a human operator has approved the recommended actions.

Your tasks (in order):
1. Fetch the work order template from Cosmos DB
2. Fill it with the incident details and CAPA actions from the Document Agent analysis
3. Create the work order in CMMS (use create_work_order tool)
4. Fetch the audit entry template from Cosmos DB
5. Fill it with all required GMP fields (deviation, root cause, CAPA, batch disposition, approver)
6. Create the audit entry in QMS (use create_audit_entry tool)
7. Return the IDs of both created records

CRITICAL: You must include the approver's name and the approval timestamp in the audit entry.
Output must be valid JSON with work_order_id and audit_entry_id fields.
```

---

## Files

```
agents/
  execution_agent.py       # Agent definition + run_execution_agent() function
  prompts/
    execution_system.md    # System prompt
```

## Definition of Done

- [ ] Execution Agent created in Foundry
- [ ] `run_execution_agent()` creates WO and AE via MCP tools
- [ ] WO and AE IDs returned and stored in Cosmos DB incident document
- [ ] Audit entry includes approver_id and approval timestamp
- [ ] Agent called zero times when operator rejects (guard in Durable orchestrator)
