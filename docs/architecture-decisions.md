# Architecture Decision Records — Sentinel Intelligence

← [README](../README.md) · [02 Архітектура](../02-architecture.md) · [docs/hackathon-scope.md](./hackathon-scope.md) · [docs/architecture-history.md](./architecture-history.md)

> Архітектурні рішення, прийняті під час проектування системи. Кожне ADR фіксує контекст, розглянуті варіанти, рішення та наслідки. Додавайте нові ADR як `ADR-XXX` у хронологічному порядку.

## Зміст

- [ADR-001 — Human-in-the-loop mechanism](#adr-001--human-in-the-loop-mechanism)
- [ADR-002 — Foundry Connected Agents](#adr-002--foundry-connected-agents)

---

## ADR-001 — Human-in-the-loop mechanism

> **Тип:** ADR · **Дата:** 17 квітня 2026 · **Статус:** Прийнято ✅

**Контекст.** GMP вимагає mandatory human approval. Operator має до 24 годин на рішення. Потрібен механізм: пауза workflow, resume з рішенням, timeout + escalation.

**Варіанти:**

- **A. Foundry function_call + `previous_response_id`.** Run expires через 10 хв → не підходить для 24h паузи. Джерело: [Microsoft Foundry docs (квітень 2026)](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/function-calling) — *«Runs expire 10 minutes after creation. Submit your tool outputs before they expire.»*
- **B. Durable Functions `waitForExternalEvent` + `raise_event`.** Безкоштовна пауза скільки потрібно (Azure Storage persists state). Resume через HTTP endpoint.

**Рішення: B.**

| Критерій | A (Foundry) | B (Durable) |
|---|---|---|
| Максимальна пауза | 10 хв | необмежено |
| Відновлення після restart/crash | втрачається | persisted |
| Вартість під час паузи | N/A (протухає) | $0 (Consumption) |
| Resume API | N/A | `raiseEvent` HTTP |
| Timeout + escalation | немає | `create_timer` race pattern |

**Наслідки.** Foundry агенти — короткі activity functions (≤ 10 хв). Workflow state живе у Durable (Azure Storage). `approval-tasks` Cosmos container тримає pending approval для React UI. SignalR пушить «очікується рішення оператора». `POST /api/incidents/{id}/decision` викликає `raise_event` → orchestrator resume.

---

## ADR-002 — Foundry Connected Agents

> **Тип:** ADR · **Дата:** 17 квітня 2026 · **Статус:** Прийнято ✅

**Контекст.** Початкова ідея — окремі Durable activities на кожного агента з ручною передачею результатів та кастомним лічильником `loop_count` для `more_info`.

**Варіанти:**

- **A. Ручна оркестрація у Durable.** Окрема activity для кожного агента, ручна передача `ResearchAgentOutput` → Document Agent через Durable state, `loop_count` у Python коді.
- **B. Foundry Connected Agents.** Одна activity `run_foundry_agents` → Orchestrator Agent, до якого Research та Document підключені як `AgentTool`. Foundry нативно керує reasoning loop, `max_iterations`, routing, MCP + RAG tool connections.

**Рішення: B.**

| Критерій | A (ручна) | B (Connected Agents) |
|---|---|---|
| Кількість activity functions | 2 | 1 |
| Передача даних між агентами | через Durable state | нативно (Foundry thread) |
| more_info loop | кастомний лічильник | `max_iterations` у Foundry |
| MCP tool connections | кастомний wrapper | нативно |
| RAG tools | кастомний SDK код | `AzureAISearchTool` нативно |
| Рядків коду | ~200 | ~50 |

**Наслідки.** T-024 спрощується: одна activity `run_foundry_agents`. T-025/T-026 — Foundry Agent definitions, не Durable activities. `more_info`: Durable отримує decision, append-ить `operator_question` у context, повторно викликає `run_foundry_agents` — Foundry handle-ить новий round internally. Кількість rounds регулюється через `max_iterations` у Foundry + `MAX_MORE_INFO_ROUNDS` у Durable (для GMP audit trail).

---

← [02 Архітектура](../02-architecture.md) · [docs/architecture-history.md →](./architecture-history.md)
