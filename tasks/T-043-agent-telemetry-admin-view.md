# T-043 · Agent Telemetry by Incident (Agent + Sub-agent Logs + Admin View)

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🟠 HIGH
**Status:** ✅ DONE
**Gap / Requirement:** Gap #4 (AI Observability), Gap #5 (Admin UX), Architecture scoring: Reliability / Performance / Cost

---

## Goal

Create a full audit/telemetry trail for each incident for agents and sub-agents (Foundry Connected Agents) so that IT Admin / QA Manager can conveniently analyze system behavior, debug problems and configure prompts/tools.

## Current verified status (April 19, 2026)

There is already an important part of the foundation in the repo, but it has not yet reached the admin frontend as a separate production feature.

### What is already there

- `backend/activities/run_foundry_agents.py` already writes incident-scoped `FOUNDRY_PROMPT_TRACE` entries in **App Insights**
- available trace kinds:
  - `prompt_context`
  - `orchestrator_user_prompt`
  - `thread_messages`
  - `raw_response`
  - `parsed_response`
  - `normalized_result`
- all these records can already be searched by `incident_id` and `round` in App Insights / Log Analytics

### What the frontend already sees today

- React incident detail already calls `GET /api/incidents/{id}/events`
- this endpoint reads **Cosmos `incident_events`**
- business timeline / transcript is stored there:
  - `analysis_started`
  - `agent_response`
  - `more_info`
  - approval / rejection / escalation events

### What is already implemented in the MVP slice

- `backend/shared/agent_telemetry.py` normalizes incident-scoped `FOUNDRY_PROMPT_TRACE` rows from App Insights via `azure-monitor-query`
- `backend/triggers/http_agent_telemetry.py` adds `GET /api/incidents/{id}/agent-telemetry`
- endpoint supports filters: `agent_name`, `status`, `round`
- role gating on the backend: `QAManager`, `ITAdmin`, `Auditor`
- `frontend/src/pages/IncidentTelemetryPage.tsx` adds admin incident-centric telemetry page to `/telemetry`
- frontend already has:
  - KPI summary cards
  - timeline of normalized trace items
  - `Copy diagnostics` button
  - incident detail deep-link `View Telemetry`
  - sidebar + command palette navigation

### What else is missing

- structured `agent_telemetry` projection in `incident_events`
- token / cost / retry metrics of sufficient accuracy for the final demo claim
- guaranteed exact sub-agent run-step visibility via Foundry SDK

### An important limitation

The current `azure-ai-agents` SDK in this repo does not provide a full connected-agents run-step API for internal Research / Document sub-agent invocations.

So the first-pass admin view should honestly show **backend-visible Foundry trace**, and not promise a perfectly complete internal call graph of subagents.

---

## Scope

### 1) Backend telemetry logging (by incident)

> **Clarification to MVP:** detailed trace source of truth already lives in App Insights. In the current slice, we do not duplicate these trace rows in a new store, but build a normalized admin delivery path to the frontend.

Log each step in `incident_events` (and in parallel in App Insights) with shared `incidentId` and `correlationId`:

- `agent_run_started`
- `subagent_run_started`
- `subagent_run_completed`
- `subagent_run_failed`
- `agent_run_completed`
- `agent_run_failed`
- `tool_call_started`
- `tool_call_completed`
- `tool_call_failed`

Mandatory fields for each event:
- `incidentId`
- `correlationId`
- `round`
- `agent_name` (`orchestrator`, `research`, `document`, `execution`)
- `run_id`, `thread_id` (if available)
- `tool_name` (if this is a tool event)
- `duration_ms`
- `status`
- `token_input`, `token_output`, `token_total` (if available)
- `error_type`, `error_message` (for failed events)
- `timestamp`

### Technical minimum: Cosmos event schema

> We do not make a separate telemetry collection for the hackathon/demo. We write to the existing `incident_events`, but with a separate `type = "agent_telemetry"` and a stable payload schema.

```json
{
  "id": "evt-telemetry-INC-2026-0001-00017",
  "type": "agent_telemetry",
  "incidentId": "INC-2026-0001",
  "incident_id": "INC-2026-0001",
  "correlationId": "corr-6c0b9b7d",
  "action": "subagent_run_completed",
  "status": "completed",
  "round": 1,
  "agent_name": "research",
  "parent_agent": "orchestrator",
  "run_id": "run_abc123",
  "thread_id": "thread_xyz789",
  "tool_name": null,
  "duration_ms": 8421,
  "token_input": 1850,
  "token_output": 640,
  "token_total": 2490,
  "estimated_cost_usd": 0.0312,
  "error_type": null,
  "error_message": null,
  "details": "Research agent completed grounded retrieval over SOP/BPR/QMS sources",
  "timestamp": "2026-04-19T10:42:11Z",
  "createdAt": "2026-04-19T10:42:11Z"
}
```

**Normalization for existing code:**
- We write both `incidentId` and `incident_id`, because the repo already has mixed naming patterns
- `action` remains the main event discriminator to reuse the existing timeline UI
- `type = "agent_telemetry"` allows you to filter these events from `more_info`, `approved`, `agent_response`

### Technical minimum: helper API in backend

```python
# backend/utils/agent_telemetry.py
def log_agent_telemetry(
    incident_id: str,
    action: str,
    *,
    agent_name: str,
    status: str,
    correlation_id: str,
    round: int = 0,
    parent_agent: str | None = None,
    run_id: str | None = None,
    thread_id: str | None = None,
    tool_name: str | None = None,
    duration_ms: int | None = None,
    token_input: int | None = None,
    token_output: int | None = None,
    token_total: int | None = None,
    estimated_cost_usd: float | None = None,
    details: str | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> None:
    ...
```

Current MVP already covers:
- `backend/activities/run_foundry_agents.py` as a source trace emitter
- `backend/shared/agent_telemetry.py` as App Insights query + normalization layer

Second pass:
- `backend/activities/run_execution_agent.py`
- wrapper around MCP/tool ​​invocations (only completed/failed on first pass)
- optional compact projection into `incident_events`

### 2) Admin API for incident telemetry timeline

Add an endpoint for convenient viewing of incident logs:

```
GET /api/incidents/{incident_id}/agent-telemetry
Authorization: Bearer {token}
Roles: qa-manager, it-admin, auditor (read-only)
```

Response:
- normalized timeline items (sorted asc)
- aggregated summary for the current filtered incident trace slice
- explicit scope / limitations block so admin UI does not overclaim SDK visibility

### Technical minimum: endpoint contract

Query params:
- `agent_name` — optional (`orchestrator|research|document|execution`)
- `status` — optional (`started|completed|failed`)
- `round` — optional integer

Implemented MVP response shape:

```json
{
  "incident_id": "INC-2026-0001",
  "summary": {
    "total_items": 14,
    "started_items": 2,
    "completed_items": 12,
    "failed_items": 0,
    "rounds": [0, 1],
    "agent_names": ["orchestrator"],
    "trace_kinds": ["prompt_context", "normalized_result"],
    "total_content_chars": 8120,
    "total_duration_ms": 64219,
    "last_timestamp": "2026-04-19T10:41:04Z",
    "view_scope": "backend_visible_foundry_trace"
  },
  "items": [
    {
      "id": "telemetry-1-normalized_result-abc123def456",
      "timestamp": "2026-04-19T10:41:04Z",
      "trace_kind": "normalized_result",
      "title": "Normalized Result",
      "status": "completed",
      "round": 1,
      "agent_name": "orchestrator",
      "source": "app_insights",
      "content_type": "json",
      "preview": "{\"risk_level\": \"HIGH\"}",
      "content": "{\"risk_level\": \"HIGH\"}",
      "metadata": {},
      "chunk_count": 1,
      "content_length": 22,
      "run_id": null,
      "thread_id": null
    }
  ],
  "query": {
    "agent_name": null,
    "status": null,
    "round": null
  },
  "scope": {
    "source": "app_insights",
    "view": "backend_visible_foundry_trace",
    "limitations": [
      "Current SDK traces cover the backend-visible Foundry path only.",
      "Connected sub-agent internal steps are not fully exposed by the SDK."
    ]
  }
}
```

### Technical minimum: backend implementation slice

1. ✅ `GET /api/incidents/{id}/agent-telemetry` in `backend/triggers/http_agent_telemetry.py`
2. ✅ Query App Insights / Log Analytics for `FOUNDRY_PROMPT_TRACE` rows by `incident_id`
3. ✅ Compute normalized timeline items + aggregates in Python
4. ✅ Reuse existing auth helpers and allow only `qa-manager`, `it-admin`, `auditor`
5. ⏳ Optionally merge with `incident_events` (`type = 'agent_telemetry'`) once compact projection is added

### 3) Admin UI (incident-centric)

Add a page/panel for admins:

```
src/pages/IncidentTelemetryPage.tsx
src/components/Admin/IncidentTelemetryTimeline.tsx
src/components/Admin/AgentRunSummary.tsx
```

Features:
- Filters: `incidentId`, `agent_name`, `status`, `time range`
- Timeline in "event stream" style (with success/warn/error colors)
- Grouping by round
- Quick metrics from above: latency, failed calls, retries, tokens, cost
- Copy diagnostics button (incident snapshot for support)

### Technical minimum: frontend contract

> A full observability portal is not required for the demo. One incident-centric page in the IT Admin area is enough.

```tsx
IncidentTelemetryPage
  AgentRunSummary
  TelemetryFilters
  IncidentTelemetryTimeline
```

Minimum for demo:
- ✅ KPI strip from above: `Trace Items`, `Completed`, `Started`, `Failed`, `Rounds`, `Duration`
- ✅ Timeline list by timestamp
- ✅ Badges: status + content type + chunk metadata
- ✅ Button `Copy diagnostics` copies JSON summary + last 20 events
- ⏳ `Retries`, `Tokens`, `Cost` remain second pass when these metrics are stably available in traces

We do not do in the first pass:
- global cross-incident observability
- charts by day/week
- live streaming telemetry
- editable prompt tuning UI

### Demo script (30 seconds)

- Open incident detail or admin page
- Go to the telemetry tab/page
- Show: orchestrator started -> research sub-agent -> document sub-agent -> tool calls -> completed
- If there was a failure: show failed row + retry + final outcome
- End with the message: "we see not only the result of AI, but also the entire process of its formation"

---

## Implementation order (smallest viable slice)

1. ✅ `GET /api/incidents/{id}/agent-telemetry` over App Insights traces
2. ✅ Simple IT Admin page with summary cards + timeline
3. ✅ Incident detail deep-link + admin navigation entry points
4. ⏳ Persist compact projection in `incident_events` for fast UI / offline correlation
5. ⏳ Add tokens/cost and tool-level events as second pass

---

## Dependencies

- T-029 (decision/more_info events are already written in incident_events)
- T-031 (backend API surface)
- T-034 (IT Admin views)
- T-040 (agent observability metrics)

---

## Definition of Done

- [x] App Insights traces are normalized into an incident-centric admin telemetry response
- [x] `incident_events` contains structured telemetry projection for agent/sub-agent/tool ​​calls (or an explicitly accepted fallback scope is documented)
- [x] For one incident, the backend-visible chain is visible: start -> trace items / tool rows (when available) -> completion/failure
- [x] `GET /api/incidents/{id}/agent-telemetry` returns timeline + aggregates
- [x] IT Admin page shows telemetry timeline in incident section
- [x] Role gating works (operator does not see telemetry admin view)
- [ ] App Insights and Cosmos events are correlated via `incidentId` + `correlationId`
- [ ] Demo-ready: for one incident, you can explain in 30 seconds "what the agent did, why, how much it cost and where the failure occurred"
