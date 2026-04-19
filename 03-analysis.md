# 03 · Аналіз архітектури

← [README](./README.md) · [01 Вимоги](./01-requirements.md) · [02 Архітектура](./02-architecture.md) · [04 План дій](./04-action-plan.md)

> **Призначення:** Аналіз поданого рішення — що добре, що потрібно виправити. Базується на офіційному Triage Report від 30 березня 2026. Оновлюємо при кожній ітерації архітектури.

---

## Зміст
1. [Тріаж-звіт (30 березня 2026)](#1-тріаж-звіт-30-березня-2026)
2. [Architecture Dimensions](#2-architecture-dimensions)
3. [Use Case Dimensions](#3-use-case-dimensions)
4. [Сильні сторони](#4-сильні-сторони)
5. [Топ-6 Gaps для виправлення](#5-топ-6-gaps-для-виправлення)
6. [Azure WAF Gaps](#6-azure-waf-gaps)
7. [Azure AI Pillar Gaps](#7-azure-ai-pillar-gaps)
8. [Cross-cutting перевірки](#8-cross-cutting-перевірки)
9. [Прогрес виправлення gaps](#9-прогрес-виправлення-gaps)

---

## 1. Тріаж-звіт (30 березня 2026)

> Джерело: `docs/triage-report-sentinel-intelligence-20260330_175839.pdf`  
> Система оцінювання: AI-powered triage system (Capgemini + Microsoft)

### Загальний результат

| Категорія | Бали | Максимум |
|---|---|---|
| Architecture | 33 | 50 |
| Use Case | 38 | 50 |
| **TOTAL** | **71** | **100** |

**Вердикт: Good — 71/100**

### Короткий summary від тріажу
> Sentinel Intelligence proposes an AI Foundry-based Operations Assistant for GMP manufacturing that detects anomaly/deviation events from SCADA/MES/IoT signals, enriches them with batch/equipment context, grounds decisions in SOP/BPR/CAPA history via RAG, generates CAPA recommendations and audit-ready reports, and keeps a human approval step before work-order execution.

---

## 2. Architecture Dimensions

| Dimension | Оцінка | Обґрунтування | Gaps |
|---|---|---|---|
| **Clarity & Flow** | 8/10 | Потік detect → context → compliance → CAPA → approval → record чіткий. Agent ролі та data sources видимі. Exception paths і runtime decision logic залишаються high-level. | Exception paths не described, model decision logic не деталізований |
| **Platform Fit** | 7/10 | Azure Functions, Azure AI Search, Foundry Agent Service — правильний вибір для event ingestion, RAG, multi-agent. Але: **track не задекларований**, full developer/platform setup не показаний. | Track A не вказаний, GitHub + CI/CD відсутні |
| **Data / Governance / Security** | 6/10 | Data sources та governed retrieval добре ідентифіковані. Human approval та audit logging. Але: identity, access control, encryption, retention, classification, private connectivity, content safety — **не описані**. | Весь security шар відсутній |
| **Reliability / Performance / Cost** | 5/10 | KPI < 5 хв показує performance intent. Але: retries, queues, failure recovery, fallback, model timeout, cost controls, token optimization — **не визначені**. | Весь reliability шар відсутній |
| **Scalability / Integration / Provisioning** | 7/10 | Enterprise integrations чітко ідентифіковані. Azure сервіси названі. Але: **немає IaC**, API contract детей, environment topology, repeatable provisioning. | IaC/deployment відсутній |

---

## 3. Use Case Dimensions

| Dimension | Оцінка | Обґрунтування | Gaps |
|---|---|---|---|
| **Value & KPI Impact** | 9/10 | High-value regulated process. Чіткі business pain points, explicit KPI impact (decision time, QA effort, errors, inspection readiness). Value quantification може бути більш evidence-based. | KPI evidence-base можна посилити |
| **Innovation** | 8/10 | Комбінація: predictive signal interpretation + GMP compliance validation + CAPA recommendation + audit trail — більш диференційована ніж basic chatbot/anomaly detector. Thoughtful multi-agent design tied to regulated workflow. | — |
| **AI Fit** | 8/10 | AI добре підходить для contextual retrieval, historical pattern interpretation, recommendation drafting, evidence packaging. Human approval важливий для GxP. Але: **Responsible AI controls не explicit**. | RAI не деталізований |
| **UX Simplicity** | 6/10 | Process-level description є, але **actual user interface/channel не описаний**. Ease of use, explainability, approval ergonomics — не можна оцінити. | Operator UI не визначений |
| **Build–Scale–Reuse** | 7/10 | MVP feasible при звуженні до 1 asset type, 1 deviation class, small SOP/CAPA set. Retrieval та agent patterns reusable. Але: **reusable MCP assets/connectors та production-scale constraints не конкретизовані**. | MVP scope не звужений |

---

## 4. Сильні сторони

> Зберігаємо та підтримуємо в наступних ітераціях:

### Architecture
- ✅ **Clarity & Flow** — detect → context → compliance → CAPA → human approval → record: чітко і легко зрозуміло
- ✅ **Platform Fit** — Azure Functions (event-driven ingest), Azure AI Search (RAG), Foundry Agent Service (orchestration): правильний вибір для GMP сценарію
- ✅ **Governance-aware design** — SOP/BPR/CAPA grounding, mandatory human review, audit logging відповідають regulated manufacturing
- ✅ **Enterprise integrations** — MES, SCADA, CMMS, QMS, asset history: операційно релевантно, не isolated demo

### Use Case
- ✅ **Strong GMP problem statement** — explicit stakeholder set, regulated industry context
- ✅ **KPI business-facing** — decision latency, manual QA effort, inspection preparation: зрозуміло бізнесу
- ✅ **Innovation** — multi-agent design tied to real regulated workflow (не просто chatbot)
- ✅ **AI Fit для задачі** — contextual retrieval, historical pattern interpretation, recommendation drafting

---

## 5. Топ-6 Gaps для виправлення

### Gap #1: Track не задекларований

| Параметр | Значення |
|---|---|
| **Severity** | 🔴 CRITICAL — це compliance failure |
| **Evaluation check** | Environment Track declared → FAIL |
| **Affects** | Platform Fit (−2), провалив cross-cutting check |

**Проблема:** Track A (GitHub + Azure + Foundry) явно не вказаний. Submission не show-ує де GitHub, CI/CD, deployment workflows входять у lifecycle.

**Що потрібно:**
- Явно вказати "Track A — GitHub + Azure + Azure AI Foundry"
- Додати GitHub repo до архітектурної схеми
- Показати CI/CD pipeline (GitHub Actions)
- Показати deployment workflow: dev → staging → prod
- Evaluation pipeline через AI Foundry

**Де виправити:** → [02 · Архітектура — GitHub + CI/CD section](./02-architecture.md#github--cicd-gap-1)  
**Задача:** → [04 · План дій](./04-action-plan.md)

---

### Gap #2: Security

| Параметр | Значення |
|---|---|
| **Severity** | 🔴 HIGH |
| **Evaluation check** | Data/Governance/Security → 6/10, Microsoft Security & Monitoring → WARN |
| **Affects** | Architecture score −4, WAF Security pillar |

**Проблема:** Audit logging є, але весь security шар відсутній:
- Немає identity architecture
- Немає RBAC (хто може що робити)
- Немає secrets handling
- Немає network isolation
- Немає encryption specification
- Немає SIEM/monitoring

**Що потрібно:**
```
Identity:
  - Azure Entra ID (Managed Identities для Azure Functions, Foundry, AI Search)
  - No hardcoded credentials — all via Managed Identity або Key Vault references

Secrets:
  - Azure Key Vault для всіх API keys, connection strings, certificates

Network:
  - Private Endpoints для AI Search, Foundry, Storage
  - VNet Integration для Azure Functions
  - NSG rules

RBAC (мінімальний набір ролей):
  - Operator: може переглядати alerts, approving/declining recommendations
  - QA Engineer: може переглядати + редагувати CAPA, escalate
  - Compliance Officer: read-only audit trail, reporting
  - Admin/IT: full access, deployment
  - Agent Service Principal: read-only SOP/CAPA (least privilege)

Data:
  - Encryption at rest: Azure Storage, AI Search (default AES-256)
  - Encryption in transit: TLS 1.2+ (default Azure)
  - Data classification: SOP (Confidential), CAPA (Restricted), audit logs (Restricted)

Monitoring:
  - Azure Monitor + Log Analytics workspace
  - Alerts на failed events, security incidents
  - (Опц.) Microsoft Sentinel SIEM
```

**Де виправити:** → [02 · Архітектура — Security section](./02-architecture.md#шар-security-gap-2)  
**Вимоги:** → [01 · Вимоги — Security](./01-requirements.md#8-security--monitoring-вимоги)

---

### Gap #3: Reliability

| Параметр | Значення |
|---|---|
| **Severity** | 🔴 HIGH |
| **Evaluation check** | Reliability/Performance/Cost → 5/10 (найнижча оцінка), Azure WAF Reliability → WARN |
| **Affects** | Architecture score −5 |

**Проблема:** GMP-critical workflow без visibility:
- Немає event queuing (якщо Functions впав — подія втрачена)
- Немає retry strategy
- Немає dead-letter handling
- Немає fallback mode
- Немає model timeout handling
- Немає cost controls

**Що потрібно:**
```
Event Queuing:
  - Azure Service Bus (preferred для reliable messaging) або Event Hubs (streaming)
  - SCADA/MES → Service Bus Topic → Azure Functions
  - Dead Letter Queue для failed/unprocessable events

Retry:
  - Azure Functions: retry policy (exponential backoff, max 3 attempts)
  - Agent calls: retry на transient failures (timeouts, throttling)
  - Per-service retry budgets

Circuit Breaker:
  - При > N failures за window → circuit open → manual fallback mode

Fallback Mode:
  - Якщо AI недоступний → alert operator без AI recommendation
  - Manual-only operating mode для GMP continuity

Latency Budgets:
  - Context enrichment: < 30 сек
  - Compliance Agent: < 90 сек
  - CAPA Agent: < 90 сек
  - Total to decision package: < 5 хв (наш KPI)
  - Human approval: async (no timeout)

Cost Controls:
  - Token budgets per agent call
  - Caching для frequently retrieved SOPs
  - Model routing: cheapest model для simple classification, GPT-4 для complex reasoning
```

**Де виправити:** → [02 · Архітектура — Reliability section](./02-architecture.md#шар-reliability-gap-3)  
**Вимоги:** → [01 · Вимоги — WAF](./01-requirements.md#6-azure-waf-вимоги)

---

### Gap #4: Responsible AI (RAI)

| Параметр | Значення |
|---|---|
| **Severity** | 🟠 HIGH |
| **Evaluation check** | AI Fit → 8/10 із застереженням, Azure WAF AI Pillar → WARN |
| **Affects** | Use Case score −2, AI Pillar compliance |

**Проблема:** Partial RAI coverage:
- Немає confidence thresholds
- Немає evidence gating (рекомендація без джерела → не допускається)
- Немає hallucination controls
- Немає prompt-injection defenses
- Немає agent observability
- Немає model versioning/rollback

**Що потрібно:**
```
Confidence & Evidence:
  - Кожна рекомендація Compliance Agent ПОВИННА мати: SOP reference + page + GMP clause
  - Кожна CAPA рекомендація ПОВИННА мати: CAPA history case reference + similarity score
  - Confidence threshold: < 0.7 → escalate to human (не показувати як рекомендацію)
  - Evidence mandatory gate: без evidence → рекомендація заблокована

Hallucination Controls:
  - Grounded generation тільки (RAG, не free generation)
  - Source verification: agent повинен підтвердити що джерело існує в Azure AI Search
  - Structured output schema (JSON з обов'язковими полями evidence)

Prompt Injection:
  - Input validation на SCADA/MES даних (sanitize перед передачею агенту)
  - System prompt hardening (boundaries між data і instructions)
  - Azure AI Content Safety перед виходом

Observability:
  - Azure Monitor + Application Insights трасування кожного agent call
  - Log: prompt → retrieved docs → output → confidence score → human decision
  - Alerting на аномальну поведінку агентів

Model Lifecycle:
  - Версіонування deployed моделей (model name + version explicit)
  - Rollback plan при regression
  - Evaluation runs перед deployments (AI Foundry evaluation)
```

**Де виправити:** → [02 · Архітектура — RAI section](./02-architecture.md#шар-responsible-ai-gap-4)  
**Вимоги:** → [01 · Вимоги — AI Pillar](./01-requirements.md#7-azure-ai-pillar-вимоги)

---

### Gap #5: UX

| Параметр | Значення |
|---|---|
| **Severity** | 🟠 MEDIUM |
| **Evaluation check** | UX Simplicity → 6/10 |
| **Affects** | Use Case score −4 |

**Проблема:** Process-level description без interface:
- Не показано, де оператор бачить decision package
- Не показано, як він approves/denies
- Explainability та trustworthiness cannot be assessed

**Що потрібно:**
```
Operator interface (вибрати один варіант):
  Варіант A: Microsoft Teams Adaptive Card
    - Alert card у Teams channel
    - Показує: summary + risk level + CAPA recommendation + evidence source
    - Вбудовані кнопки: [Approve] [Deny] [Ask Question]
    - Teams bot для Q&A з агентом
    ✅ Pros: no new app, familiar UX, integrates з Teams
    ⚠️ Cons: обмежений layout

  Варіант B: Power Apps portal (low-code)
    - Dedicated operator dashboard
    - Queue of pending approvals
    - Detail view з full evidence
    ✅ Pros: rich UX, можна брендувати
    ⚠️ Cons: потребує Power Apps license

  Варіант C: Custom Web App (Azure Static Web Apps)
    - React/minimal web app
    - Hosted на Azure Static Web Apps
    ✅ Pros: повний контроль, Track A aligned
    ⚠️ Cons: більше роботи

Sample Decision Package (must-have):
  ┌─────────────────────────────────────────────────────────┐
  │ DEVIATION ALERT — HIGH RISK                              │
  │ Asset: Granulator GR-204 | Line 2                       │
  │ Signal: Vibration spike 2.8g → threshold 1.5g (MES)    │
  │ Batch: BPR-2024-1153 · Stage: Wet granulation           │
  ├─────────────────────────────────────────────────────────┤
  │ COMPLIANCE ASSESSMENT                                    │
  │ Classification: Equipment Deviation — Type II           │
  │ GMP Risk: HIGH (potential bearing failure)              │
  │ Reference: SOP-MAINT-044 §3.2 (Vibration thresholds)   │
  │ Confidence: 0.92                                        │
  ├─────────────────────────────────────────────────────────┤
  │ CAPA RECOMMENDATION                                     │
  │ 1. Stop granulator, inspect bearing                     │
  │ 2. Replace bearing per PM-PROC-019                      │
  │ 3. Run validation batch before restart                  │
  │ Based on: CAPA-2023-0847 (similar case, same asset type)│
  ├─────────────────────────────────────────────────────────┤
  │ [✅ Approve & Create Work Order]  [❌ Deny]  [💬 Q&A]   │
  └─────────────────────────────────────────────────────────┘
```

**Де виправити:** → [02 · Архітектура — UX section](./02-architecture.md#operator-ux-gap-5)

---

### Gap #6: IaC / Provisioning

| Параметр | Значення |
|---|---|
| **Severity** | 🟡 MEDIUM |
| **Evaluation check** | Scalability/Integration/Provisioning → 7/10 |
| **Affects** | Architecture score −3 |

**Проблема:** Architecture lists services but not deployment mechanisms.

**Що потрібно:**
```
IaC:
  - Bicep або Terraform templates для всіх Azure ресурсів
  - Resource groups: rg-sentinel-dev / rg-sentinel-staging / rg-sentinel-prod
  - Parameters для environment-specific values

Environments:
  - dev: для розробки та тестування
  - staging: для validation перед production
  - prod: для demo/finals

GitHub Actions:
  - CI: lint + unit tests на PR
  - CD: deploy до staging на merge до main
  - Manual gate: promote staging → prod

Monitoring setup:
  - Log Analytics Workspace provisioned via IaC
  - Application Insights для кожного Azure Function
  - Dashboards в Azure Monitor
```

**Де виправити:** → [02 · Архітектура — IaC section](./02-architecture.md#github--cicd-gap-1)

---

## 6. Azure WAF Gaps

| WAF Pillar | Статус | Що відсутнє | Пріоритет |
|---|---|---|---|
| **Reliability** | ❌ WARN | Queuing, retry, DLQ, fallback, degraded mode | 🔴 HIGH |
| **Security** | ❌ WARN | Identity, RBAC, Key Vault, network isolation, SIEM | 🔴 HIGH |
| **Cost Optimisation** | ❌ WARN | Token controls, caching, model routing, per-event cost | 🟠 MEDIUM |
| **Operational Excellence** | ❌ WARN | Monitoring, alerting, CI/CD, observability | 🟠 MEDIUM |
| **Performance Efficiency** | ⚠️ PARTIAL | KPI < 5 хв є, latency SLOs не деталізовані | 🟡 LOW |

---

## 7. Azure AI Pillar Gaps

| AI Pillar Requirement | Статус | Деталі |
|---|---|---|
| Agent Design | ✅ GOOD | Multi-agent orchestration, clear roles |
| Grounding / RAG | ✅ GOOD | Validated SOP/BPR, CAPA history retrieval |
| Model Lifecycle | ⚠️ PARTIAL | Evaluation та governed deployment згадано але не деталізовано |
| Responsible AI | ❌ MISSING | Confidence thresholds, evidence gating, hallucination controls |
| AI Observability | ⚠️ PARTIAL | Incident-scoped App Insights traces now cover the backend-visible Foundry path; Cosmos `incident_events` covers business audit / transcript only; dashboards, alerts, and admin retrieval UX are still pending |
| Prompt Injection Defense | ❌ MISSING | Content safety, input validation |

---

## 8. Cross-cutting перевірки

Офіційні checks з тріаж-репорту:

| Check | Статус (v1.0) | Статус (поточний) | Action |
|---|---|---|---|
| Environment Track declared | ❌ FAIL | ❌ Не виправлений | → [Gap #1](#gap-1-track-не-задекларований) |
| Industry Use Case aligned | ✅ PASS | ✅ | Зберегти |
| Azure WAF aligned | ⚠️ WARN | ⚠️ | → [Gap #2](#gap-2-security), [#3](#gap-3-reliability) |
| Azure WAF AI Pillar aligned | ⚠️ WARN | ⚠️ | → [Gap #4](#gap-4-responsible-ai-rai) |
| Microsoft Security & Monitoring | ⚠️ WARN | ⚠️ | → [Gap #2](#gap-2-security) |

---

## 9. Прогрес виправлення gaps

> Останнє оновлення: 17 квітня 2026 — Architecture v2.0 DESIGNED

| Gap | Пріоритет | Статус | Рішення в v2.0 | Задача |
|---|---|---|---|---|
| #1 Track + GitHub/CI/CD | 🔴 CRITICAL | 🎨 DESIGNED | GitHub Actions CI/CD (T-042) + Bicep IaC (T-041) + Track A явно в архітектурі | [T-041](./tasks/T-041-bicep-iac.md), [T-042](./tasks/T-042-cicd.md) |
| #2 Security | 🔴 HIGH | 🎨 DESIGNED | Entra ID + Key Vault + Managed Identities + VNet + 5 RBAC roles | [T-035](./tasks/T-035-rbac.md), [T-038](./tasks/T-038-security.md) |
| #3 Reliability | 🔴 HIGH | 🎨 DESIGNED | Azure Service Bus DLQ + Durable Functions retry + fallback mode + timeout escalation | [T-022](./tasks/T-022-service-bus.md), [T-039](./tasks/T-039-reliability.md) |
| #4 RAI | 🟠 HIGH | 🔧 IN PROGRESS | Confidence gate path already exists; App Insights prompt and response traces are now implemented for the backend-visible Foundry flow, while Cosmos `incident_events` still only carries business audit / transcript events; Content Safety, prompt-injection guard, admin retrieval UX, and dashboards remain pending | [T-040](./tasks/T-040-rai.md), [T-043](./tasks/T-043-agent-telemetry-admin-view.md) |
| #5 UX | 🟠 MEDIUM | 🎨 DESIGNED | React + Vite operator dashboard + approval UX + SignalR real-time + 5 role views | [T-032](./tasks/T-032-frontend-core.md), [T-033](./tasks/T-033-frontend-approval.md) |
| #6 IaC | 🟡 MEDIUM | 🎨 DESIGNED | Bicep `infra/main.bicep` + modules для всіх 12 ресурсів | [T-041](./tasks/T-041-bicep-iac.md) |

**Легенда статусів:**  
🔜 TODO — не розпочато  
🎨 DESIGNED — архітектура v2.0 описана, задачі створені, реалізація починається  
🔧 IN PROGRESS — implentation розпочато  
✅ DONE — реалізовано і перевірено

---

← [02 Архітектура](./02-architecture.md) · [04 План дій →](./04-action-plan.md)
