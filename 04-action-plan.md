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

**Зараз в роботі:** T-027 (Execution Agent — placeholder impl, full Foundry Agent spec pending) · T-034 (manager/auditor/IT-admin views — manager stats contract hardening) · T-039 (Reliability hardening) · T-040 (RAI observability)

> **ADR-002 — Foundry Connected Agents:** Research Agent + Document Agent реалізовані як sub-agents Foundry Orchestrator Agent.  
> Durable викликає одну activity `run_foundry_agents` — Foundry керує pipeline Research → Document нативно.  
> `more_info` loop: Durable накопичує `operator_questions`, знову запускає `run_foundry_agents`. Foundry керує internal iterations.  
> Дивись [02-architecture §8.10b](./02-architecture.md#810b-adr-002-foundry-connected-agents-vs-ручна-оркестрація).





**Наступний крок:** T-034 (frontend manager/auditor/IT views) → T-001 architecture presentation → T-002 final video

---

## 2. Backlog задач

> Порядок виконання у [§3 Sprint план](#3-sprint--iteration-план).  
> Кожна задача — окремий файл `tasks/T-NNN-*.md`.

### Критичні (Must-have для finals)

| ID | Задача | Gap / Вимога | Пріоритет | Статус | Блокує |
|---|---|---|---|---|---|
| T-001 | **[Оновити архітектурну презентацію](./tasks/T-001-architecture-presentation.md)** — закрити всі gaps, показати реальну збудовану архітектуру (Track A, Security, Reliability, RAI, UX, IaC) | Gap #1–6 | 🔴 CRITICAL | 🔜 TODO | T-002 |
| T-002 | **[5-хвилинне фінальне відео](./tasks/T-002-final-video.md)** — demo-first app walkthrough + architecture slides | Deliverables | 🔴 CRITICAL | 🔜 TODO | finals |
| T-020 | **[Cosmos DB — схема + provisioning](./tasks/T-020-cosmos-db.md)** — 8 containers, indexes, seed script | T-023, T-024 | 🔴 CRITICAL | ✅ DONE | — |
| T-021 | **[Mock data seed](./tasks/T-021-mock-data.md)** — equipment(3), batches(20), incidents(30), templates(2) | demo | 🔴 CRITICAL | ✅ DONE | — |
| T-023 | **[Ingestion API](./tasks/T-023-ingestion-api.md)** — POST /api/alerts + context enrichment + Service Bus publish | Gap #3 | 🔴 CRITICAL | ✅ DONE | — |
| T-024 | **[Durable Functions orchestrator](./tasks/T-024-durable-orchestrator.md)** — workflow: enrich→run_foundry_agents→notify→wait (24h HITL)→more_info loop→execute→finalize; ADR-002 | Gap #3 | 🔴 CRITICAL | ✅ DONE | T-029 |
| T-025 | **[Research Agent](./tasks/T-025-research-agent.md)** — Foundry sub-agent (Connected Agents) + MCP + AzureAISearchTool; підключається до Orchestrator Agent як `AgentTool` | Gap #4 | 🔴 CRITICAL | ✅ DONE | T-024 |
| T-026 | **[Document Agent](./tasks/T-026-document-agent.md)** — Foundry sub-agent (Connected Agents) + template fill; confidence gate в `run_foundry_agents.py` | Gap #4, #5 | 🔴 CRITICAL | ✅ DONE | T-024 |
| T-027 | **[Execution Agent](./tasks/T-027-execution-agent.md)** — Foundry Agent + MCP-QMS + MCP-CMMS (placeholder impl in `run_execution_agent.py`, full Foundry Agent spec pending) | — | 🔴 CRITICAL | 🟡 IN PROGRESS | T-028 |
| T-028 | **[MCP servers](./tasks/T-028-mcp-servers.md)** — mcp-sentinel-db, mcp-qms, mcp-cmms (stdio) | — | 🔴 CRITICAL | ✅ DONE | T-025–T-027 |
| T-029 | **[Human approval flow](./tasks/T-029-human-approval.md)** — POST /decision API + waitForExternalEvent | Gap #5 | 🔴 CRITICAL | ✅ DONE | — |
| T-031 | **[Backend API Functions](./tasks/T-031-backend-api.md)** — incidents CRUD, templates, equipment, batches endpoints | Gap #5 | 🔴 CRITICAL | ✅ DONE | T-032 |
| T-032 | **[React frontend — core](./tasks/T-032-frontend-core.md)** — incident list, details, status timeline | Gap #5 | 🔴 CRITICAL | ✅ DONE | — |
| T-033 | **[React frontend — approval UX](./tasks/T-033-frontend-approval.md)** — decision package view + approve/reject/more-info buttons | Gap #5 | 🔴 CRITICAL | ✅ DONE | — |

### Важливі (Should-have)

| ID | Задача | Gap / Вимога | Пріоритет | Статус | Блокує |
|---|---|---|---|---|---|
| T-010 | **[Cartoon / анімація «До і Після»](./tasks/T-010-cartoon-animation.md)** — descoped for finals, optional post-submission asset | Deliverables | 🟡 LOW | ✅ CLOSED | — |
| T-022 | **[Azure Service Bus setup](./tasks/T-022-service-bus.md)** — alert-queue + DLQ config | Gap #3 | 🟠 HIGH | ✅ DONE | T-023 |
| T-030 | **[Azure SignalR setup](./tasks/T-030-signalr.md)** — negotiate endpoint + notification service + unread notification center contract | Gap #5 | 🟠 HIGH | ✅ DONE | T-033 |
| T-034 | **[React frontend — manager/auditor/IT views](./tasks/T-034-frontend-other-roles.md)** | Gap #5 | 🟠 HIGH | ✅ DONE | — |
| T-043 | **[Agent telemetry + admin incident view](./tasks/T-043-agent-telemetry-admin-view.md)** — App Insights trace delivery + normalized admin timeline per incident | Gap #4, #5 | 🟠 HIGH | ✅ DONE | — |
| T-045 | **[Evidence citations quality + historical evidence links](./tasks/T-045-evidence-citation-quality.md)** — canonical document cards, strict citation contract, excerpt backfill, unresolved evidence state, historical incident linkability | Gap #4, #5 | 🟠 HIGH | ✅ DONE | — |
| T-035 | **[RBAC setup](./tasks/T-035-rbac.md)** — Entra ID app registration, 5 roles, token validation in Functions | Gap #2 | 🟠 HIGH | ✅ DONE | T-031 |
| T-036 | **[Document ingestion pipeline](./tasks/T-036-ingestion-pipeline.md)** — Blob → chunk → embed → AI Search (one-shot script; live triggers out of scope) | Gap #4 | 🟠 HIGH | ✅ DONE | T-037 |
| T-037 | **[AI Search indexes + mock docs](./tasks/T-037-ai-search.md)** — 5 indexes, 9 docs, 117 chunks з HNSW vector search | Gap #4 | 🟠 HIGH | ✅ DONE | — |
| T-041 | **[Bicep IaC templates](./tasks/T-041-bicep-iac.md)** — infra/main.bicep + modules for all resources | Gap #1, #6 | 🟠 HIGH | ✅ DONE | T-042 |
| T-042 | **[GitHub Actions CI/CD](./tasks/T-042-cicd.md)** — build, test, Bicep deploy, Foundry eval pipeline | Gap #1 | 🟠 HIGH | ✅ DONE | finals |

### Nice-to-have

| ID | Задача | Gap / Вимога | Пріоритет | Статус |
|---|---|---|---|---|
| T-046 | **[Foundry Agent code hardening](./tasks/T-046-foundry-agent-code-hardening.md)** — post-demo cleanup: видалити `_infer_known_document()` хардкод, замінити keyword-matching `_has_direct_stop_requirement()` на LLM-відповідь у Document Agent prompt, додати `agent_recommendation: APPROVE | REJECT` в Document Agent output schema, прибрати startup sleep з Activity, додати `RAG_TOP_K`/`RAG_EXCERPT_CHARS` env vars | post-demo | 🟢 LOW | 🔜 TODO |

### Post-hackathon (Security, Reliability, RAI & Operational Excellence)

> Архітектурно задокументовані в §8.15 (Security), §8.17 (Reliability), §8.18 (RAI), §8.16 (Operational Excellence) — показуємо що знаємо і задизайновано; реалізація після finals.

| ID | Задача | Gap / §Arch | Пріоритет | Статус |
|---|---|---|---|---|
| T-038 | **[Security layer](./tasks/T-038-security.md)** — Managed Identities для всіх Functions, Key Vault managed identity auth, retention policy (21 CFR Part 11), data classification tags | Gap #2, §8.15 | 🟡 MEDIUM | 🔜 TODO |
| T-039 | **[Reliability layer](./tasks/T-039-reliability.md)** — fallback mode (degraded manual CAPA), circuit breaker для Foundry calls, latency SLO alerts, chaos experiments baseline | Gap #3, §8.17 | 🟡 MEDIUM | 🔜 TODO |
| T-040 | **[RAI layer](./tasks/T-040-rai.md)** — prompt injection guard (Content Safety Prompt Shield), model versioning + rollback via Foundry governed deployment, formal eval pipeline (groundedness/coherence/relevance), low-confidence escalation UI state | Gap #4, §8.18 | 🟡 MEDIUM | 🔜 TODO |

| ID | Задача | WAR Gap | Пріоритет | Статус |
|---|---|---|---|---|
| T-047 | **[VNet / NSGs / Private Endpoints](./tasks/T-047-vnet-private-endpoints.md)** — Function App → Flex Consumption; VNet 10.0.0.0/16 з 2 subnets; NSGs; Private Endpoints для Cosmos DB, AI Search, Service Bus, Storage, Key Vault, Azure OpenAI; Private DNS Zones; `publicNetworkAccess=Disabled` на всіх PaaS | SE:06 | 🟡 MEDIUM | 🔜 TODO |
| T-048 | **[JIT / Conditional Access](./tasks/T-048-jit-conditional-access.md)** — 4 Entra ID Security Groups; CA Policy: MFA для всіх, block non-EU, compliant device для IT Admin; Azure PIM eligible Contributor для IT Admin (JIT 1-4h); Lifecycle Workflows для onboarding/offboarding | SE:05 | 🟡 MEDIUM | 🔜 TODO |
| T-049 | **[WAR Easy Wins — Security & Cost](./tasks/T-049-war-easy-wins.md)** — Defender for Cloud (SE:10), resource tags (SE:03), block legacy auth (SE:08), KV secret rotation (SE:09), Azure Budget alerts (CO:04) — ~4h, all Bicep/config changes | SE:03/08/09/10, CO:04 | 🟢 LOW | 🔜 TODO |
| T-050 | **[Recovery Procedures Runbook](./tasks/T-050-recovery-runbook.md)** — розширити `docs/operations-runbook.md` з 3 recovery сценаріями (orchestrator hang, DLQ, Foundry timeout) + DLQ depth Azure Monitor alert у Bicep | RE:09 | 🟢 LOW | 🔜 TODO |
| T-051 | **[Azure Load Testing](./tasks/T-051-load-testing.md)** — 4 Locust scenarios (alert spike 200 RPS, SignalR 200 concurrent, agent E2E 10 parallel, read API 500 RPS); Azure Load Testing resource у Bicep; GitHub Actions CI gate | PE:05/06 | 🟡 MEDIUM | 🔜 TODO |
| T-055 | **[AI pipeline status contract hardening](./tasks/T-055-ai-pipeline-status-contract.md)** — прибрати demo workaround і виправити backend status contract: `ingested/analyzing/awaiting_agents` мають реально ставитися в Cosmos, а `incident_status_changed` / `agent_step_completed` мають реально летіти через SignalR; cleanup legacy `queued` / `analyzing_agents` у watchdog | Gap #3, UX consistency, T-024/T-030/T-031 | 🟡 MEDIUM | 🔜 TODO |

### Нові задачі (HITL UX hardening)

| ID | Задача | Gap / Вимога | Пріоритет | Статус |
|---|---|---|---|---|
| T-052 | **[Editable WO / Audit entry forms](./tasks/T-052-editable-wo-audit-forms.md)** — WO draft та audit entry draft в approval UI як pre-filled редаговані поля (operator/QA може змінювати); порожні + обов'язкові при BLOCKED-стані; інші ролі read-only; backend payload з верифікованого drafts передається до CMMS/QMS | Gap #5, HITL | 🟠 HIGH | 🔜 TODO |
| T-053 | **[Alert feedback loop](./tasks/T-053-alert-feedback-loop.md)** — при Reject: async POST до `ALERT_FEEDBACK_URL` (configurable, optional); payload з `source_alert_id`, `outcome`, `operator_agrees_with_agent`; retry 3×; event у `incident_events`; frontend показує статус в timeline | SCADA/MES learning | 🟡 MEDIUM | 🔜 TODO |
| T-054 | **[Agent recommendation visibility](./tasks/T-054-agent-recommendation-visibility.md)** — `agent_recommendation: APPROVE\|REJECT` скрізь: badge в ApprovalPanel (над кнопками), AI-колонка в IncidentTable + IncidentHistoryPage, AiVsHumanBadge в AuditTrail, agreement rate KPI у RecentDecisions; backend: зберігати в `ai_analysis`, `finalDecision`, `recent_decisions` stats | Demo story, Analytics | 🟠 HIGH | 🔜 TODO |

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
| 28–29 квіт | ✅ T-032 (React core) · ✅ T-033 (approval UX) |
| 30 квіт | T-034 (інші ролі frontend) · T-040 (RAI layer) · T-043 (agent telemetry admin view) |

### Week 3 (1–7 травня) — Polish + Submission
| Підзадача |
|---|
| T-034 (інші ролі frontend) · T-038/039/040 (security/reliability/RAI layers) · T-043 (agent telemetry admin view) |
| T-001 (оновити презентацію) · T-002 (demo-first відео) |
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
- [ ] Evidence verification state показує **verified** vs **unresolved** citations окремо
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
| T-010 | [tasks/T-010-cartoon-animation.md](./tasks/T-010-cartoon-animation.md) | Descoped for finals; optional storytelling asset after submission |

---

### Корисні посилання для планування:
- Gaps, які потрібно закрити → [03 · Аналіз](./03-analysis.md#5-топ-6-gaps-для-виправлення)
- Вимоги, що не виконані → [01 · Вимоги чеклист](./01-requirements.md#10-чеклист-відповідності-живий)
- Архітектурні зміни in-progress → [02 · Архітектура §8](./02-architecture.md#8-поточна-версія-in-progress)

---

← [03 Аналіз](./03-analysis.md) · [README →](./README.md)
