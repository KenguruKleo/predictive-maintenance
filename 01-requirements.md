# 01 · Вимоги хакатону

← [README](./README.md) · [02 Архітектура](./02-architecture.md) · [03 Аналіз](./03-analysis.md) · [04 План дій](./04-action-plan.md)

> **Призначення:** Єдине джерело правди про всі вимоги. Перевіряємо перед кожним ітерацією архітектури та кожним deliverable.

---

## Зміст
1. [Хакатон — загальні вимоги](#1-хакатон--загальні-вимоги)
2. [Use Case — LS / Supply Chain (наш трек)](#2-use-case--ls--supply-chain-наш-трек)
3. [Середовища (Tracks)](#3-середовища-tracks)
4. [Критерії оцінки — Architecture (50 балів)](#4-критерії-оцінки-architecture-50-балів)
5. [Критерії оцінки — Use Case (50 балів)](#5-критерії-оцінки-use-case-50-балів)
6. [Azure WAF вимоги](#6-azure-waf-вимоги)
7. [Azure AI Pillar вимоги](#7-azure-ai-pillar-вимоги)
8. [Security & Monitoring вимоги](#8-security--monitoring-вимоги)
9. [Deliverables по фазах](#9-deliverables-по-фазах)
10. [Чеклист відповідності (живий)](#10-чеклист-відповідності-живий)

---

## 1. Хакатон — загальні вимоги

| Параметр | Значення |
|---|---|
| Назва | Microsoft Agentic Industry Hackathon 2026 |
| Організатори | Capgemini (Clemens Reijnen) + Microsoft |
| Мета | Побудова working agentic solutions на Microsoft AI Platforms |
| Команда | 2–7 осіб |
| Оцінка | Architecture (50 балів) + Use Case (50 балів) = 100 |

**Загальні вимоги до рішення:**
- Рішення повинно використовувати **Microsoft AI Platforms** повноцінно
- Повинен бути продемонстрований **industry impact** та **quality**
- Командою обирається один **Track (A/B/C/D)** — і архітектура будується під нього
- Human-in-the-loop **обов'язковий** для GxP/regulated процесів
- Рішення оцінюється як **MVP** — фокус на конкретному сценарії

---

## 2. Use Case — LS / Supply Chain (наш трек)

### Problem Statement (офіційний з хакатону)
> In life sciences (pharma/biotech/medical devices), GMP is the set of regulated quality standards that ensure products are consistently made and controlled so they are safe, effective, and meet specifications. Operations teams must keep assets and batches within validated limits while juggling equipment health, preventive maintenance, and strict SOP/BPR compliance, so monitoring assets in real time, detecting early failure signals, optimizing "golden batch" parameters, and identifying potential deviations fast without disrupting production.

### 4 підходи для цього use case

| Підхід (Track) | Назва | Опис |
|---|---|---|
| **A — Pro-code ✅ (наш)** | Predictive maintenance / Operations Assistant | Azure AI Foundry multi-agent, streaming SCADA/MES, RAG на SOP/BPR |
| B — Low-code | Maintenance Coach (Copilot Studio) | Teams-based NL-query над SOP, guided checklists, Power Automate |
| C — SaaS | Operations Copilot (Dynamics 365) | Closed-loop work orders, asset/field service, auditable workflows |
| D — Fine-tune | Manufacturing Support (Mistral) | Fine-tune на site alarms, batch deviations, maintenance notes |

### Наш підхід (Track A) — офіційний опис
> Using Microsoft AI Foundry, an Operations Agent orchestrates agents that stream real-time sensor/SCADA data to detect early wear patterns and cross-check them against SOP/BPR "golden batch" limits. Example: a vibration spike on a granulator triggers a predicted bearing failure alert plus a recommended PM plan and deviation-resolution playbook retrieved from validated SOPs. AI Foundry supports it with agent orchestration, RAG over controlled documents, evaluation, and governed deployment.

---

## 3. Середовища (Tracks)

### Track A — наш вибір ✅
**Склад:**
- GitHub (repo, CI/CD, GitHub Actions)
- Azure (повний стек)
- Azure AI Foundry (агенти, оркестрація, RAG, evaluation, governed deployment)
- Microsoft Fabric — **опціонально** (якщо потрібно для data pipeline)

**Що Microsoft надає командам Track A:**
- GitHub Copilot
- Azure (Cognitive Services + OpenAI enabled)
- Foundry IQ (preview)
- Fabric IQ (preview, опціонально)

> ⚠️ **Критична вимога:** Track **повинен бути явно задекларований** у submission. У першому поданні цього не було — це Gap #1. Дивись → [03 · Аналіз Gap #1](./03-analysis.md#gap-1-track-не-задекларований)

---

## 4. Критерії оцінки — Architecture (50 балів)

| Dimension | Макс. | Опис критерію |
|---|---|---|
| **Clarity & Flow** | 10 | Чіткість потоку: detect → context → agents → approval → action. Agent roles та data sources видимі. Exception paths та runtime logic визначені. |
| **Platform Fit** | 10 | Правильний вибір Azure сервісів для задачі. Track задекларований. Developer/platform setup показано. GitHub + CI/CD інтегровані. |
| **Data / Governance / Security** | 10 | Identity (Entra ID), RBAC для всіх ролей, Key Vault, private endpoints, encryption, data classification, retention policy, controlled access до SOP/BPR/CAPA. |
| **Reliability / Performance / Cost** | 10 | Event queuing, retries, dead-letter handling, fallback, latency SLOs (< 5 хв), caching, token budgets, cost controls, model timeout handling. |
| **Scalability / Integration / Provisioning** | 10 | IaC/deployment approach, API contracts, environment topology, repeatable provisioning. Enterprise integrations MES/SCADA/CMMS/QMS деталізовані. |

> Поточний стан: **33/50** → [Деталі в аналізі](./03-analysis.md#architecture-dimensions)

---

## 5. Критерії оцінки — Use Case (50 балів)

| Dimension | Макс. | Опис критерію |
|---|---|---|
| **Value & KPI Impact** | 10 | Чіткі business pain points, evidence-based KPI quantification, вимірюваний вплив на regulated process. |
| **Innovation** | 10 | Диференційоване рішення (не basic chatbot/anomaly detector). Thoughtful multi-agent design tied to regulated workflow. |
| **AI Fit** | 10 | AI добре підходить до задачі. Confidence thresholds, evidence gating, hallucination controls, prompt-injection defenses, agent observability. Responsible AI явний. |
| **UX Simplicity** | 10 | Конкретний operator interface показаний. Approval ergonomics та explainability. Sample decision package з rationale/evidence. |
| **Build–Scale–Reuse** | 10 | MVP чітко звужений (один тип активу, один клас відхилення, невеликий SOP/CAPA set). Reusable patterns та MCP assets. Production-scale constraints визначені. |

> Поточний стан: **38/50** → [Деталі в аналізі](./03-analysis.md#use-case-dimensions)

---

## 6. Azure WAF вимоги

Hackathon явно перевіряє **Azure Well-Architected Framework**:

| Pillar | Вимога | Наш стан |
|---|---|---|
| **Reliability** | Retry strategy, queuing, dead-letter, fallback mode, degraded/manual-only mode | ❌ Відсутній |
| **Security** | Entra ID, secrets handling, network isolation, encryption, SIEM | ❌ Відсутній |
| **Cost Optimisation** | Token controls, caching, model routing, cost per event | ❌ Відсутній |
| **Operational Excellence** | Monitoring, alerting, CI/CD, observability | ❌ Відсутній |
| **Performance Efficiency** | Latency budgets, throughput, scaling triggers | ⚠️ Частково (< 5 хв KPI є) |

> Все WAF покриття → [03 · Аналіз](./03-analysis.md#azure-waf-gaps)

---

## 7. Azure AI Pillar вимоги

| Вимога | Опис | Наш стан |
|---|---|---|
| **Agent Design** | Multi-agent orchestration, clear agent roles | ✅ Добре |
| **Grounding / RAG** | Validated SOP/BPR, CAPA history retrieval | ✅ Добре |
| **Model Lifecycle** | Evaluation, governed deployment, versioning/rollback | ⚠️ Частково (згадано, не деталізовано) |
| **Responsible AI** | Confidence thresholds, evidence gating | ❌ Відсутній |
| **AI Observability** | Agent monitoring, output tracing | ❌ Відсутній |
| **Prompt Injection Defense** | Content safety, input validation | ❌ Відсутній |

---

## 8. Security & Monitoring вимоги

Хакатон явно перевіряє **Microsoft Security & Monitoring**:

- [ ] Identity architecture (Entra ID / Managed Identities)
- [ ] RBAC model (operators / QA / compliance / IT ролі)
- [ ] Secrets handling (Azure Key Vault)
- [ ] Network isolation (Private Endpoints, VNet integration)
- [ ] Encryption (at rest + in transit)
- [ ] Data classification та retention
- [ ] SIEM / monitoring (Azure Monitor, Log Analytics)
- [ ] Alerting
- [ ] Audit logging ✅ — вже є, але тільки це

---

## 9. Deliverables по фазах

### Semi-finals (кінець березня) — ✅ ЗРОБЛЕНО
- [x] PowerPoint з описом use case
- [x] Business process AS-IS → TO-BE
- [x] High-level архітектура
- [ ] ⚠️ Track задекларований — **НЕ ЗАФІКСОВАНО** в submission

### Implementation (квітень 2026) — 🔄 ЗАРАЗ
- [ ] Working code у GitHub repo
- [ ] Azure Foundry agents deployed
- [ ] RAG pipeline (Azure AI Search) налаштований
- [ ] Integration з mock data sources
- [ ] Security layer (Entra ID, RBAC, Key Vault)
- [ ] Reliability layer (queuing, retry)
- [ ] Responsible AI controls
- [ ] Demo scenario готовий (один asset, один deviation class)

### Final submission (1-й тиж. травня)
- [ ] **5-хвилинне demo відео** (детальні вимоги нижче ↓)
- [ ] GitHub repo з повним кодом
- [ ] Working implementation

#### 📹 Вимоги до фінального відео (5 хвилин)

> ⚡ **Критично важливо.** Це єдиний touchpoint для Capgemini executives та Microsoft judges на фіналі. 5 хвилин = рішення про переможця.

**Обов'язкові елементи відео:**
- [ ] Hook — проблема + ключова цифра (30–60 хв → < 5 хв)
- [ ] Cartoon/анімація AS-IS процесу (без додатку) — ~60 сек
- [ ] Cartoon/анімація TO-BE процесу (з додатком) — ~60 сек  
- [ ] Live demo робочого додатку (один повний сценарій: SCADA alert → decision package → approval → audit trail)
- [ ] Архітектура — один слайд (Track A + всі компоненти)
- [ ] KPI summary та impact
- [ ] Тривалість: ≤ 5:10 хв
- [ ] Мова: **English**
- [ ] Субтитри (judges можуть дивитись без звуку)

**Детальний план відео:** → [04 · План дій — T-002](./04-action-plan.md#фінальне-відео-t-002)

### Finals (2-й тиж. травня)
- [ ] Presentation топ-10 для Capgemini executives + Microsoft

---

## 10. Чеклист відповідності (живий)

Перевіряємо при кожній ітерації архітектури:

### ✅ Реалізовано (код або інфраструктура існує)
- [x] Strong GMP problem statement
- [x] Multi-agent design на Azure AI Foundry (архітектура)
- [x] Human approval step (GxP) — механізм Durable `waitForExternalEvent` задокументовано (ADR-001)
- [x] Enterprise integrations названі (MES, SCADA, CMMS, QMS)
- [x] Clear KPIs (< 5 хв decision time)
- [x] Stakeholders визначені
- [x] **Track A явно задекларований** — в 02-architecture.md v2.0, GitHub Actions + Bicep
- [x] **GitHub + CI/CD** — `ci.yml` (lint+test+bicep validate) + `deploy.yml` (push main) живі та зелені
- [x] **Event Queue** — Azure Service Bus `alert-queue` + DLQ задеплоєно (Bicep, Sweden Central)
- [x] **Cosmos DB** — 5 containers задеплоєно (incidents, equipment, batches, capa-plans, approval-tasks)
- [x] **IaC** — Bicep `infra/main.bicep` + 5 modules, 7 ресурсів задеплоєно
- [x] **App Insights + Log Analytics** — задеплоєно, traces доступні
- [x] **Mock data** — equipment (3), batches (2), incidents (3), templates (2) у `data/mock/`
- [x] **Конкретний equipment scenario** — GR-204, Granulator, Plant-01, Line-2

### 🎨 Спроектовано (архітектура описана, реалізація не завершена)
- [ ] **Entra ID / Managed Identities** — архітектура в §8.1, реалізація T-035, T-038
- [ ] **RBAC модель** — 5 ролей визначено (§8.1), реалізація T-035
- [ ] **Azure Key Vault** — архітектура в §8.1, не задеплоєно, T-038
- [ ] **Retry / DLQ / Fallback** — Service Bus DLQ задеплоєно, retry logic у Durable orchestrator T-024, T-039
- [ ] **Responsible AI** — confidence gate + evidence schema у §8.3, реалізація T-040
- [ ] **Prompt injection defenses** — описано в §8, реалізація T-040
- [ ] **Content Safety** — архітектура в cross-cutting concerns, реалізація T-040
- [ ] **Agent observability** — App Insights задеплоєно, custom metrics T-040
- [ ] **RAG на SOP/BPR/CAPA** — 4 AI Search indexes описано (§8.5), AI Search не задеплоєно, T-037
- [ ] **Operator UI** — wireframe у T-033, React проект не створено, T-032
- [ ] **Sample decision package** — schema у §8.3, реалізація T-026

### 🔧 В розробці (реалізація — квітень 2026)
- [ ] Private Endpoints / VNet — реалізація T-038
- [ ] Latency SLOs — реалізація під час dev (T-039)
- [ ] Token budgets / caching — T-039 nice-to-have
- [ ] Model versioning / rollback — T-040
- [ ] Усі implementation задачі T-020 → T-042 (див. [04 · План дій](./04-action-plan.md))

---

← [README](./README.md) · [02 Архітектура →](./02-architecture.md)
