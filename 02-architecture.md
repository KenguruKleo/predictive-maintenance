# 02 · Архітектура

← [README](./README.md) · [01 Вимоги](./01-requirements.md) · [03 Аналіз](./03-analysis.md) · [04 План дій](./04-action-plan.md)

> **Призначення:** Живий документ архітектури. Містить те, що ми **подали** (AS-SUBMITTED), і буде оновлюватись у міру implementation. Кожна зміна повинна бути перевірена через [чеклист вимог](./01-requirements.md#10-чеклист-відповідності-живий).

---

## Зміст
1. [Версія подана (AS-SUBMITTED)](#1-версія-подана-as-submitted)
2. [Компонентна схема](#2-компонентна-схема)
3. [Потік даних](#3-потік-даних)
4. [Компоненти — деталі](#4-компоненти--деталі)
5. [Джерела даних](#5-джерела-даних)
6. [Ролі та стейкхолдери](#6-ролі-та-стейкхолдери)
7. [AS-IS vs TO-BE процес](#7-as-is-vs-to-be-процес)
8. [Поточна версія (IN-PROGRESS)](#8-поточна-версія-in-progress)
9. [Changelog архітектури](#9-changelog-архітектури)

---

## 1. Версія подана (AS-SUBMITTED)

> Дата подачі: 26 березня 2026  
> Автор: Kostiantyn Yemelianov  
> Оцінка: 71/100 → [Детальний аналіз](./03-analysis.md)

### Назва рішення
**Deviation Management & CAPA in GMP Manufacturing**  
Predictive maintenance Approach — Operations Assistant

### Загальний опис
AI-powered multi-agent Operations Assistant на **Azure AI Foundry**, який:
- Детектує anomaly/deviation events із SCADA/MES/IoT сигналів
- Збагачує їх batch/equipment контекстом
- Знаходить рішення через RAG на SOP/BPR/CAPA history
- Генерує CAPA рекомендації та audit-ready звіти
- **Обов'язкова** human approval перед виконанням work order

---

## 2. Компонентна схема

```
╔══════════════════════════════════════════════════════════════╗
║          COMPANY DATA LAYER (Azure AI Search / RAG)         ║
║  ┌─────────────┐ ┌──────────────┐ ┌──────────────────────┐  ║
║  │ SOP          │ │ GMP Rules /  │ │ Deviation & CAPA     │  ║
║  │ Repository   │ │ Policies     │ │ History              │  ║
║  └─────────────┘ └──────────────┘ └──────────────────────┘  ║
╚══════════════════════════════════════════════════════════════╝
           ↑ RAG Search          ↑ Azure MCP           ↑ Azure MCP

╔══════════════════════════════════════════════════════════════╗
║         FOUNDRY AGENT SERVICE (Agent Orchestrator)          ║
║   Multi-agent workflow · State management · Routing         ║
║                                                             ║
║  ┌────────────────────┐      ┌───────────────────────────┐  ║
║  │  Compliance Agent  │      │  CAPA / Audit Agent       │  ║
║  │                    │      │                           │  ║
║  │ • Deviation        │      │ • CAPA recommendations    │  ║
║  │   classification   │      │   (history-grounded)      │  ║
║  │ • Risk scoring     │      │ • Report draft generation │  ║
║  │ • GMP compliance   │      │ • Audit trail generation  │  ║
║  │   validation       │      │   (traceable)             │  ║
║  │ • Explainable      │      │                           │  ║
║  │   reasoning        │      └───────────────────────────┘  ║
║  └────────────────────┘                                     ║
╚══════════════════════════════════════════════════════════════╝
                    ↑                    ↑
            Context/Alert         Decision Package
                    │                    │
╔═══════════════════╧════════════════════╧══════════════════╗
║              CONTEXT ENRICHMENT SERVICE                   ║
║  • Retrieve batch & product context (MES)                 ║
║  • Retrieve equipment metadata (CMMS)                     ║
║  • Prefilter historical references                        ║
╚═══════════════════════════════════════════════════════════╝
                         ↑
                  Anomaly detect event
                         │
╔════════════════════════╧══════════════════════════════════╗
║          AZURE FUNCTIONS (Event Ingestion)                ║
╚═══════════════╤══════════════╤═══════════════╤═══════════╝
                │              │               │
        ┌───────┴──┐    ┌──────┴────┐    ┌─────┴──────┐
        │  SCADA   │    │    MES    │    │  IoT/CMMS  │
        │ (signals)│    │ (batch)   │    │ (equipment)│
        └──────────┘    └───────────┘    └────────────┘

                    ↓ (Decision Package)
╔═══════════════════════════════════════════════════════════╗
║              HUMAN APPROVAL (GxP Requirement)             ║
║           [Approved] · [Denied] · [Question]              ║
╚══════════╤══════════════════════════════════════╤═════════╝
           │                                      │
    ┌──────┴──────┐                      ┌────────┴────────┐
    │ Work Order  │                      │  Audit Logging  │
    │ Service     │                      │  Service        │
    │ (QMS/CMMS)  │                      │  (full trace)   │
    └─────────────┘                      └─────────────────┘
```

---

## 3. Потік даних

### AS-SUBMITTED — step by step

```
Step 1: DETECT
  SCADA → anomaly signal → Azure Functions trigger

Step 2: BUILD CONTEXT
  Azure Functions →  Context Enrichment Service
    ├── MES query   → batch context, stage, product
    ├── CMMS query  → equipment metadata, maintenance history
    └── BPR lookup  → historical reference data (pre-filter)

Step 3: AGENT ORCHESTRATION
  Context Enrichment → Foundry Agent Service (Orchestrator)
    │
    ├── Compliance Agent
    │     ├── RAG Call → Azure AI Search (SOP Repository)
    │     ├── RAG Call → Azure AI Search (GMP Rules / Policies)
    │     └── Output: deviation classification + risk score + GMP validation
    │
    └── CAPA/Audit Agent
          ├── RAG Call → Azure AI Search (Deviation & CAPA History)
          ├── RAG Call → Azure AI Search (Equipment manuals/specs)
          └── Output: CAPA recommendations + report draft + audit trail draft

Step 4: DECISION PACKAGE
  Orchestrator → Human Approval Interface
    Decision package = recommendation + rationale + evidence

Step 5: HUMAN DECISION
  Operator/QA → [Approve] / [Deny] / [Ask Question]

Step 6: EXECUTION
  Approved →
    ├── Work Order Service → QMS/CMMS (create & pre-fill work order)
    └── Audit Logging Service → full traceability record
```

---

## 4. Компоненти — деталі

### Azure Functions (Event Ingestion)
- **Роль:** Тригер при аномальному сигналі з SCADA/MES/IoT
- **Вхід:** Raw sensor signals, MES alerts, monitoring system events
- **Вихід:** Structured anomaly event → Context Enrichment Service
- **Gaps:** → [Немає queuing, retry, DLQ](./03-analysis.md#gap-3-reliability)

### Context Enrichment Service
- **Роль:** Збагачення аномалії контекстом перед відправкою агентам
- **Джерела:** MES (batch/product), CMMS (equipment metadata), BPR (historical)
- **Вихід:** Structured incident context

### Agent Orchestrator (Foundry Agent Service)
- **Роль:** Multi-agent workflow, state management, routing між агентами
- **Платформа:** Azure AI Foundry Agent Service
- **Gaps:** → [Немає exception paths, model timeout handling](./03-analysis.md#gap-3-reliability)

### Compliance Agent
- **Роль:** Deviation classification, GMP compliance validation, risk scoring
- **RAG джерела:** SOP Repository, GMP Rules/Policies
- **Вихід:** Classification + risk score + explainable reasoning
- **Gaps:** → [Немає confidence thresholds, prompt injection defense](./03-analysis.md#gap-4-rai)

### CAPA / Audit Agent
- **Роль:** CAPA recommendations, report draft, audit trail generation
- **RAG джерела:** Deviation & CAPA History, Equipment manuals/specs
- **Вихід:** CAPA recommendations (history-grounded) + traceable audit trail
- **Gaps:** → [Немає evidence thresholds, hallucination controls](./03-analysis.md#gap-4-rai)

### Human Approval
- **Роль:** GxP-обов'язкова зупинка перед виконанням
- **Actions:** Approved / Denied / Question
- **Gaps:** → [Немає конкретного UI/interface description](./03-analysis.md#gap-5-ux)

### Work Order Service
- **Роль:** Create & pre-fill work order у QMS/CMMS
- **Інтеграція:** QMS (Quality Management System), CMMS (Computerized Maintenance Management System)

### Audit Logging Service
- **Роль:** Full traceability record для compliance
- **Статус:** ✅ присутній (одна з сильних сторін)

---

## 5. Джерела даних

| Джерело | Тип | Використовується як | Компонент |
|---|---|---|---|
| SCADA | Real-time signals | Anomaly trigger | Azure Functions |
| MES | Batch & stage data | Context enrichment | Context Enrichment Service |
| BPR (Batch Production Record) | Historical | Context enrichment + RAG | Context Enrichment + AI Search |
| SOP Repository | Procedures | RAG retrieval | Azure AI Search |
| GMP Rules / Policies | Regulations | RAG retrieval | Azure AI Search |
| Deviation & CAPA History | Case history | RAG retrieval | Azure AI Search |
| CMMS / Asset Management | Equipment metadata | Context enrichment + RAG | Context Enrichment + AI Search |
| Equipment manuals / specs | Technical docs | RAG retrieval | Azure AI Search |

---

## 6. Ролі та стейкхолдери

| Роль | Участь у системі |
|---|---|
| Production Operator | Отримує alert, переглядає decision package, approves/denies |
| QA / Quality Engineer | Валідує CAPA рекомендації, затверджує відхилення |
| Compliance & Audit Team | Переглядає audit trail, inspection readiness |
| QA Manager | Manages CAPA process, final approvals |
| IT / Digital Transformation | Deploying та managing the system |

> ⚠️ RBAC модель для цих ролей **не описана** → [Gap #2](./03-analysis.md#gap-2-security)

---

## 7. AS-IS vs TO-BE процес

### AS-IS (поточний, manual)
```
Sensor Signal → Alert
  → Operator RECEIVES (manual, interprets context manually)
  → CHECK SOP/BPR (manual search)
  → MAKES DECISION (based on experience, incomplete info)
  → REGISTER CAPA (manual work order creation in QMS/CMMS)
  → CREATE REPORT (manual documentation for audit trail)
```
**Час:** 30–60 хвилин, оператор-залежний результат

### TO-BE (AI-assisted)
```
Sensor Signal → Alert (already automated anomaly detection)
  → Context built AUTO (derived data + incident context)
  → SOP & data retrieval AUTO (relevant SOPs, BPRs, historical cases)
  → AI decision support AUTO (deviation classification + recommendations)
  → CAPA / Work Order prepared AUTO (pre-filled for review)
  → Human review & approval MANUAL (GxP requirement ✅)
  → Report generated AUTO (structured, inspection-ready)
  → CAPA recorded in QMS/CMMS AUTO
```
**Час:** < 5 хвилин для decision, стандартизований результат

---

## 8. Поточна версія (IN-PROGRESS)

> Ця секція оновлюється під час implementation phase (квітень 2026).  
> Зміни базуються на gaps з → [03 · Аналіз](./03-analysis.md#топ-6-gaps-для-виправлення)

### Що потрібно додати до архітектури

#### Шар Security (Gap #2)
```
TODO: Додати до схеми:
- Azure Entra ID (Managed Identities для всіх сервісів)
- Azure Key Vault (secrets, API keys, connection strings)
- Private Endpoints / VNet Integration
- RBAC roles: Operator / QA Engineer / Compliance / Admin
- Encryption at rest (storage) + in transit (TLS)
- Data classification tags на SOP/BPR/CAPA content
```

#### Шар Reliability (Gap #3)
```
TODO: Додати до схеми:
- Azure Service Bus / Event Hubs (event queue між SCADA та Functions)
- Dead Letter Queue (DLQ) для failed events
- Retry policy на Azure Functions
- Circuit breaker для agent calls
- Fallback mode (manual-only при деградації AI)
- Latency budgets: < 30 сек context enrichment, < 3 хв agents, < 5 хв total
```

#### Шар Responsible AI (Gap #4)
```
TODO: Додати до схеми:
- Content Safety перед/після agent calls
- Confidence threshold gate (low confidence → escalate to human)
- Evidence mandatory (кожна рекомендація = recommendation + source SOP + evidence)
- Prompt injection validation на вхідних даних
- Agent output observability (Azure Monitor + traces)
- Model versioning + rollback strategy
```

#### GitHub + CI/CD (Gap #1)
```
TODO: Додати до схеми:
- GitHub repository (code, IaC, configs)
- GitHub Actions (CI/CD pipeline)
- IaC (Bicep або Terraform) для Azure resources
- Deployment environments: dev / staging / prod
- Evaluation pipeline (Azure AI Foundry evaluation runs)
```

#### Operator UX (Gap #5)
```
TODO: Визначити конкретний channel для Human Approval:
- Варіант A: Microsoft Teams adaptive card
- Варіант B: Power Apps portal
- Варіант C: Web application

Decision package має включати:
- Summary відхилення
- Compliance Agent висновок з rationale
- CAPA рекомендація з посиланням на SOP + CAPA history case
- Evidence (трасабельна до джерел)
- [Approve] / [Deny] / [Ask Question] кнопки
```

---

## 9. Changelog архітектури

| Дата | Версія | Зміна | Пов'язаний Gap |
|---|---|---|---|
| 2026-03-26 | v1.0 | Initial submission | — |
| _TBD_ | v1.1 | Security layer (Entra ID, Key Vault, VNet) | [Gap #2](./03-analysis.md#gap-2-security) |
| _TBD_ | v1.2 | Reliability layer (queuing, retry, DLQ) | [Gap #3](./03-analysis.md#gap-3-reliability) |
| _TBD_ | v1.3 | RAI layer (confidence, content safety, observability) | [Gap #4](./03-analysis.md#gap-4-rai) |
| _TBD_ | v1.4 | GitHub + CI/CD + IaC | [Gap #1](./03-analysis.md#gap-1-track-не-задекларований) |
| _TBD_ | v1.5 | Operator UX (Teams card / portal) | [Gap #5](./03-analysis.md#gap-5-ux) |

---

← [01 Вимоги](./01-requirements.md) · [03 Аналіз →](./03-analysis.md)
