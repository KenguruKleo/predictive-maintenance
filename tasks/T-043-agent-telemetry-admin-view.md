# T-043 · Agent Telemetry by Incident (Agent + Sub-agent Logs + Admin View)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟠 HIGH  
**Статус:** ✅ DONE  
**Gap / Вимога:** Gap #4 (AI Observability), Gap #5 (Admin UX), Architecture scoring: Reliability / Performance / Cost

---

## Мета

Зробити повний audit/telemetry trail по кожному інциденту для агентів і субагентів (Foundry Connected Agents), щоб IT Admin / QA Manager могли зручно аналізувати поведінку системи, дебажити проблеми і налаштовувати prompts/tools.

## Поточний перевірений стан (19 квітня 2026)

В repo вже є важлива частина foundation, але вона поки не доходить до admin frontend як окремий продуктований feature.

### Що вже є

- `backend/activities/run_foundry_agents.py` вже пише incident-scoped `FOUNDRY_PROMPT_TRACE` записи в **App Insights**
- доступні trace kinds:
  - `prompt_context`
  - `orchestrator_user_prompt`
  - `thread_messages`
  - `raw_response`
  - `parsed_response`
  - `normalized_result`
- усі ці записи вже можна шукати по `incident_id` і `round` у App Insights / Log Analytics

### Що frontend already sees today

- React incident detail already calls `GET /api/incidents/{id}/events`
- цей endpoint читає **Cosmos `incident_events`**
- там зберігається business timeline / transcript:
  - `analysis_started`
  - `agent_response`
  - `more_info`
  - approval / rejection / escalation events

### Що вже реалізовано в MVP slice

- `backend/shared/agent_telemetry.py` нормалізує incident-scoped `FOUNDRY_PROMPT_TRACE` rows з App Insights через `azure-monitor-query`
- `backend/triggers/http_agent_telemetry.py` додає `GET /api/incidents/{id}/agent-telemetry`
- endpoint підтримує filters: `agent_name`, `status`, `round`
- role gating на backend: `QAManager`, `ITAdmin`, `Auditor`
- `frontend/src/pages/IncidentTelemetryPage.tsx` додає admin incident-centric telemetry page на `/telemetry`
- frontend already has:
  - KPI summary cards
  - timeline of normalized trace items
  - `Copy diagnostics` button
  - incident detail deep-link `View Telemetry`
  - sidebar + command palette navigation

### Чого ще немає

- структурованої `agent_telemetry` projection в `incident_events`
- token / cost / retry metrics достатньої точності для фінального demo claim
- guaranteed exact sub-agent run-step visibility через Foundry SDK

### Важливе обмеження

Поточний `azure-ai-agents` SDK у цьому repo не дає повного connected-agents run-step API для внутрішніх Research / Document sub-agent invocations.

Отже first-pass admin view має чесно показувати **backend-visible Foundry trace**, а не обіцяти ідеально повний внутрішній call graph субагентів.

---

## Scope

### 1) Backend telemetry logging (by incident)

> **Уточнення до MVP:** detailed trace source of truth already lives in App Insights. У поточному slice ми не дублюємо ці trace rows в нову store, а будуємо normalized admin delivery path до frontend.

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

Поточний MVP already covers:
- `backend/activities/run_foundry_agents.py` як source trace emitter
- `backend/shared/agent_telemetry.py` як App Insights query + normalization layer

Second pass:
- `backend/activities/run_execution_agent.py`
- wrapper навколо MCP/tool invocations (тільки completed/failed на first pass)
- optional compact projection into `incident_events`

### 2) Admin API for incident telemetry timeline

Додати endpoint для зручного перегляду логів по інциденту:

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
- ✅ KPI strip зверху: `Trace Items`, `Completed`, `Started`, `Failed`, `Rounds`, `Duration`
- ✅ Timeline список по timestamp
- ✅ Badges: status + content type + chunk metadata
- ✅ Button `Copy diagnostics` копіює JSON summary + last 20 events
- ⏳ `Retries`, `Tokens`, `Cost` лишаються second pass, коли ці метрики стабільно доступні в traces

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

1. ✅ `GET /api/incidents/{id}/agent-telemetry` over App Insights traces
2. ✅ Simple IT Admin page with summary cards + timeline
3. ✅ Incident detail deep-link + admin navigation entry points
4. ⏳ Persist compact projection в `incident_events` for fast UI / offline correlation
5. ⏳ Add tokens/cost and tool-level events as second pass

---

## Залежності

- T-029 (події decision/more_info вже пишуться в incident_events)
- T-031 (backend API surface)
- T-034 (IT Admin views)
- T-040 (agent observability metrics)

---

## Definition of Done

- [x] App Insights traces are normalized into an incident-centric admin telemetry response
- [x] `incident_events` містить structured telemetry projection for agent/sub-agent/tool calls (or an explicitly accepted fallback scope is documented)
- [x] Для одного incident видно backend-visible ланцюг: start -> trace items / tool rows (коли доступні) -> completion/failure
- [x] `GET /api/incidents/{id}/agent-telemetry` повертає timeline + aggregates
- [x] IT Admin page показує telemetry timeline у розрізі incident
- [x] Role gating працює (operator не бачить telemetry admin view)
- [ ] App Insights і Cosmos events корелюються через `incidentId` + `correlationId`
- [ ] Demo-ready: для одного incident можна за 30 секунд пояснити "що зробив агент, чому, скільки це коштувало і де збій"
