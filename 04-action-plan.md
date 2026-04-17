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

**Зараз в роботі:** T-023 (ingestion API) · T-024 (Durable orchestrator)

**Завершено (17 квітня 2026):**
- ✅ T-041 — Bicep IaC: 9 ресурсів задеплоєно (Cosmos DB, Service Bus, Functions, Storage, App Insights, Log Analytics, AI Search, Azure OpenAI)
- ✅ T-042 — GitHub Actions CI/CD: `ci.yml` + `deploy.yml` живі та зелені
- ✅ T-022 — Service Bus: `alert-queue` + DLQ задеплоєно
- ✅ T-020 — Cosmos DB: 6 containers задеплоєно (`templates` container додано 17 квітня), 55 items seeded
- ✅ T-021 — Mock data: 55 items залито в Cosmos DB (`scripts/seed_cosmos.py`)
- ✅ T-037 — AI Search: 5 indexes з HNSW vector search (`srch-sentinel-intel-dev-erzrpo`, westeurope basic SKU); 9 документів завантажено до 4 blob containers; 117 chunks проіндексовано (OpenAI `text-embedding-3-small`); `scripts/upload_documents.py` + `scripts/create_search_indexes.py`

**Наступний крок:** T-023 ingestion API → T-024 Durable orchestrator skeleton

---

## 2. Backlog задач

> Порядок виконання у [§3 Sprint план](#3-sprint--iteration-план).  
> Кожна задача — окремий файл `tasks/T-NNN-*.md`.

### Критичні (Must-have для finals)

| ID | Задача | Gap / Вимога | Пріоритет | Статус | Блокує |
|---|---|---|---|---|---|
| T-001 | **[Оновити архітектурну презентацію](./tasks/T-001-architecture-presentation.md)** — закрити всі gaps, показати реальну збудовану архітектуру (Track A, Security, Reliability, RAI, UX, IaC) | Gap #1–6 | 🔴 CRITICAL | 🔜 TODO | T-002 |
| T-002 | **[5-хвилинне фінальне відео](./tasks/T-002-final-video.md)** — повна demo презентація | Deliverables | 🔴 CRITICAL | 🔜 TODO | finals |
| T-020 | **[Cosmos DB — схема + provisioning](./tasks/T-020-cosmos-db.md)** — 6 collections, indexes, seed script | T-023, T-024 | 🔴 CRITICAL | ✅ DONE | — |
| T-021 | **[Mock data seed](./tasks/T-021-mock-data.md)** — equipment(3), batches(20), incidents(30), templates(2) | demo | 🔴 CRITICAL | ✅ DONE | — |
| T-023 | **[Ingestion API](./tasks/T-023-ingestion-api.md)** — POST /api/alerts + context enrichment + Service Bus publish | Gap #3 | 🔴 CRITICAL | 🔜 TODO | T-024 |
| T-024 | **[Durable Functions orchestrator](./tasks/T-024-durable-orchestrator.md)** — workflow: create→enrich→agents→notify→wait→execute→finalize | Gap #3 | 🔴 CRITICAL | 🔜 TODO | T-029 |
| T-025 | **[Research Agent](./tasks/T-025-research-agent.md)** — Foundry Agent + MCP + RAG tools | Gap #4 | 🔴 CRITICAL | 🔜 TODO | T-024 |
| T-026 | **[Document Agent](./tasks/T-026-document-agent.md)** — Foundry Agent + template fill + confidence gate | Gap #4, #5 | 🔴 CRITICAL | 🔜 TODO | T-024 |
| T-027 | **[Execution Agent](./tasks/T-027-execution-agent.md)** — Foundry Agent + MCP-QMS + MCP-CMMS | — | 🔴 CRITICAL | 🔜 TODO | T-028 |
| T-028 | **[MCP servers](./tasks/T-028-mcp-servers.md)** — mcp-cosmos-db, mcp-qms-mock, mcp-cmms-mock (stdio) | — | 🔴 CRITICAL | 🔜 TODO | T-025–T-027 |
| T-029 | **[Human approval flow](./tasks/T-029-human-approval.md)** — POST /decision API + waitForExternalEvent + SignalR | Gap #5 | 🔴 CRITICAL | 🔜 TODO | T-030, T-033 |
| T-031 | **[Backend API Functions](./tasks/T-031-backend-api.md)** — incidents CRUD, templates, equipment, batches endpoints | Gap #5 | 🔴 CRITICAL | 🔜 TODO | T-032 |
| T-032 | **[React frontend — core](./tasks/T-032-frontend-core.md)** — incident list, details, status timeline | Gap #5 | 🔴 CRITICAL | 🔜 TODO | T-033 |
| T-033 | **[React frontend — approval UX](./tasks/T-033-frontend-approval.md)** — decision package view + approve/reject/more-info buttons | Gap #5 | 🔴 CRITICAL | 🔜 TODO | finals |

### Важливі (Should-have)

| ID | Задача | Gap / Вимога | Пріоритет | Статус | Блокує |
|---|---|---|---|---|---|
| T-010 | **[Cartoon / анімація «До і Після»](./tasks/T-010-cartoon-animation.md)** | Deliverables | 🟠 HIGH | 🔜 TODO | T-002 |
| T-022 | **[Azure Service Bus setup](./tasks/T-022-service-bus.md)** — alert-queue + DLQ config | Gap #3 | 🟠 HIGH | ✅ DONE | T-023 |
| T-030 | **[Azure SignalR setup](./tasks/T-030-signalr.md)** — negotiate endpoint + notification service | Gap #5 | 🟠 HIGH | 🔜 TODO | T-033 |
| T-034 | **[React frontend — manager/auditor/IT views](./tasks/T-034-frontend-other-roles.md)** | Gap #5 | 🟠 HIGH | 🔜 TODO | — |
| T-035 | **[RBAC setup](./tasks/T-035-rbac.md)** — Entra ID app registration, 5 roles, token validation in Functions | Gap #2 | 🟠 HIGH | 🔜 TODO | T-031 |
| T-036 | **[Document ingestion pipeline](./tasks/T-036-ingestion-pipeline.md)** — Blob → blob trigger → chunk → embed → AI Search | Gap #4 | 🟠 HIGH | 🔜 TODO | T-037 |
| T-037 | **[AI Search indexes + mock docs](./tasks/T-037-ai-search.md)** — 5 indexes, 9 docs, 117 chunks з HNSW vector search | Gap #4 | 🟠 HIGH | ✅ DONE | — |
| T-041 | **[Bicep IaC templates](./tasks/T-041-bicep-iac.md)** — infra/main.bicep + modules for all resources | Gap #1, #6 | 🟠 HIGH | ✅ DONE | T-042 |
| T-042 | **[GitHub Actions CI/CD](./tasks/T-042-cicd.md)** — build, test, Bicep deploy, Foundry eval pipeline | Gap #1 | 🟠 HIGH | ✅ DONE | finals |

### Nice-to-have

| ID | Задача | Gap / Вимога | Пріоритет | Статус |
|---|---|---|---|---|
| T-038 | **[Security layer](./tasks/T-038-security.md)** — Key Vault, VNet, Private Endpoints, Managed Identities | Gap #2 | 🟡 MEDIUM | 🔜 TODO |
| T-039 | **[Reliability layer](./tasks/T-039-reliability.md)** — retry policies, fallback mode, circuit breaker, latency SLOs | Gap #3 | 🟡 MEDIUM | 🔜 TODO |
| T-040 | **[RAI layer](./tasks/T-040-rai.md)** — confidence gate impl, Content Safety API, prompt injection guard, eval metrics | Gap #4 | 🟡 MEDIUM | 🔜 TODO |

---

## 3. Sprint / Iteration план

> Дедлайн: 1-й тиждень травня 2026. Орієнтовно 2 тижні до submission.

### Week 1 (17–23 квітня) — Infrastructure + Backend + Agents
| День | Задачі |
|---|---|
| 17 квіт | ✅ T-041 (Bicep IaC) · ✅ T-042 (CI/CD) · ✅ T-022 (Service Bus) · ✅ T-020/T-021 (Cosmos + seed) · ✅ T-037 (AI Search indexes + 117 chunks) |
| 18–19 квіт | T-023 (ingestion API) · T-028 (MCP servers) |
| 20–21 квіт | T-023 (ingestion API) · T-036 (document ingestion) |
| 22–23 квіт | T-024 (Durable orchestrator) · T-025 (Research Agent) · T-026 (Document Agent) |

### Week 2 (24–30 квітня) — Agents + Frontend + Integration
| День | Задачі |
|---|---|
| 24–25 квіт | T-027 (Execution Agent) · T-029 (human approval API) · T-030 (SignalR) |
| 26–27 квіт | T-031 (backend API) · T-035 (RBAC) |
| 28–29 квіт | T-032 (React core) · T-033 (approval UX) |
| 30 квіт | T-034 (інші ролі frontend) · T-040 (RAI layer) |

### Week 3 (1–7 травня) — Polish + Submission
| Підзадача |
|---|
| T-034 (інші ролі frontend) · T-038/039/040 (security/reliability/RAI layers) |
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
