# Hackathon Scope vs Target Architecture — Compromises & Post-Hackathon Backlog

> **Призначення цього документа.** [`02-architecture.md`](../02-architecture.md) описує **цільову архітектуру** Sentinel Intelligence — те, як система має виглядати у production. Цей документ фіксує, що з цільової архітектури було свідомо скорочено для хакатонного прототипу, з яких причин, і куди це винесено у roadmap.
>
> Для суддів/архітектурного огляду: **архітектура розроблена повністю**, демо показує прототип її критичних шляхів (alert → multi-agent reasoning → human approval → execution + audit).

← [README](../README.md) · [02 Архітектура](../02-architecture.md) · [04 План дій](../04-action-plan.md)

---

## Зміст

1. [Принцип скорочення](#1-принцип-скорочення)
2. [Що реалізовано у прототипі](#2-що-реалізовано-у-прототипі)
3. [Security — компроміси](#3-security--компроміси)
4. [Reliability — компроміси](#4-reliability--компроміси)
5. [Operational Excellence & Performance — компроміси](#5-operational-excellence--performance--компроміси)
6. [Responsible AI — компроміси](#6-responsible-ai--компроміси)
7. [Data & Integration — компроміси](#7-data--integration--компроміси)
8. [Post-hackathon backlog — задачі](#8-post-hackathon-backlog--задачі)
9. [WAR assessment mapping](#9-war-assessment-mapping)

---

## 1. Принцип скорочення

Цільова архітектура повністю спроектована як production-ready GMP-система. Для демо ми залишаємо:

- всі **структурні елементи** (сервіси, потоки даних, контракти API, схему даних);
- всі **AI-специфічні механізми** (multi-agent pipeline, HITL, confidence gate, evidence citations, agent observability);
- **audit trail + RBAC** (бо це ядро GxP-цінності рішення).

Скорочено все, що вимагає:

- **Entra ID P2 ліцензії** (Conditional Access, PIM) — недоступно у хакатонському sandbox;
- **Flex Consumption / Premium plan** (VNet Integration, Private Endpoints) — хакатон використовує Consumption Y1;
- **Multi-region, DR-тестування, load testing, chaos engineering** — операційні активності, що виходять за межі 10-денного демо;
- **Формальні процеси** (red-team testing, model governance lifecycle) — людські процеси, не код.

---

## 2. Що реалізовано у прототипі

Демо покриває **критичний шлях** цільової архітектури end-to-end:

- POST `/api/alerts` → Service Bus `alert-queue` (з DLQ та retry);
- Durable Functions orchestrator: `create_incident` → `enrich_context` → `run_foundry_agents` → `notify_operator` → `waitForExternalEvent` → `run_execution_agent` → `finalize_audit`;
- Foundry Connected Agents pipeline: Orchestrator Agent → Research Agent (5 RAG indexes + MCP sentinel-db) → Document Agent (confidence gate 0.7) → Execution Agent (MCP-QMS + MCP-CMMS);
- Cosmos DB з 8 containers (`incidents`, `incident_events`, `notifications`, `equipment`, `batches`, `capa-plans`, `approval-tasks`, `templates`);
- Azure AI Search з 5 indexes (SOP, equipment manuals, GMP policies, BPR, incident history);
- Azure SignalR push для real-time UX (operator approve/reject/more_info);
- React + Vite SPA на Azure Static Web Apps, MSAL-авторизація, 5 RBAC ролей;
- Azure Key Vault + Managed Identities;
- Application Insights з `FOUNDRY_PROMPT_TRACE` структурованими traces;
- Bicep IaC (`infra/main.bicep` + 5 модулів), GitHub Actions CI/CD.

Усі компоненти, описані в [`02-architecture.md`](../02-architecture.md), є у коді або задеплоєні — скорочені лише посилені production-конфігурації, перераховані нижче.

---

## 3. Security — компроміси

### 3.1 Network isolation (SE:06)

**Цільовий дизайн:** VNet 10.0.0.0/16, `snet-functions` + `snet-private-endpoints`, Private Endpoints для Cosmos / AI Search / Service Bus / Storage / Key Vault / Azure OpenAI, `publicNetworkAccess = Disabled` для всіх PaaS, Private DNS Zones.

**Hackathon:** Consumption Y1 plan **не підтримує** VNet Integration → PaaS endpoint-и публічні, захищені Managed Identity + RBAC + HTTPS-only.

**Що знімає ризик у прототипі:** всі звернення до Cosmos / Service Bus / AI Search / Key Vault йдуть тільки через Managed Identity Function App-у; немає shared keys у коді; App Registration має `assignment_required = true`.

**Follow-up:** [T-047 — Network isolation (VNet + PE)](../tasks/)

### 3.2 Privileged access & MFA (SE:05)

**Цільовий дизайн:**

- Conditional Access: MFA для всіх users, блокування non-EU countries (pharma compliance), `compliant device` для IT Admin;
- Azure PIM: JIT-eligible активація Contributor для IT Admin (1–4h з justification), eligible Reviewer для QA Manager;
- Entra Security Groups: `sg-sentinel-operators`, `sg-sentinel-qa-managers`, `sg-sentinel-auditors`, `sg-sentinel-it-admin`, Lifecycle Workflows для onboarding/offboarding.

**Hackathon:** CA та PIM потребують Entra ID **P2 ліцензії** — недоступні у sandbox. У прототипі реалізовано 5 RBAC-ролей через App Roles + assignment_required; MFA не enforcement-ується policy-ю.

**Follow-up:** [T-048 — Conditional Access + PIM](../tasks/)

### 3.3 Easy wins — Defender, tagging, legacy auth, secret rotation

**Цільовий дизайн:**

- Microsoft Defender for Cloud для App Service + Key Vault (`Microsoft.Security/pricings`);
- Теги `environment`, `team`, `cost-center`, `data-classification` на кожному ресурсі;
- CA-блокування Basic/NTLM/legacy OAuth;
- Key Vault `rotationPolicy` на всіх secrets (90 днів) + Event Grid trigger.

**Hackathon:** не enabled — технічно прості Bicep/config зміни (≤ 4h), не входять у 10-денний демо-скоуп.

**Follow-up:** [T-049 — WAR easy wins](../tasks/)

---

## 4. Reliability — компроміси

### 4.1 Реалізовано у прототипі

- Service Bus DLQ + 3 auto-retries на `alert-queue`;
- Durable Functions `RetryPolicy(max_number_of_attempts=3, first_retry_interval=5s)` з exponential backoff на всіх activities;
- Cosmos DB Serverless autoscale;
- `MAX_MORE_INFO_ROUNDS=3` — захист від нескінченного `more_info` циклу;
- 24h HITL timeout → auto-escalate path через Durable `create_timer`;
- App Insights structured logging + exception tracking.

### 4.2 Post-hackathon (T-039, T-050)

**Цільовий дизайн:**

- **Fallback mode:** якщо Foundry Agent fail → degraded mode: operator отримує pre-filled manual CAPA template замість AI-рекомендацій;
- **Circuit breaker:** 3 послідовні Foundry failures → circuit open → fallback; auto-reset за 60s;
- **Latency SLOs + Azure Monitor alerts:** P95 POST `/api/alerts` < 2s; P95 GET `/incidents` < 500ms; E2E agent pipeline < 120s;
- **Chaos experiments:** Azure Chaos Studio сценарії (Foundry timeout, Service Bus unavailability, Cosmos throttling);
- **Multi-region DR:** Cosmos DB geo-redundancy + AI Search replica у secondary region;
- **Recovery runbook:** документований процес відновлення incident-ів, що застрягли після max retries + DLQ depth alert.

**Чому не у демо:** fallback mode потребує окремого manual-CAPA UX; chaos/DR — операційні активності з горизонтом тижні.

**Follow-up:** [T-039 — Production reliability](../tasks/), [T-050 — Recovery runbook + DLQ alert](../tasks/)

---

## 5. Operational Excellence & Performance — компроміси

### 5.1 Azure Load Testing (PE:05/06)

**Цільовий дизайн:** Azure Load Testing з Locust/JMeter:

- `scenario-alert-spike` — POST `/api/alerts` × 200 RPS протягом 5 хв;
- `scenario-signalr-concurrent` — 200 SignalR clients, join/leave incident groups;
- `scenario-agent-pipeline` — 10 concurrent orchestrations end-to-end;
- `scenario-api-read` — GET `/incidents` × 500 RPS, P95 < 500ms.

Очікуваний production load:

- Alert ingestion spike: 50–200 concurrent при batch-close зміни;
- SignalR: 50–200 operator sessions одночасно;
- Foundry agent: 5–10 concurrent orchestrations (30–120s кожна);
- API P95 < 500ms (read), P95 < 2s (POST `/alerts`).

**Hackathon:** не реалізовано. Flex Consumption + Cosmos Serverless мають автоскейл без manual tuning; load test валідує cold start та Cosmos RU throttling ризики.

**Follow-up:** [T-051 — Load testing scenarios](../tasks/)

### 5.2 Cost alerts (CO:04)

**Цільовий дизайн:** `Microsoft.Consumption/budgets` + alert rule → email на $X/місяць.

**Hackathon:** не налаштовано.

**Follow-up:** [T-049 — WAR easy wins](../tasks/)

---

## 6. Responsible AI — компроміси

### 6.1 Реалізовано у прототипі

- Confidence gate 0.7: якщо `confidence < 0.7` → UI помічає рекомендацію як `LOW_CONFIDENCE`, operator comment обов'язковий; якщо ще й немає evidence → `BLOCKED` + авто-ескалація QA Manager;
- Evidence citation contract: `document_id` + section + excerpt + relevance score; backend verification pass (document existence, section claim, excerpt anchor) — див. [`02-architecture.md` §7.2](../02-architecture.md);
- Mandatory human approval перед будь-яким execution;
- Повний audit trail у `incident_events` + `FOUNDRY_PROMPT_TRACE` в App Insights;
- Azure Content Safety API — output screening перед відправкою оператору (partial, без Prompt Shield).

### 6.2 Post-hackathon (T-040)

**Цільовий дизайн:**

- **Prompt injection detection:** Azure Content Safety Prompt Shield на SCADA input + operator messages;
- **Model versioning + rollback:** Foundry governed deployment — кожна версія агента проходить eval pipeline перед promotion, rollback за 1 команду;
- **Formal evaluation pipeline:** Groundedness / Coherence / Relevance / F1 через Azure AI Foundry Evaluation, нічні прогони з thresholds;
- **Hallucination rate dashboard:** тренд accuracy per agent per тиждень → App Insights custom workbook;
- **Red-team testing protocol:** формальна red-team сесія для GMP-критичних рекомендацій перед production deploy.

**Follow-up:** [T-040 — Production RAI controls](../tasks/)

---

## 7. Data & Integration — компроміси

### 7.1 Зовнішні системи

**Цільовий дизайн:** інтеграції з production SCADA/MES/CMMS/QMS через REST/OPC UA/файлові обміни.

**Hackathon:** усі зовнішні системи симулюються:

- SCADA/MES → `scripts/simulate_alerts.py` публікує alert-и у Service Bus;
- CMMS → MCP server `mcp-cmms` пише у Cosmos `capa-plans` (без реальної інтеграції);
- QMS → MCP server `mcp-qms` пише у Cosmos `approval-tasks`;
- Equipment/batches — seed dataset у Cosmos (`scripts/seed_cosmos.py`).

Контракти MCP tools ідентичні production — перехід на реальні системи відбувається через заміну backend implementation MCP сервера без зміни агентів.

### 7.2 MCP transport

**Цільовий дизайн:** MCP servers як окремі hosted сервіси (HTTP/SSE transport) з власною аутентифікацією через Managed Identity.

**Hackathon:** MCP servers запускаються як stdio subprocess з Function App (локальний transport).

**Follow-up:** винесення MCP servers у окремі Azure Functions або Container Apps — частина [T-039](../tasks/).

### 7.3 Document ingestion — Blob containers

**Цільовий дизайн:** 5 окремих Blob containers (`blob-sop`, `blob-manuals`, `blob-gmp`, `blob-bpr`, `blob-history`) з 5 Azure Function blob triggers → 5 AI Search indexes.

**Hackathon:** 1 container `documents` з path-based routing; решта containers у roadmap.

**Follow-up:** [T-036 — Document ingestion pipeline](../tasks/), [T-041 — Blob containers у Bicep](../tasks/)

---

## 8. Post-hackathon backlog — задачі

| Задача | Область | Оцінка | WAR items |
|---|---|---|---|
| T-039 — Production reliability (fallback, circuit breaker, SLOs, chaos, multi-region DR) | Reliability | ~2 тижні | RE:05, RE:08, RE:09, PE:05/06 |
| T-040 — Production RAI (prompt injection, model governance, eval pipeline, red-team) | Responsible AI | ~2 тижні | SE:08, OE:11, PE:06 |
| T-047 — Network isolation (VNet + Private Endpoints + Private DNS) | Security | ~3 дні | SE:06 |
| T-048 — Conditional Access + Azure PIM | Security | ~2 дні | SE:05 |
| T-049 — WAR easy wins (Defender, tags, legacy auth block, secret rotation, cost alerts) | Security + Cost | ~4 години | SE:03, SE:08, SE:09, SE:10, CO:04 |
| T-050 — Recovery runbook + DLQ depth alert | Reliability | ~1 день | RE:09 |
| T-051 — Azure Load Testing scenarios | Performance | ~1 тиждень | PE:05/06 |

---

## 9. WAR assessment mapping

Зведена відповідність цільової архітектури WAR best practices та статус у прототипі.

| WAR Item | Priority | Target design у [`02-architecture.md`](../02-architecture.md) | Прототип | Post-hackathon |
|---|---|---|---|---|
| SE:03 — Resource tagging | — | Теги на кожному Bicep module | Partial (env only) | T-049 |
| SE:05 P:100 — Limit high-privilege accounts | 100 | RBAC 5 ролей + no shared accounts | Реалізовано | — |
| SE:05 P:95 — CA + JIT | 95 | Entra CA + Azure PIM | Not implemented (P2 license) | T-048 |
| SE:06 P:90 — DDoS + firewall for ingress | 90 | HTTPS + WAF + ingress firewall | Partial (HTTPS + RBAC) | T-047 |
| SE:06 P:80 — NSG + PE for PaaS | 80 | VNet + PE | Not implemented | T-047 |
| SE:06 P:70 — Private DNS, no public PaaS | 70 | `publicNetworkAccess = Disabled` | Not implemented | T-047 |
| SE:08 — Block legacy auth | — | CA rule | Not configured | T-049 |
| SE:08 — Prompt injection defense | — | Azure Content Safety Prompt Shield | Partial (Content Safety output) | T-040 |
| SE:09 — Secret rotation | — | Key Vault rotationPolicy 90d | Manual | T-049 |
| SE:10 P:90 — Defender for Cloud | 90 | Defender App Service + KV | Not enabled | T-049 |
| RE:05 — Multi-region DR | — | Cosmos geo-redundancy + AI Search replica | Single region | T-039 |
| RE:08 — Chaos experiments | — | Azure Chaos Studio scenarios | Not implemented | T-039 |
| RE:09 P:60 — Recovery procedures | 60 | Runbook + DLQ alert + fallback mode | Durable retry + DLQ exist | T-050, T-039 |
| PE:05/06 — Load testing + perf monitoring | — | Locust/JMeter + SLO alerts | Not implemented | T-051, T-039 |
| OE:11 — Model governance lifecycle | — | Foundry versioning + rollback + eval gate | Partial (manual eval) | T-040 |
| CO:04 — Cost budgets + alerts | — | `Microsoft.Consumption/budgets` | Not configured | T-049 |

---

← [02 Архітектура](../02-architecture.md) · [04 План дій](../04-action-plan.md)
