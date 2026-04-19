# T-043 · Agent Telemetry by Incident (Agent + Sub-agent Logs + Admin View)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟠 HIGH  
**Статус:** 🔜 TODO  
**Gap / Вимога:** Gap #4 (AI Observability), Gap #5 (Admin UX), Architecture scoring: Reliability / Performance / Cost

---

## Мета

Зробити повний audit/telemetry trail по кожному інциденту для агентів і субагентів (Foundry Connected Agents), щоб IT Admin / QA Manager могли зручно аналізувати поведінку системи, дебажити проблеми і налаштовувати prompts/tools.

---

## Scope

### 1) Backend telemetry logging (by incident)

Логувати кожен крок у `incident_events` (і паралельно в App Insights) зі спільним `incidentId` та `correlationId`:

- `agent_run_started`
- `subagent_run_started`
- `subagent_run_completed`
- `subagent_run_failed`
- `agent_run_completed`
- `agent_run_failed`
- `tool_call_started`
- `tool_call_completed`
- `tool_call_failed`

Обов'язкові поля для кожного event:
- `incidentId`
- `correlationId`
- `round`
- `agent_name` (`orchestrator`, `research`, `document`, `execution`)
- `run_id`, `thread_id` (якщо доступні)
- `tool_name` (якщо це tool event)
- `duration_ms`
- `status`
- `token_input`, `token_output`, `token_total` (якщо доступні)
- `error_type`, `error_message` (для failed events)
- `timestamp`

### Technical minimum: Cosmos event schema

> Для hackathon/demo не робимо окрему telemetry collection. Пишемо в існуючий `incident_events`, але з окремим `type = "agent_telemetry"` і стабільним payload schema.

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

**Нормалізація для існуючого коду:**
- Пишемо і `incidentId`, і `incident_id`, бо в repo вже є змішані naming patterns
- `action` залишається головним event discriminator, щоб reuse-нути існуючий timeline UI
- `type = "agent_telemetry"` дозволяє відфільтрувати ці події від `more_info`, `approved`, `agent_response`

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

Мінімальні точки виклику:
- `backend/activities/run_foundry_agents.py`
- `backend/activities/run_execution_agent.py`
- wrapper навколо MCP/tool invocations (тільки completed/failed на first pass)

### 2) Admin API for incident telemetry timeline

Додати endpoint для зручного перегляду логів по інциденту:

```
GET /api/incidents/{incident_id}/agent-telemetry
Authorization: Bearer {token}
Roles: qa-manager, it-admin, auditor (read-only)
```

Response:
- timeline events (sorted asc)
- aggregated summary:
  - total runs
  - failed runs
  - retries
  - total tokens
  - estimated cost
  - total duration

### Technical minimum: endpoint contract

Query params:
- `agent_name` — optional (`orchestrator|research|document|execution`)
- `status` — optional (`started|completed|failed`)
- `round` — optional integer

Response example:

```json
{
  "incident_id": "INC-2026-0001",
  "summary": {
    "total_events": 14,
    "agent_runs": 3,
    "failed_runs": 1,
    "tool_calls": 4,
    "retries": 1,
    "token_total": 8120,
    "estimated_cost_usd": 0.1184,
    "total_duration_ms": 64219,
    "last_status": "completed"
  },
  "items": [
    {
      "timestamp": "2026-04-19T10:41:04Z",
      "action": "agent_run_started",
      "status": "started",
      "round": 1,
      "agent_name": "orchestrator",
      "parent_agent": null,
      "tool_name": null,
      "duration_ms": null,
      "token_total": null,
      "estimated_cost_usd": null,
      "details": "Orchestrator run started"
    }
  ]
}
```

### Technical minimum: backend implementation slice

1. `GET /api/incidents/{id}/agent-telemetry` in new trigger file `backend/triggers/http_agent_telemetry.py`
2. Query only `incident_events` with `type = 'agent_telemetry'`
3. Compute aggregates in Python (не робимо окрему materialized view для hackathon)
4. Reuse existing auth helpers and allow only `qa-manager`, `it-admin`, `auditor`

### 3) Admin UI (incident-centric)

Додати сторінку/панель для адмінів:

```
src/pages/IncidentTelemetryPage.tsx
src/components/Admin/IncidentTelemetryTimeline.tsx
src/components/Admin/AgentRunSummary.tsx
```

Features:
- Фільтри: `incidentId`, `agent_name`, `status`, `time range`
- Timeline в стилі "event stream" (з кольорами success/warn/error)
- Групування по round
- Швидкі метрики зверху: latency, failed calls, retries, tokens, cost
- Copy diagnostics button (incident snapshot for support)

### Technical minimum: frontend contract

> Для demo не потрібен повноцінний observability portal. Достатньо однієї incident-centric сторінки в IT Admin area.

```tsx
IncidentTelemetryPage
  AgentRunSummary
  TelemetryFilters
  IncidentTelemetryTimeline
```

Мінімум для demo:
- KPI strip зверху: `Total runs`, `Failures`, `Retries`, `Tokens`, `Cost`, `Duration`
- Timeline список по timestamp
- Badges: `orchestrator`, `research`, `document`, `execution`, `tool`
- Error rows highlighted in red
- Button `Copy diagnostics` копіює JSON summary + last 20 events

Не робимо в first pass:
- global cross-incident observability
- charts by day/week
- live streaming telemetry
- editable prompt tuning UI

### Demo script (30 seconds)

- Відкрити incident detail або admin page
- Перейти на telemetry tab/page
- Показати: orchestrator стартував -> research sub-agent -> document sub-agent -> tool calls -> completed
- Якщо був збій: показати failed row + retry + final outcome
- Завершити меседжем: "ми бачимо не тільки результат AI, а і весь процес його формування"

---

## Implementation order (smallest viable slice)

1. Backend helper `log_agent_telemetry()` + 3-4 event types в `run_foundry_agents.py`
2. Persist в `incident_events`
3. `GET /api/incidents/{id}/agent-telemetry`
4. Simple IT Admin page with summary cards + timeline
5. Add tokens/cost and tool-level events as second pass

---

## Залежності

- T-029 (події decision/more_info вже пишуться в incident_events)
- T-031 (backend API surface)
- T-034 (IT Admin views)
- T-040 (agent observability metrics)

---

## Definition of Done

- [ ] `incident_events` містить structured telemetry для agent/sub-agent/tool calls
- [ ] Для одного incident видно повний ланцюг: start -> subagent/tool steps -> completion/failure
- [ ] `GET /api/incidents/{id}/agent-telemetry` повертає timeline + aggregates
- [ ] IT Admin page показує telemetry timeline у розрізі incident
- [ ] Role gating працює (operator не бачить telemetry admin view)
- [ ] App Insights і Cosmos events корелюються через `incidentId` + `correlationId`
- [ ] Demo-ready: для одного incident можна за 30 секунд пояснити "що зробив агент, чому, скільки це коштувало і де збій"
