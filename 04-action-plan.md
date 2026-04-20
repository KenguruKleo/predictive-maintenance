# 04 · План дій

← [README](./README.md) · [01 Вимоги](./01-requirements.md) · [02 Архітектура](./02-architecture.md) · [03 Аналіз](./03-analysis.md)

> **Призначення:** Живий backlog задач implementation фази. Оновлюємо в міру роботи. Кожна задача прив'язана до конкретного gap або вимоги.

---

## Зміст
1. [Поточний фокус](#1-поточний-фокус)
2. [Backlog задач](#2-backlog-задач)
3. [Sprint / Iteration план](#3-sprint--iteration-план)
4. [Definition of Done](#4-definition-of-done)
5. [Блокери та ризики](#5-блокери-та-ризики)

---

## 1. Поточний фокус

> **Квітень 2026 — Implementation Phase**  
> Дедлайн фінального submission: 1-й тиждень травня 2026  
> Стек: Python 3.11 · Azure Durable Functions · Azure AI Foundry · Cosmos DB · React + Vite

**Зараз в роботі:** T-027 (Execution Agent — placeholder impl, full Foundry Agent spec pending) · T-029 (Human Approval — transcript events + /decision flow) · T-030 (SignalR extension — notification center + unread state + browser alerts) · T-032 (React frontend core — incident detail/timeline + header bell + toast stack + unread sidebar cues) · T-033 (Approval UX — static rail + dialog transcript + mark-read on detail open) · T-039 (Reliability hardening) · T-040 (RAI observability) · T-043 (Agent telemetry admin delivery) · T-045 (Evidence citations quality)

> **ADR-002 — Foundry Connected Agents:** Research Agent + Document Agent реалізовані як sub-agents Foundry Orchestrator Agent.  
> Durable викликає одну activity `run_foundry_agents` — Foundry керує pipeline Research → Document нативно.  
> `more_info` loop: Durable накопичує `operator_questions`, знову запускає `run_foundry_agents`. Foundry керує internal iterations.  
> Дивись [02-architecture §8.10b](./02-architecture.md#810b-adr-002-foundry-connected-agents-vs-ручна-оркестрація).

**Завершено (18-19 квітня 2026):**
- ✅ T-024 — Durable Functions orchestrator: `incident_orchestrator.py` + 5 activities (`enrich_context`, `run_foundry_agents`, `notify_operator`, `run_execution_agent`, `finalize_audit`) + `service_bus_trigger.py` + `http_decision.py`
- ✅ T-025 — Research Agent (`asst_NDuVHHTsxfRvY1mRSd7MtEGT`): 8 tools (3 MCP + 5 AI Search), system prompt, підключений до Orchestrator як `AgentTool`
- ✅ T-026 — Document Agent (`asst_AXgt7fxnSnUh5WXauR27S40L`): system prompt + confidence gate + structured JSON output, підключений до Orchestrator як `AgentTool`
- ✅ T-041 (extension) — Bicep: AI Foundry Hub + Project + KeyVault + AI Search connection (`agents.bicep` модуль)
- ✅ Foundry Orchestrator Agent (`asst_CNYK3TZIaOCH4OPKcP4N9B2r`) зі вдвоєними sub-agents створено в Azure AI Foundry (`create_agents.py`)
- ✅ `run_foundry_agents.py` переписано під `azure-ai-agents` SDK

**Останнє оновлення (19-20 квітня 2026):**
- T-029 — `http_decision.py` hardened with RBAC (`Operator` / `QAManager`) and auth-backed caller identity, a focused pytest slice was added (`tests/test_http_decision.py`), and the change was deployed; live unauthorized smoke now returns `401 Authentication required`, while full bearer-token proof from the current CLI session is blocked by missing tenant consent for `api://38843d08-f211-4445-bcef-a07d383f2ee6/.default`
- T-029 — investigated the previous live blocker on `INC-2026-0019`: Cosmos showed `pending_approval` while Durable status was `null` (no active instance). `scripts/recover_live_incident.py --skip-more-info-replay --yes` re-queued the alert, recreated `durable-INC-2026-0019`, and `/decision` succeeded on the recovered live instance, so the observed issue is currently treated as a stale approval task / missing Durable instance rather than an instance-id mismatch
- T-030/T-032/T-033 — notification UX implementation started: backend now exposes Cosmos-backed unread notification APIs (`GET /api/notifications`, `GET /api/notifications/summary`, `POST /api/incidents/{id}/notifications/read`), SignalR payloads include stable notification IDs, frontend renders a header bell with unread badge/dropdown, live toast stack, browser-alert opt-in, unread highlight in the left incident rail, and marks incident notifications as read when the detail page opens
- T-045 — live `idx-incident-history` was manually rebuilt from approved closed Cosmos incidents (`INC-2026-0005`, `INC-2026-0006`, `INC-2026-0013`), and the same historical query now returns hits through both `search_utils.search_index()` and the deployed `mcp-search` REST endpoint; backend auto-sync-on-close was also implemented in `finalize_audit` and deployed, but fresh end-to-end live proof now depends on bearer-token approval validation after the T-029 RBAC hardening, not on the older stale `INC-2026-0019` Durable state
- T-045 — first implementation slice shipped for evidence/document quality: frontend incident detail now renders only normalized `evidence_citations`, backend normalization adds canonical dedupe, resolved/unresolved citation state, contextful excerpt backfill, and historical incident deep links, while `documents_from_incidents()` now indexes only approved closed/completed precedents; focused pytest coverage and frontend production build passed
- T-045 — created a follow-up backlog task for evidence/document quality after reviewing `INC-2026-0013`: make `evidence_citations` the only UI source of truth, enforce a strict backend citation contract, dedupe by canonical document identity, improve excerpt quality, and fix historical incident evidence/link semantics without editing legacy test data
- T-044 — local backend startup for E2E was hardened: `backend/function_app.py` now forces the repo backend path ahead of unrelated workspace paths so `utils.auth` no longer resolves to a foreign `utils.py`, and `http_agent_telemetry` now lazy-loads App Insights query dependencies so a missing local `azure.monitor.query` package degrades only that admin endpoint instead of crashing the whole Functions host
- T-026/T-040 — initial operator dialogue hardened in `run_foundry_agents.py`: round `0` now rewrites impossible carry-over phrasing like "the recommendation remains the same" to a clean first recommendation summary, with a focused regression test and live validation on `INC-2026-0013`
- T-044 — frontend local E2E path implemented: `VITE_AUTH_MODE=e2e`, shared mock-auth runtime, forced local `/api` base URL in E2E mode, Vite `/api` proxy, Playwright config with frontend+backend `webServer`, and 2 passing smoke tests (`operator` dashboard, `it-admin` templates)
- T-044 — while wiring admin smoke tests, frontend template handling was hardened to match the real backend contract: `GET /api/templates` now unwraps `{ items, total }`, object-shaped `fields` no longer crash the list page, and the editor preserves `fields` on save
- T-042 — backend deploy hardened: GitHub Actions backend deploy переведено на Azure Functions Core Tools publish (`func azure functionapp publish --python`), тобто той самий remote-build path, який реально відновлює Linux Consumption runtime після regression з `0 functions` і 404 на `/api/*`
- T-041 — для parity додано `AzureWebJobsFeatureFlags=EnableWorkerIndexing` у Function App app settings
- T-029/T-032/T-033 — incident detail approval UX спрощено: прибрано sticky/self-scroll у правій колонці, `Ask question` переведено в multiline textarea, transcript тепер зберігає initial + follow-up agent replies через `incident_events`, а recommendation card лишається latest state окремо від діалогу
- T-039 — `run_foundry_agents` hardened against long Foundry runs for both initial and `more_info` rounds: `backend/host.json` now sets `functionTimeout=00:10:00`, Foundry polling is bounded by an explicit wall-clock budget, timed-out agent runs are cancelled when possible, and the activity now returns a controlled manual-review fallback instead of leaving incidents stuck in `awaiting_agents`
- T-039 — live recovery path verified for `INC-2026-0001`: stale Durable instance terminated + purged, incident re-queued, fresh initial round returned to `pending_approval`, and the preserved operator `more_info` question was replayed onto the new orchestration instance
- T-039 — added `scripts/recover_live_incident.py`: one-command recovery for stuck live incidents (`terminate → purge → requeue → wait initial → optional replay more_info`) plus README usage notes for future on-call recovery
- T-039/T-040 — added incident-scoped Foundry prompt and response tracing in `run_foundry_agents` behind `FOUNDRY_PROMPT_TRACE_ENABLED`, with a stable `FOUNDRY_PROMPT_TRACE` envelope (`incident_id`, `round`, `trace_kind`, `thread_id`, `run_id`, chunk metadata) so logs can be queried later per incident for admin and audit troubleshooting
- T-040 — documented current multi-agent control flow, model split, SDK observability limits, and App Insights retrieval pattern in `docs/foundry-followup-analysis.md`
- T-043 — shipped the first admin telemetry MVP slice: App Insights-backed `GET /api/incidents/{id}/agent-telemetry`, Python normalization of `FOUNDRY_PROMPT_TRACE` rows, `/telemetry` admin page with KPI strip + timeline + copy diagnostics, incident-detail deep link, and admin navigation entries; remaining second-pass work is compact Cosmos projection plus token/cost/retry metrics when reliably available

**Завершено (17 квітня 2026):****
- ✅ T-041 — Bicep IaC: 9 ресурсів задеплоєно (Cosmos DB, Service Bus, Functions, Storage, App Insights, Log Analytics, AI Search, Azure OpenAI)
- ✅ T-042 — GitHub Actions CI/CD: `ci.yml` + `deploy.yml` живі та зелені
- ✅ T-022 — Service Bus: `alert-queue` + DLQ задеплоєно
- ✅ T-020 — Cosmos DB: 8 containers задеплоєно, 55 items seeded
- ✅ T-021 — Mock data: 55 items залито в Cosmos DB (`scripts/seed_cosmos.py`)
- ✅ T-037 — AI Search: 5 indexes, 9 docs, 117 chunks з HNSW vector embeddings
- ✅ T-023 — Ingestion API: `POST /api/alerts` + validation + severity + idempotency + Service Bus publish; `scripts/simulate_alerts.py` з 6 demo сценаріями
- ✅ T-028 — MCP servers: `mcp-sentinel-db` (5 tools), `mcp-qms` (create_audit_entry), `mcp-cmms` (create_work_order); `scripts/test_mcp_servers.py` — 8/8 passed
- ✅ T-031 — Backend API: 9 REST endpoints (incidents, equipment, batches, templates, stats); role-based filtering; all 11 HTTP triggers deployed
- ✅ T-035 — RBAC: App Registrations (API + SPA), 5 Entra ID roles, JWKS JWT signature verification (`auth.py`), security tests passed

**Наступний крок:** T-034 (frontend manager/auditor/IT views) → T-029 live e2e validation → T-001 architecture presentation → T-002 final video

---

## 2. Backlog задач

> Порядок виконання у [§3 Sprint план](#3-sprint--iteration-план).  
> Кожна задача — окремий файл `tasks/T-NNN-*.md`.

### Критичні (Must-have для finals)

| ID | Задача | Gap / Вимога | Пріоритет | Статус | Блокує |
|---|---|---|---|---|---|
| T-001 | **[Оновити архітектурну презентацію](./tasks/T-001-architecture-presentation.md)** — закрити всі gaps, показати реальну збудовану архітектуру (Track A, Security, Reliability, RAI, UX, IaC) | Gap #1–6 | 🔴 CRITICAL | 🔜 TODO | T-002 |
| T-002 | **[5-хвилинне фінальне відео](./tasks/T-002-final-video.md)** — повна demo презентація | Deliverables | 🔴 CRITICAL | 🔜 TODO | finals |
| T-020 | **[Cosmos DB — схема + provisioning](./tasks/T-020-cosmos-db.md)** — 8 containers, indexes, seed script | T-023, T-024 | 🔴 CRITICAL | ✅ DONE | — |
| T-021 | **[Mock data seed](./tasks/T-021-mock-data.md)** — equipment(3), batches(20), incidents(30), templates(2) | demo | 🔴 CRITICAL | ✅ DONE | — |
| T-023 | **[Ingestion API](./tasks/T-023-ingestion-api.md)** — POST /api/alerts + context enrichment + Service Bus publish | Gap #3 | 🔴 CRITICAL | ✅ DONE | — |
| T-024 | **[Durable Functions orchestrator](./tasks/T-024-durable-orchestrator.md)** — workflow: enrich→run_foundry_agents→notify→wait (24h HITL)→more_info loop→execute→finalize; ADR-002 | Gap #3 | 🔴 CRITICAL | ✅ DONE | T-029 |
| T-025 | **[Research Agent](./tasks/T-025-research-agent.md)** — Foundry sub-agent (Connected Agents) + MCP + AzureAISearchTool; підключається до Orchestrator Agent як `AgentTool` | Gap #4 | 🔴 CRITICAL | ✅ DONE | T-024 |
| T-026 | **[Document Agent](./tasks/T-026-document-agent.md)** — Foundry sub-agent (Connected Agents) + template fill; confidence gate в `run_foundry_agents.py` | Gap #4, #5 | 🔴 CRITICAL | ✅ DONE | T-024 |
| T-027 | **[Execution Agent](./tasks/T-027-execution-agent.md)** — Foundry Agent + MCP-QMS + MCP-CMMS (placeholder impl in `run_execution_agent.py`, full Foundry Agent spec pending) | — | 🔴 CRITICAL | 🟡 IN PROGRESS | T-028 |
| T-028 | **[MCP servers](./tasks/T-028-mcp-servers.md)** — mcp-sentinel-db, mcp-qms, mcp-cmms (stdio) | — | 🔴 CRITICAL | ✅ DONE | T-025–T-027 |
| T-029 | **[Human approval flow](./tasks/T-029-human-approval.md)** — POST /decision API + waitForExternalEvent + SignalR | Gap #5 | 🔴 CRITICAL | 🟡 IN PROGRESS | T-030, T-033 |
| T-031 | **[Backend API Functions](./tasks/T-031-backend-api.md)** — incidents CRUD, templates, equipment, batches endpoints | Gap #5 | 🔴 CRITICAL | ✅ DONE | T-032 |
| T-032 | **[React frontend — core](./tasks/T-032-frontend-core.md)** — incident list, details, status timeline | Gap #5 | 🔴 CRITICAL | 🟡 IN PROGRESS | T-033 |
| T-033 | **[React frontend — approval UX](./tasks/T-033-frontend-approval.md)** — decision package view + approve/reject/more-info buttons | Gap #5 | 🔴 CRITICAL | 🟡 IN PROGRESS | finals |

### Важливі (Should-have)

| ID | Задача | Gap / Вимога | Пріоритет | Статус | Блокує |
|---|---|---|---|---|---|
| T-010 | **[Cartoon / анімація «До і Після»](./tasks/T-010-cartoon-animation.md)** | Deliverables | 🟠 HIGH | 🔜 TODO | T-002 |
| T-022 | **[Azure Service Bus setup](./tasks/T-022-service-bus.md)** — alert-queue + DLQ config | Gap #3 | 🟠 HIGH | ✅ DONE | T-023 |
| T-030 | **[Azure SignalR setup](./tasks/T-030-signalr.md)** — negotiate endpoint + notification service + unread notification center contract | Gap #5 | 🟠 HIGH | 🟡 IN PROGRESS | T-033 |
| T-034 | **[React frontend — manager/auditor/IT views](./tasks/T-034-frontend-other-roles.md)** | Gap #5 | 🟠 HIGH | 🔜 TODO | — |
| T-043 | **[Agent telemetry + admin incident view](./tasks/T-043-agent-telemetry-admin-view.md)** — App Insights trace delivery + normalized admin timeline per incident | Gap #4, #5 | 🟠 HIGH | 🟡 IN PROGRESS | T-034 |
| T-045 | **[Evidence citations quality + historical evidence links](./tasks/T-045-evidence-citation-quality.md)** — canonical document cards, strict citation contract, excerpt backfill, unresolved evidence state, historical incident linkability | Gap #4, #5 | 🟠 HIGH | 🟡 IN PROGRESS | — |
| T-035 | **[RBAC setup](./tasks/T-035-rbac.md)** — Entra ID app registration, 5 roles, token validation in Functions | Gap #2 | 🟠 HIGH | ✅ DONE | T-031 |
| T-036 | **[Document ingestion pipeline](./tasks/T-036-ingestion-pipeline.md)** — Blob → chunk → embed → AI Search (one-shot script; live triggers out of scope) | Gap #4 | 🟠 HIGH | ✅ DONE | T-037 |
| T-037 | **[AI Search indexes + mock docs](./tasks/T-037-ai-search.md)** — 5 indexes, 9 docs, 117 chunks з HNSW vector search | Gap #4 | 🟠 HIGH | ✅ DONE | — |
| T-041 | **[Bicep IaC templates](./tasks/T-041-bicep-iac.md)** — infra/main.bicep + modules for all resources | Gap #1, #6 | 🟠 HIGH | ✅ DONE | T-042 |
| T-042 | **[GitHub Actions CI/CD](./tasks/T-042-cicd.md)** — build, test, Bicep deploy, Foundry eval pipeline | Gap #1 | 🟠 HIGH | ✅ DONE | finals |

### Nice-to-have

| ID | Задача | Gap / Вимога | Пріоритет | Статус |
|---|---|---|---|---|
| T-038 | **[Security layer](./tasks/T-038-security.md)** — Key Vault, VNet, Private Endpoints, Managed Identities, retention policy (21 CFR Part 11), data classification | Gap #2 | 🟡 MEDIUM | 🔜 TODO |
| T-039 | **[Reliability layer](./tasks/T-039-reliability.md)** — retry policies, fallback mode, circuit breaker, latency SLOs | Gap #3 | 🟡 MEDIUM | 🟡 IN PROGRESS |
| T-040 | **[RAI layer](./tasks/T-040-rai.md)** — confidence gate impl, Content Safety API, prompt injection guard, eval metrics | Gap #4 | 🟡 MEDIUM | 🟡 IN PROGRESS |

---

## 3. Sprint / Iteration план

> Дедлайн: 1-й тиждень травня 2026. Орієнтовно 2 тижні до submission.

### Week 1 (17–23 квітня) — Infrastructure + Backend + Agents
| День | Задачі |
|---|---|
| 17 квіт | ✅ T-041 · ✅ T-042 · ✅ T-022 · ✅ T-020/T-021 · ✅ T-037 · ✅ T-023 · ✅ T-028 |
| 18–19 квіт | ✅ T-024 (Durable orchestrator + all activities) · ✅ T-025 (Research Agent) · ✅ T-026 (Document Agent) · ✅ T-041 ext (AI Foundry Bicep) |
| 20–21 квіт | T-027 (Execution Agent) · T-029 (Human Approval API) · ✅ T-036 (document ingestion) |
| 22–23 квіт | ✅ T-031 (Backend API) · T-030 (SignalR) · ✅ T-035 (RBAC) |

### Week 2 (24–30 квітня) — Agents + Frontend + Integration
| День | Задачі |
|---|---|
| 24–25 квіт | T-027 (Execution Agent) · T-029 (human approval API) · T-030 (SignalR) |
| 26–27 квіт | ✅ T-031 (backend API) · ✅ T-035 (RBAC) |
| 28–29 квіт | T-032 (React core) · T-033 (approval UX) |
| 30 квіт | T-034 (інші ролі frontend) · T-040 (RAI layer) · T-043 (agent telemetry admin view) |

### Week 3 (1–7 травня) — Polish + Submission
| Підзадача |
|---|
| T-034 (інші ролі frontend) · T-038/039/040 (security/reliability/RAI layers) · T-043 (agent telemetry admin view) |
| T-001 (оновити презентацію) · T-010 (cartoon AS-IS/TO-BE) · T-002 (відео) |
| Final submission |

---

## 4. Definition of Done

Задача вважається завершеною якщо:

**Для архітектурних змін:**
- [ ] Зміна відображена в [02 · Архітектура](./02-architecture.md)
- [ ] Відповідний gap відмічений як "виправлений" в [03 · Аналіз](./03-analysis.md#9-прогрес-виправлення-gaps)
- [ ] Відповідний пункт відмічений у [01 · Вимоги чеклист](./01-requirements.md#10-чеклист-відповідності-живий)
- [ ] Changelog оновлений в [02 · Архітектура §9](./02-architecture.md#9-changelog-архітектури)

**Для коду:**
- [ ] Code у GitHub repo
- [ ] CI pipeline проходить
- [ ] Deployed до dev environment
- [ ] Базовий smoke test проходить

**Для demo scenario:**
- [ ] Один кінцевий сценарій з реальними mock даними
- [ ] Decision package показує recommendation + evidence + SOP reference
- [ ] Human approval flow демонструється
- [ ] Audit trail генерується

---

## 5. Блокери та ризики

| Блокер/Ризик | Опис | Mitigation |
|---|---|---|
| _TBD_ | | |

---

## 6. Задачі — деталі

Кожна задача розписана в окремому файлі в папці [`tasks/`](./tasks/README.md):

| ID | Файл | Примітка |
|---|---|---|
| T-001 | [tasks/T-001-architecture-presentation.md](./tasks/T-001-architecture-presentation.md) | Закрити всі 6 gaps в презентації; architecture slide потрібен для T-002 |
| T-002 | [tasks/T-002-final-video.md](./tasks/T-002-final-video.md) | ⚡ Це вирішить чи переможемо. Детальна структура відео, script, DoD |
| T-010 | [tasks/T-010-cartoon-animation.md](./tasks/T-010-cartoon-animation.md) | Cartoon AS-IS vs TO-BE; блокує T-002 |

---

### Корисні посилання для планування:
- Gaps, які потрібно закрити → [03 · Аналіз](./03-analysis.md#5-топ-6-gaps-для-виправлення)
- Вимоги, що не виконані → [01 · Вимоги чеклист](./01-requirements.md#10-чеклист-відповідності-живий)
- Архітектурні зміни in-progress → [02 · Архітектура §8](./02-architecture.md#8-поточна-версія-in-progress)

---

← [03 Аналіз](./03-analysis.md) · [README →](./README.md)
