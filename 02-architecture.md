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
   - [8.9 Два рівні оркестрації](#89-два-рівні-оркестрації)
   - [8.10 ADR-001: HITL механізм](#810-adr-001-human-in-the-loop--durable-waitforexternalevent-vs-foundry-native)
   - [8.11 Розбивка на Azure Functions](#811-розбивка-на-azure-functions--повна-карта)
   - [8.12 Azure SignalR — контракт](#812-azure-signalr--контракт)
   - [8.13 Шар документів — Ingestion Architecture](#813-шар-документів--ingestion-architecture)
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

> ⚠️ **AS-SUBMITTED v1.0.** Термінологія цього розділу відповідає поданій архітектурі (26 березня 2026). В реалізаційній фазі v2.0 компоненти перейменовані та реструктуровані — дивись [§8.2 таблицю компонентів](#82-компоненти-v20--таблиця) та [таблицю еволюції нижче](#еволюція-компонентів-v10--v20).

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

### Еволюція компонентів: v1.0 → v2.0

| Компонент v1.0 (AS-SUBMITTED) | Компонент v2.0 (реалізація) | Зміна |
|---|---|---|
| Azure Functions (Event Ingestion) | `ingest_alert` HTTP + `alert_processor` Service Bus trigger | Розбито: HTTP endpoint публікує в Service Bus; окремий тригер споживає чергу |
| Context Enrichment Service | `enrich_context` Durable Activity | Вбудовано в Durable orchestrator — не окремий сервіс |
| Agent Orchestrator (Foundry) | **Два рівні**: Durable Functions (workflow) + Foundry Agent Service (AI) | [ADR-001 §8.10](#810-adr-001-human-in-the-loop--durable-waitforexternalevent-vs-foundry-native) |
| Compliance Agent | Research Agent (context) + Document Agent (classification/risk) | Responsibilities розподілено |
| CAPA / Audit Agent | Document Agent (CAPA drafting) + Execution Agent (execution) | Drafting відокремлено від execution після approval |
| Human Approval | `decision_handler` HTTP → `waitForExternalEvent` + SignalR push | Конкретний механізм з resume API |
| Work Order Service | Execution Agent → MCP `create_work_order` (CMMS mock) | MCP tool call — не окремий сервіс |
| Audit Logging Service | `finalize_audit` Durable Activity → Cosmos `incidents` + `approval-tasks` | Вбудовано в Durable orchestrator |

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

## 8. Поточна версія v2.0 (IN-PROGRESS — Implementation Phase)

> Архітектура v2.0 розроблена для Implementation Phase (квітень 2026).  
> Мова: **Python**. Frontend: **React + Vite** (Azure Static Web Apps).  
> MCP servers: **локальний stdio transport**.  
> Усі 6 gaps з тріажу закрито в цьому дизайні.
>
> **Статус деплою (17 квітня 2026):** 7 Azure ресурсів задеплоєно в `ODL-GHAZ-2177134` (Sweden Central).  
> CI/CD: GitHub Actions `deploy.yml` на push у `main`.  
> Bicep: `infra/main.bicep` → 5 модулів у `infra/modules/`.

---

### 8.1 Загальна схема v2.0

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SOURCES (Mock для hackathon)            │
│   SCADA/MES signals    ──►   POST /api/alerts                       │
│   (simulated via seed script)                                        │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│              AZURE SERVICE BUS — alert-queue (Gap #3 ✅)            │
│   Reliability: DLQ, retry, at-least-once delivery                   │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│           AZURE DURABLE FUNCTIONS — Python (Gap #3 ✅)              │
│                                                                     │
│  Orchestrator Function                                              │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ 1. Activity: CreateIncident ──► Cosmos DB                  │    │
│  │ 2. Activity: EnrichContext  ──► Cosmos DB (equipment/batch)│    │
│  │ 3. Activity: RunAgents      ──► Azure AI Foundry           │    │
│  │    └─ Research Agent   (RAG + MCP-cosmos-db)               │    │
│  │    └─ Document Agent   (templates + structured output)     │    │
│  │ 4. Activity: NotifyOperator ──► Azure SignalR              │    │
│  │ 5. waitForExternalEvent("operator_decision")               │    │
│  │    OR Timer: 24h → escalate to QA Manager                  │    │
│  │ 6a. "approved"     → Activity: ExecuteDecision             │    │
│  │     └─ Execution Agent (MCP-qms-mock + MCP-cmms-mock)      │    │
│  │ 6b. "rejected"     → Activity: CloseIncident(rejected)     │    │
│  │ 6c. "more_info"    → loop back to step 2 + extra context   │    │
│  │ 7. Activity: FinalizeAuditRecord ──► Cosmos DB             │    │
│  └────────────────────────────────────────────────────────────┘    │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────────────┐
          ▼               ▼                       ▼
┌──────────────┐  ┌───────────────────┐  ┌──────────────────────────┐
│   AZURE      │  │  AZURE AI FOUNDRY │  │   AZURE COSMOS DB        │
│   SIGNALR    │  │  AGENT SERVICE    │  │   Serverless             │
│              │  │                   │  │   (5 containers)         │
│  Real-time   │  │  Orchestrator     │  │  incidents               │
│  push to     │  │  ├─ Research Agt  │  │  equipment (mock CMMS)   │
│  React UI    │  │  ├─ Document Agt  │  │  batches (mock MES)      │
│  (Gap #5 ✅) │  │  └─ Execution Agt │  │  capa-plans              │
└──────────────┘  │                   │  │  approval-tasks          │
                  │  MCP Servers:     │  └──────────────────────────┘
                  │  ├─ mcp-cosmos-db │
                  │  ├─ mcp-qms-mock  │
                  │  └─ mcp-cmms-mock │
                  └───────────────────┘
                          │
                          ▼
              ┌───────────────────────────┐
              │  AZURE AI SEARCH          │
              │  5 indexes (RAG):         │
              │  ├─ idx-sop-documents     │
              │  ├─ idx-equipment-manuals │
              │  ├─ idx-gmp-policies      │
              │  ├─ idx-bpr-documents ★  │
              │  └─ idx-incident-history  │
              └───────────────────────────┘
                    ★ product-specific CPP ranges
                      (NOR narrower than equip. PAR)

┌─────────────────────────────────────────────────────────────────────┐
│                  BACKEND API — Azure Functions HTTP                 │
│  POST /api/alerts              GET /api/incidents                   │
│  GET  /api/incidents/{id}      GET /api/incidents/{id}/events       │
│  POST /api/incidents/{id}/decision  (resumes Durable orchestrator)  │
│  GET/PUT /api/templates/{id}   GET /api/equipment/{id}              │
│  GET /api/batches/current/{eq_id}                                   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│              REACT + VITE FRONTEND (Azure Static Web Apps)          │
│  (Gap #5 ✅)                                                         │
│                                                                     │
│  Role: operator      → Incident list + decision package + approval  │
│  Role: qa-manager    → All incidents + escalation queue             │
│  Role: maint-tech    → Work orders view (read-only)                 │
│  Role: auditor       → Full audit trail view (read-only)            │
│  Role: it-admin      → Template management + LLM analytics          │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│               CROSS-CUTTING CONCERNS                                │
│  Security (Gap #2 ✅): Azure Entra ID · Key Vault · Managed         │
│    Identities · VNet Private Endpoints · RBAC 5 roles               │
│  Reliability (Gap #3 ✅): Service Bus DLQ · Durable retry ·         │
│    Fallback mode · Circuit breaker · Timeout escalation             │
│  RAI (Gap #4 ✅): Confidence gate 0.7 · Azure Content Safety ·      │
│    Evidence-grounded output · Prompt injection guard                │
│  Observability: Azure Monitor · App Insights · Log Analytics        │
│  Track A (Gap #1 ✅): GitHub repo · GitHub Actions CI/CD ·          │
│    Bicep IaC · Azure Foundry evaluation runs                        │
│  IaC (Gap #6 ✅): Bicep templates · main.bicep + modules/           │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 8.2 Компоненти v2.0 — таблиця

| Компонент | Технологія | Роль | Закриває Gap |
|---|---|---|---|
| **Backend API** | Azure Functions (Python) | HTTP trigger для REST API endpoints | — |
| **Workflow Engine** | Azure Durable Functions (Python) | Stateful orchestration, pause/resume, timeout | Gap #3 |
| **Alert Queue** | Azure Service Bus | Decoupled ingestion, DLQ, at-least-once | Gap #3 |
| **Agent Orchestrator** | Azure AI Foundry Agent Service | Routing між агентами, state, loops | — |
| **Research Agent** | Foundry Agent + MCP + RAG | Збір контексту: equipment history, semantic SOPs | Gap #4 |
| **Document Agent** | Foundry Agent + templates | Draft: work_order, audit_entry, recommendation, risk_level | Gap #5 |
| **Execution Agent** | Foundry Agent + MCP-QMS/CMMS | Виконання після approval: create WO + audit entry | — |
| **MCP: mcp-cosmos-db** | Python (stdio MCP server) | Tools: get_incident, get_equipment, get_batch, search_incidents | — |
| **MCP: mcp-qms-mock** | Python (stdio MCP server) | Tool: create_audit_entry (мок QMS) | — |
| **MCP: mcp-cmms-mock** | Python (stdio MCP server) | Tool: create_work_order (мок CMMS) | — |
| **Incident DB** | Azure Cosmos DB Serverless | 5 containers: incidents, equipment, batches, capa-plans, approval-tasks | — |
| **RAG Storage** | Azure AI Search | **5 indexes**: SOPs, equipment manuals, GMP policies, **BPR product specs**, incident history | Gap #4 |
| **Document Ingestion** | Blob Storage + blob trigger Function | Chunk → embed → AI Search (for SOPs/manuals) | — |
| **Real-time Push** | Azure SignalR Service | Push notifications до React UI (approval pending, status change) | Gap #5 |
| **Frontend** | React + Vite (Static Web Apps) | Operator dashboard, approval UX, manager/auditor views | Gap #5 |
| **Identity & Access** | Azure Entra ID | AuthN/AuthZ, Managed Identities, 5 RBAC roles | Gap #2 |
| **Secrets** | Azure Key Vault | All connection strings, API keys, agent secrets | Gap #2 |
| **Network** | VNet + Private Endpoints | Cosmos DB, AI Search, Service Bus не відкриті в інтернет | Gap #2 |
| **Observability** | App Insights + Log Analytics | Request traces, agent traces, errors, metrics | Gap #4 |
| **IaC** | Bicep (infra/) | Repeatable provisioning для всіх ресурсів | Gap #6 |
| **CI/CD** | GitHub Actions | Build, test, Bicep deploy, Foundry eval | Gap #1 |

---

### 8.3 Агенти — детальний дизайн

#### Research Agent
- **Мета:** зібрати весь релевантний контекст для incident
- **RAG tools:** `search_sop_documents`, `search_equipment_manuals`, `search_gmp_policies`, **`search_bpr_documents`**, `search_incident_history`
- **MCP tools:** `get_equipment(id)`, `get_batch(id)`, `search_incidents(equipment_id, date_range)`
- **Output schema** (`ResearchAgentOutput`):

```json
{
  "equipment_status": {
    "id": "GR-204",
    "validated_params": { "impeller_speed_rpm": [200, 800] },
    "last_maintenance": "2026-03-10",
    "open_deviations": 1
  },
  "batch_context": {
    "batch_id": "BPR-2026-0042",
    "product": "Metformin 500mg",
    "stage": "wet_granulation",
    "current_params": { "impeller_speed_rpm": 580 }
  },
  "bpr_constraints": {
    "document_id": "BPR-MET-500-v3.2",
    "product_nor": { "impeller_speed_rpm": [600, 700], "spray_rate_g_min": [75, 105] },
    "product_par": { "impeller_speed_rpm": [580, 750] },
    "note": "Product NOR/PAR narrower than equipment PAR. Use for deviation assessment."
  },
  "relevant_sops": [
    { "doc_id": "SOP-DEV-001", "title": "Deviation Management", "section": "§4.2", "score": 0.94 }
  ],
  "historical_cases": [
    { "incident_id": "INC-2025-0311", "similarity": 0.88, "resolution": "bearing replacement" }
  ]
}
```

#### Document Agent
- **Мета:** скласти decision package з evidence
- **Input:** `ResearchAgentOutput` + incident details
- **Output schema** (`DocumentAgentOutput`):

```json
{
  "recommendation": "Stop granulator, inspect impeller bearing",
  "risk_level": "HIGH",
  "confidence": 0.84,
  "deviation_classification": "Equipment Deviation – Type II",
  "evidence_citations": [
    { "source": "SOP-DEV-001", "section": "§4.2", "text": "vibration thresholds..." },
    { "source": "INC-2025-0311", "similarity": 0.88 }
  ],
  "work_order_draft": { "type": "corrective_maintenance", "priority": "urgent", "description": "..." },
  "audit_entry_draft": { "deviation_type": "Equipment", "gmp_clause": "21 CFR 211.68" },
  "capa_steps": ["Stop granulator", "Inspect bearing", "Run validation batch before restart"]
}
```

- **RAI gate — confidence < 0.7:**

| `confidence` | `risk_level` | Дія | Audit trail |
|---|---|---|---|
| ≥ 0.7 | `HIGH` / `MEDIUM` / `LOW` | Operator бачить рекомендацію | Confidence score записується |
| < 0.7 | `LOW_CONFIDENCE` | ⚠️ Попередження: «AI впевненість недостатня» — коментар обов'язковий | `human_override = true` записується |
| < 0.7 + no evidence | `BLOCKED` | Рекомендація не показується; авто-ескалація до QA Manager | Escalation event у `incidents` |

#### Execution Agent
- **Мета:** виконати дії після human approval
- **Triggers:** тільки після `operator_decision == "approved"`
- **MCP tools:** `create_work_order(payload)` (CMMS mock), `create_audit_entry(payload)` (QMS mock)
- **Output schema** (`ExecutionAgentOutput`):

```json
{
  "work_order_id": "WO-2026-0847",
  "audit_entry_id": "AE-2026-1103",
  "execution_timestamp": "2026-04-17T14:32:11Z",
  "human_override": false
}
```

---

### 8.4 Cosmos DB — схема контейнерів та доступ

**Database:** `sentinel-intelligence` · Serverless · 5 контейнерів

#### Контейнери

| Контейнер | Partition Key | Призначення |
|---|---|---|
| `incidents` | `/equipmentId` | Основний документ incident + AI analysis + workflow state |
| `equipment` | `/id` | Mock CMMS: master data, validated params, PM history |
| `batches` | `/equipmentId` | Mock MES: поточні та завершені batch records |
| `capa-plans` | `/incidentId` | Згенеровані Document Agent CAPA плани |
| `approval-tasks` | `/incidentId` | Human-in-the-loop approval tasks + execution results |

> ⚠️ **Cross-partition query concern:** `incidents` партиціоновано по `/equipmentId`. Запити `GET /api/incidents` (список усіх) та фільтри по `status`/`date`/`severity` у dashboard — cross-partition (дорого). **Вирішення:** Cosmos DB автоматично підтримує cross-partition запити з `enableCrossPartitionQuery=True`; для hackathon обсягу (~100 incidents) прийнятно. В production — додати materialized view через Change Feed або secondary index по `status` + `createdAt`.

#### Матриця доступу до контейнерів

| Контейнер | Сервіс / Агент | Операція | Інструмент |
|---|---|---|---|
| `incidents` | Azure Functions | Create, Read, Update | `azure-cosmos` SDK |
| `incidents` | Research Agent | Read (semantic search) | MCP: `search_incidents(equipment_id, date_range)` |
| `equipment` | Azure Functions | Read | `azure-cosmos` SDK |
| `equipment` | Research Agent | Read by ID | MCP: `get_equipment(id)` |
| `batches` | Azure Functions | Read | `azure-cosmos` SDK |
| `batches` | Research Agent | Read by ID | MCP: `get_batch(id)` |
| `capa-plans` | Document Agent | **Write** (draft CAPA) | `azure-cosmos` SDK |
| `capa-plans` | Execution Agent | Read (before execution) | MCP: read CAPA plan |
| `approval-tasks` | Azure Functions | Write (create task), Read (poll decision) | `azure-cosmos` SDK |
| `approval-tasks` | Execution Agent | Write (audit entry result) | MCP: `create_audit_entry` |

---

### 8.5 RAG vs Direct — коли що використовується

| Дані | Спосіб | Чому |
|---|---|---|
| Equipment validated parameters (PAR) | MCP (Cosmos DB) | Структуровані — точне значення важливіше за semantic match; містить equipment-level validated range |
| Current batch context | MCP (Cosmos DB) | Structured, current state |
| **BPR product process specs (NOR)** | **RAG (AI Search `idx-bpr-documents`)** | **Semantic search — product-specific CPP ranges narrower than equipment PAR; відповідь на «яка NOR для Metformin impeller?»** |
| Historical incidents (semantic) | RAG (AI Search `idx-incident-history`) | Semantic similarity — "find similar cases" |
| SOPs/procedures | RAG (AI Search `idx-sop-documents`) | Semantic search по тексту процедур |
| Equipment manuals | RAG (AI Search `idx-equipment-manuals`) | Semantic search по технічній документації |
| GMP policies/regulations | RAG (AI Search `idx-gmp-policies`) | Semantic search по регуляторним вимогам |
| Work order status | MCP (CMMS mock) | Structured, external system |
| Audit entry IDs | MCP (QMS mock) | Structured, external system |

---

### 8.6 Human-in-the-Loop flow

```
                          Durable Orchestrator
                                  │
                    Activity: NotifyOperator
                          │
              Azure SignalR ──► React UI push
                          │
                   Operator бачить:
                   ┌──────────────────────────────┐
                   │ ⚠️  DEVIATION: GR-204         │
                   │ Impeller Speed: 580 RPM       │
                   │ (limit: 600–800 RPM | 4 min)  │
                   │                              │
                   │ 🤖 AI Risk: MEDIUM (84%)      │
                   │ Root cause: motor load...     │
                   │ CAPA: 1. Moisture check...    │
                   │ Evidence: SOP-DEV-001 §4.2   │
                   │                              │
                   │ [✅ Approve] [❌ Reject]       │
                   │ [❓ Need more info]            │
                   └──────────────────────────────┘
                          │
                          │  [якщо confidence < 0.7]
                          │  ⚠️ LOW_CONFIDENCE банер:
                          │  «Мене AI впевненість 58% — коментар обов'язковий»
                          │
          ┌───────────────┼─────────────────┬──────────────┐
          ↓               ↓                 ↓              ↓
       Approved        Rejected          More info    LOW_CONFIDENCE
          │               │                 │         + human override
  ExecuteDecision   CloseRejected      loop → agents      │
  (Execution Agent)    + log              + more context   │
          │                                          ExecuteDecision
          │                                          audit: human_override=true
          └──────────────────────────────────────────────┘
                          │
                  finalize_audit records:
                  confidence_score, human_override,
                  operator_comment (mandatory if override)
```

---

### 8.7 Технічний стек — фінальний

| Layer | Tech | Notes |
|---|---|---|
| Backend | Python 3.11 | Azure Functions v2, Durable Functions |
| Agents | Azure AI Foundry Agent Service | Python SDK `azure-ai-projects` |
| MCP servers | Python `mcp` library | stdio transport (local для demo) |
| Workflow | Azure Durable Functions | `azure-durable-functions` Python |
| Database | Azure Cosmos DB | `azure-cosmos` Python SDK |
| Queue | Azure Service Bus | `azure-servicebus` Python SDK |
| SignalR | Azure SignalR Service | REST API negotiation |
| AI Search | Azure AI Search | `azure-search-documents` Python SDK |
| Frontend | React 18 + Vite + TypeScript | `@azure/msal-react` for Entra ID |
| Auth | Azure Entra ID (MSAL) | Managed Identities на всіх Functions |
| Secrets | Azure Key Vault | `azure-keyvault-secrets` + Managed Identity |
| IaC | Bicep | `infra/main.bicep` + 5 modules |
| CI/CD | GitHub Actions | `.github/workflows/ci.yml` (PR) + `deploy.yml` (push main) |

---

### 8.8 Задеплоєні Azure ресурси

> Subscription: `Sandbox AI DS - 1003462` (`d16bb0b5-b7b2-4c3b-805b-f7ccb9ce3550`)  
> Resource Group: `ODL-GHAZ-2177134`  
> Region: **Sweden Central**  
> Bicep модуль: `infra/main.bicep` → `infra/modules/`  
> Унікальний суфікс RG: `erzrpo`

| Azure ресурс | Ім'я | Тип | Bicep модуль | Призначення |
|---|---|---|---|---|
| Storage Account | `stsentinelintelerzrpo` | `Microsoft.Storage/storageAccounts` | `modules/storage.bicep` | Стан Durable Functions + **5 Blob containers** для document ingestion (`blob-sop`, `blob-manuals`, `blob-gmp`, `blob-bpr`, `blob-history`). Наразі задеплоєно 1 container `documents` → потребує оновлення в T-036/T-041. |
| Log Analytics | `log-sentinel-intel-dev-erzrpo` | `Microsoft.OperationalInsights/workspaces` | `modules/monitoring.bicep` | Workspace для App Insights (30 днів retention) |
| Application Insights | `appi-sentinel-intel-dev-erzrpo` | `Microsoft.Insights/components` | `modules/monitoring.bicep` | Traces, metrics, exceptions для Functions |
| Cosmos DB Account | `cosmos-sentinel-intel-dev-erzrpo` | `Microsoft.DocumentDB/databaseAccounts` | `modules/cosmos.bicep` | Serverless, database `sentinel-intelligence`, 5 containers |
| Service Bus | `sb-sentinel-intel-dev-erzrpo` | `Microsoft.ServiceBus/namespaces` | `modules/servicebus.bicep` | Standard tier, queue `alert-queue` (maxDelivery=5, DLQ) |
| App Service Plan | `asp-func-sentinel-intel-dev-erzrpo` | `Microsoft.Web/serverFarms` | `modules/functions.bicep` | Consumption plan (Y1), Linux |
| Azure Functions | `func-sentinel-intel-dev-erzrpo` | `Microsoft.Web/sites` | `modules/functions.bicep` | Python 3.11, `function_app.py` |

**Cosmos DB containers** (в БД `sentinel-intelligence`):

| Container | Partition Key | Призначення |
|---|---|---|
| `incidents` | `/equipmentId` | Основний документ incident + AI analysis |
| `equipment` | `/id` | Mock CMMS: master data, validated params |
| `batches` | `/equipmentId` | Mock MES: поточні та завершені batch records |
| `capa-plans` | `/incidentId` | Згенеровані CAPA plans |
| `approval-tasks` | `/incidentId` | Human-in-the-loop approval tasks |

**Ще не задеплоєно** (наступні кроки):

| Ресурс | Тип | Tasks |
|---|---|---|
| Azure AI Search | `Microsoft.Search/searchServices` | T-037 |
| Azure SignalR | `Microsoft.SignalRService/signalR` | T-030 |
| Azure Key Vault | `Microsoft.KeyVault/vaults` | T-038 |
| Azure Static Web App | `Microsoft.Web/staticSites` | T-032 |
| Azure AI Foundry | `Microsoft.CognitiveServices/accounts` | T-025–T-027 |

---

### 8.9 Два рівні оркестрації

> Вимоги (01-requirements §4) та AS-SUBMITTED схема називали Foundry «Agent Orchestrator». У v2.0 ця роль **розбита на два рівні з різними відповідальностями**.

```
┌─────────────────────────────────────────────────────────────────────┐
│  РІВЕНЬ 1 — Workflow Orchestrator (Azure Durable Functions)         │
│  Відповідає за: послідовність кроків, HITL паузу,                  │
│                 таймаут 24h, стан всього процесу                    │
│                                                                     │
│  1. CreateIncident     ──► Cosmos DB                                │
│  2. EnrichContext      ──► Cosmos DB (equipment/batch)              │
│  3. RunAgents ─────────────────────────────────────────┐           │
│  4. NotifyOperator     ──► Azure SignalR                │           │
│  5. ⏸ waitForExternalEvent("operator_decision") ← ПАУЗА до 24h    │
│  6a. "approved"  → ExecuteDecision ─────────────────────┐          │
│  6b. "rejected"  → CloseIncident                        │           │
│  6c. "more_info" → loop до кроку 2                      │           │
│  7. FinalizeAuditRecord ──► Cosmos DB                   │           │
└───────────────────────────────────────┬──────────────────┘           │
             ↓ (activity calls)         │                             │
┌────────────────────────────────────── ▼ ────────────────────────────┤
│  РІВЕНЬ 2 — AI Orchestrator (Azure AI Foundry Agent Service)        │
│  Відповідає за: агентну логіку, tool calls, reasoning loop,        │
│                 routing між агентами всередині одного кроку         │
│                                                                     │
│  Крок 3 "RunAgents":                                                │
│    Research Agent  ──► RAG (AI Search) + MCP-cosmos-db             │
│       └─ внутрішній reasoning loop (Foundry manages)               │
│    Document Agent  ──► structured output, confidence gate          │
│       └─ внутрішній reasoning loop (Foundry manages)               │
│                                                                     │
│  Крок 6a "ExecuteDecision":                                         │
│    Execution Agent ──► MCP-qms-mock + MCP-cmms-mock               │
└─────────────────────────────────────────────────────────────────────┘
```

**Чому не один рівень?**

| Питання | Durable Functions | Foundry Agent Service |
|---|---|---|
| Керує: | workflow (кроки процесу) | AI reasoning (агентна логіка) |
| HITL пауза | ✅ `waitForExternalEvent` — до 24h | ❌ function_call timeout — 10 хв |
| Стан між кроками | ✅ persisted у Azure Storage | ✅ всередині одного run |
| Retry/DLQ | ✅ вбудований | ❌ треба вручну |
| Агентний routing | ❌ не розуміє LLM | ✅ вбудований |

**Відповідь на питання «де оркестратор?»**: Durable Functions — це **workflow orchestrator** (=«директор виробництва», керує процесом і людьми). Foundry — це **AI orchestrator** (=«мозок», який керує агентами всередині кожного кроку). Обидва — «оркестратори», але на різних рівнях.

---

### 8.10 ADR-001: Human-in-the-Loop — Durable waitForExternalEvent vs Foundry-native

> **Тип:** Architecture Decision Record  
> **Дата рішення:** 17 квітня 2026  
> **Статус:** Прийнято ✅

#### Контекст
GMP-виробництво вимагає mandatory human approval перед виконанням work order. Оператор має до 24 годин на рішення (відповідно до SOPs). Потрібен механізм:
- призупинити agentний workflow після генерації рекомендацій
- дочекатися рішення оператора (Approve / Reject / More info)
- відновити workflow з результатом рішення
- якщо 24h минуло — автоескалювати до QA Manager

#### Розглянуті варіанти

**Варіант A: Foundry function_call + previous_response_id**
```
response = openai.responses.create(input=...)
# response.output[i].type == "function_call" → агент "чекає"
# ... зберегти previous_response_id у Cosmos ...
# ... оператор вирішує (пізніше) ...
response = openai.responses.create(input=[FunctionCallOutput(...)], 
                                   previous_response_id=saved_id)
```
**Проблема:** run expires після **10 хвилин** після створення — `previous_response_id` протухає і не може бути відновлений. Джерело: [Microsoft Foundry docs (квітень 2026)](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/function-calling):
> *"Runs expire 10 minutes after creation. Submit your tool outputs before they expire."*

**Варіант B: Durable Functions waitForExternalEvent** ← **ОБРАНО**
```python
# orchestrator (Python)
yield context.wait_for_external_event("operator_decision")
# ↑ безкоштовно спить скільки завгодно (Azure Storage persists state)

# React UI → HTTP endpoint → resume orchestrator
POST /runtime/webhooks/durabletask/instances/{id}/raiseEvent/operator_decision
{"decision": "approved", "comment": "LIMS verified, proceed"}
```

#### Рішення
**Варіант B (Durable Functions `waitForExternalEvent`)**.

#### Обґрунтування

| Критерій | Foundry function_call | Durable waitForExternalEvent |
|---|---|---|
| Максимальна пауза | ❌ 10 хвилин | ✅ необмежено (24h+) |
| Відновлення після restart/crash | ❌ втрачається | ✅ persisted у Azure Storage |
| Вартість під час паузи | n/a (протухає) | ✅ $0 (Consumption plan) |
| Resume API | N/A | ✅ `raiseEvent` HTTP |
| Timeout + ескалація | ❌ немає | ✅ `create_timer` + race pattern |
| Вже в requirements.txt | ✅ (`azure-ai-projects`) | ✅ (`azure-durable-functions`) |

#### Наслідки
- Foundry агенти запускаються як короткі **activity functions** (секунди–хвилини) — вкладаються в 10-хв ліміт
- Загальний workflow state живе у Durable (Azure Storage), а не у Foundry threads
- `approval-tasks` Cosmos container зберігає pending approval для React UI
- Azure SignalR пушить notification до React: «очікується рішення оператора»
- `POST /api/incidents/{id}/decision` HTTP endpoint викликає `raise_event` → orchestrator resume

---

### 8.11 Розбивка на Azure Functions — повна карта

> Деталізація всіх функцій, які реалізують workflow. Кожна з них — окрема Python-функція у `backend/function_app.py`.

#### Потік від Service Bus до паузи

```
Service Bus: alert-queue
      │  trigger
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│  alert_processor  (Service Bus Trigger)                             │
│                                                                     │
│  • Приймає alert з черги                                            │
│  • Генерує incident_id (uuid)                                       │
│  • Викликає client.start_new("deviation_orchestrator", input=...)   │
│  • Завершується одразу — оркестратор запускається незалежно         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  start_new()
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  deviation_orchestrator  (Durable Orchestrator)                     │
│  ⚠️  Не виконується лінійно — Durable replay-механізм              │
│                                                                     │
│  yield CallActivity("create_incident")                              │
│  yield CallActivity("enrich_context")                               │
│  yield CallActivity("run_research_agent")   ─► Foundry             │
│  yield CallActivity("run_document_agent")   ─► Foundry             │
│  yield CallActivity("notify_operator")      ─► SignalR + Cosmos    │
│                                                                     │
│  ⏸  decision = yield WaitForExternalEvent("operator_decision")     │
│     ← оркестратор серіалізується в Azure Storage, RAM звільняється │
│                                                                     │
│  if decision == "approved":                                         │
│      yield CallActivity("run_execution_agent")  ─► Foundry         │
│  elif decision == "rejected":                                       │
│      yield CallActivity("close_incident")                           │
│  elif decision == "more_info":                                      │
│      # loop back to enrich_context                                  │
│  yield CallActivity("finalize_audit")       ─► Cosmos DB           │
└─────────────────────────────────────────────────────────────────────┘
```

#### Activity functions (викликаються оркестратором)

| Activity | Що робить | Куди ходить |
|---|---|---|
| `create_incident` | Створює документ incident у Cosmos DB | Cosmos: `incidents` |
| `enrich_context` | Читає equipment + batch за ID з алерту | Cosmos: `equipment`, `batches` |
| `run_research_agent` | Запускає Foundry Research Agent: RAG + MCP → повертає structured context JSON | Foundry SDK (`azure-ai-projects`) |
| `run_document_agent` | Запускає Foundry Document Agent: будує decision package, зберігає CAPA чернетку | Foundry SDK → Cosmos: `capa-plans` |
| `notify_operator` | 1. Пише record у `approval-tasks` (status: pending) 2. POST до SignalR REST API → push до React UI | Cosmos: `approval-tasks`, Azure SignalR |
| `run_execution_agent` | Запускає Foundry Execution Agent після approval: create_work_order + create_audit_entry | Foundry SDK → MCP-QMS, MCP-CMMS |
| `close_incident` | Оновлює incident status: "rejected" | Cosmos: `incidents` |
| `finalize_audit` | Пише фінальний audit record: рішення + timestamps + агентні кроки | Cosmos: `approval-tasks`, `incidents` |

#### Як оркестратор прокидається (FN-2)

```
React UI: оператор натискає [✅ Approve] / [❌ Reject] / [❓ More info]
      │
      │  POST /api/incidents/{id}/decision
      │  { "decision": "approved", "comment": "LIMS verified" }
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│  decision_handler  (HTTP Trigger)                                   │
│                                                                     │
│  1. Validates request (auth via Entra ID)                           │
│  2. Читає instance_id з Cosmos: approval-tasks (by incident_id)     │
│  3. await client.raise_event(                                       │
│         instance_id,                                                │
│         "operator_decision",                                        │
│         { "decision": "approved", "comment": "..." }               │
│     )                                                               │
│  4. Повертає HTTP 200                                               │
│                                                                     │
│  → Durable знаходить instance у Azure Storage                       │
│  → replay orchestrator від початку                                  │
│  → доходить до WaitForExternalEvent → event вже є → продовжує      │
└─────────────────────────────────────────────────────────────────────┘
```

#### Повна карта функцій

| Функція | Тип тригера | Файл | Роль |
|---|---|---|---|
| `alert_processor` | Service Bus | `function_app.py` | Вхідна точка: алерт → старт оркестратора |
| `deviation_orchestrator` | Durable Orchestrator | `function_app.py` | Координує весь workflow |
| `create_incident` | Durable Activity | `function_app.py` | Cosmos write: новий incident |
| `enrich_context` | Durable Activity | `function_app.py` | Cosmos read: equipment + batch |
| `run_research_agent` | Durable Activity | `function_app.py` | Foundry: Research Agent |
| `run_document_agent` | Durable Activity | `function_app.py` | Foundry: Document Agent → capa-plans |
| `notify_operator` | Durable Activity | `function_app.py` | Cosmos write + SignalR push |
| `run_execution_agent` | Durable Activity | `function_app.py` | Foundry: Execution Agent → QMS/CMMS |
| `close_incident` | Durable Activity | `function_app.py` | Cosmos update: status=rejected |
| `finalize_audit` | Durable Activity | `function_app.py` | Cosmos write: audit record |
| `decision_handler` | HTTP | `function_app.py` | REST endpoint: `POST /api/incidents/{id}/decision` → `raise_event` |
| `get_incidents` | HTTP | `function_app.py` | REST: `GET /api/incidents` |
| `get_incident_by_id` | HTTP | `function_app.py` | REST: `GET /api/incidents/{id}` |
| `ingest_alert` | HTTP | `function_app.py` | REST: `POST /api/alerts` → Service Bus |

> **Idempotency:** `POST /api/alerts` повинен приймати `alert_id` у payload. Перед публікацією в Service Bus — перевірити чи існує incident з `sourceAlertId == alert_id` у Cosmos. Якщо так — повернути `HTTP 200` з existing `incident_id` без повторного старту оркестратора. Це запобігає дублікатам при retry від SCADA/MES.

> **Foundry** — не Azure Function. Це зовнішній сервіс, який `run_*_agent` activities викликають через `azure-ai-projects` SDK. Foundry запускає агента, агент виконує tool calls (MCP/RAG), повертає result — activity завершується, оркестратор продовжує.

---

### 8.12 Azure SignalR — контракт

**Hub name:** `deviationHub`  
**Endpoint для negotiate:** `GET /api/negotiate` (Azure Functions HTTP trigger з SignalR input binding)  
**Auth:** Bearer token (Entra ID) → SignalR Groups per user role

#### Groups (підписки)

| Group | Хто підписується | Які events отримує |
|---|---|---|
| `role:operator` | Всі operator-role users | `incident_pending_approval`, `incident_updated` |
| `role:qa-manager` | QA Manager role | `incident_escalated`, `incident_pending_approval` |
| `incident:{id}` | Будь-хто хто відкрив деталі incident | `incident_status_changed`, `agent_step_completed` |

#### Events (server → client)

| Event name | Payload | Коли |
|---|---|---|
| `incident_pending_approval` | `{ incident_id, equipment_id, risk_level, created_at }` | Після `notify_operator` activity |
| `incident_status_changed` | `{ incident_id, old_status, new_status, timestamp }` | При кожній зміні status в Cosmos |
| `agent_step_completed` | `{ incident_id, step, result_summary }` | Після completion кожної Durable activity |
| `incident_escalated` | `{ incident_id, escalated_to, reason }` | Після 24h timer → QA Manager |

#### Negotiation flow

```
React UI → GET /api/negotiate (with Bearer token)
        ← { url: "https://...signalr.../client/", accessToken: "..." }
React UI → connects to SignalR hub with accessToken
        → joins group `role:{userRole}` + `incident:{currentIncidentId}`
```

---

### 8.13 Шар документів — Ingestion Architecture

> **Нове в v2.5.** Перехід від одного blob container `documents` з path-based routing до **5 окремих контейнерів**, по одному на тип джерела. Кожен контейнер має власну Azure Function blob trigger з різною логікою чанкування.

#### Чому окремі контейнери (а не один container з path-routing)?

| Причина | Деталь |
|---|---|
| **Різна логіка чанкування** | BPR містить CPP-таблиці — потрібен table-aware chunking щоб таблиці не розбивались між чанками. SOPs — лінійний текст. Incident history — генерується зі скрипту. |
| **Різна частота оновлень** | GMP-регуляції — рідко (місяцями); SOPs — квартально; BPR — при кожному product validation cycle; incident history — динамічно. Окремі контейнери дозволяють тригерити лише потрібний інгестор. |
| **Різні upstream джерела (production)** | QMS → `blob-sop`; LIMS/EBR → `blob-bpr`; CMMS → `blob-manuals`; регуляторна база → `blob-gmp`. Для hackathon — ручний upload через `scripts/upload_documents.py`. |
| **Незалежні retry/failure** | Відмова BPR-інгестора не блокує SOP або GMP pipeline. Кожен blob trigger retry незалежний. |

#### 5 Blob Storage containers → 5 Ingestors → 5 AI Search indexes

| Container | Local source | Ingestor Function | Target Index | Chunking strategy |
|---|---|---|---|---|
| `blob-sop` | `data/documents/sop/` | `ingest_sop_document` | `idx-sop-documents` | 500 токенів, 50 overlap |
| `blob-manuals` | `data/documents/manuals/` | `ingest_equipment_manual` | `idx-equipment-manuals` | 500 токенів + `equipment_id` tag з імені файлу |
| `blob-gmp` | `data/documents/gmp/` | `ingest_gmp_policy` | `idx-gmp-policies` | 500 токенів + clause metadata extraction |
| `blob-bpr` | `data/documents/bpr/` | `ingest_bpr_document` | `idx-bpr-documents` | **Table-aware** — Markdown-таблиці CPP не розбиваються, max ~1200 токенів |
| `blob-history` | Generated from Cosmos incidents | `ingest_history_document` | `idx-incident-history` | Generated by `scripts/generate_history_chunks.py` |

> ⚠️ **BPR table-aware chunking — чому це critical для GMP:** BPR-документи містять таблиці CPP-параметрів (наприклад, "Impeller NOR: 650±50 RPM | PAR: 600–750 RPM | Equipment range: 200–800 RPM"). Якщо таблиця розбивається між чанками, Research Agent отримує неповну таблицю і ризикує синтезувати параметр — це GMP compliance risk (AI fabricates a process limit). Функція `ingest_bpr_document` детектує Markdown-таблиці (`|---|` паттерн) і зберігає їх цілими.

#### Agent → Index mapping

| Agent | Queries indexes | Purpose |
|---|---|---|
| **Research Agent** | Всі 5: `idx-sop-documents`, `idx-equipment-manuals`, `idx-gmp-policies`, `idx-bpr-documents`, `idx-incident-history` | Повний контекст: процедури + специфікації продукту + регулятори + historical cases |
| **Document Agent** | Жодного (використовує output Research Agent) | Отримує вже зібраний контекст |
| **Execution Agent** | Жодного | Тільки structured tool calls (MCP: CMMS + QMS) |

#### Bicep — 5 blob containers (оновлення `infra/modules/storage.bicep`)

```
infra/modules/storage.bicep — provisioned containers:
  'blob-sop'       ← new (замінює 'documents' для document ingestion)
  'blob-manuals'   ← new
  'blob-gmp'       ← new
  'blob-bpr'       ← new
  'blob-history'   ← new
```

> **Hackathon note:** Storage Account `stsentinelintelerzrpo` вже задеплоєно. Container `documents` вже існує — може залишитись для Durable Functions state (auto-managed). 5 нових containers додаються інкрементально оновленням storage.bicep + redeploy. Це робота в **T-036** (ingestion pipeline) + відповідне оновлення **T-041** (Bicep).

---

## 9. Changelog архітектури

| Дата | Версія | Зміна | Пов'язаний Gap |
|---|---|---|---|
| 2026-03-26 | v1.0 | Initial submission | — |
| 2026-04-17 | v2.0 | Full implementation design: Durable Functions, Cosmos DB, SignalR, Service Bus, 3 MCP servers, React frontend, Entra ID RBAC, Key Vault, Bicep IaC, GitHub Actions | Gap #1–6 ✅ |
| 2026-04-17 | v2.1 | **First deployment:** 7 Azure ресурсів задеплоєно через Bicep. GitHub Actions CI/CD зелений. `func-sentinel-intel-dev-erzrpo` живий. Cosmos DB Serverless (5 containers). Service Bus `alert-queue`. App Insights + Log Analytics. | T-041, T-042 ✅ |
| 2026-04-17 | v2.2 | **ADR-001** (§8.10): задокументовано вибір Durable `waitForExternalEvent` над Foundry-native HITL (10-хв ліміт Foundry несумісний з 24h approval). §8.9: пояснення двох рівнів оркестрації (Durable = workflow, Foundry = AI). | — |
| 2026-04-17 | v2.3 | **§8.11**: повна карта Azure Functions — усі 14 функцій з типами тригерів, ролями та потоком від Service Bus → оркестратор → activities → `raise_event`. | — |
| 2026-04-17 | v2.4 | **Рев'ю:** §4 AS-SUBMITTED disclaimer + Component Evolution table (v1.0→v2.0); §8.3 JSON output schemas для всіх агентів + confidence gate failure matrix; §8.4 cross-partition query note; §8.6 LOW_CONFIDENCE гілка в HITL flow; §8.11 idempotency note; §8.12 SignalR contract (хуб, groups, events, negotiation flow). | Review |
| 2026-04-17 | v2.5 | **Document Layer Architecture:** §8.1 AI Search: 4→5 indexes (додано `idx-bpr-documents`); §8.2 RAG Storage row оновлено; §8.3 Research Agent: додано `search_bpr_documents` RAG tool; §8.5 RAG vs Direct: додано BPR row; §8.8 Storage: 1 container → 5 окремих blob containers per source type; §8.13 новий розділ — Document Layer Ingestion Architecture (5 containers, 5 ingestors, table-aware BPR chunking, agent→index mapping). T-036 + T-025 оновлено. | Gap #4 review |

---

← [01 Вимоги](./01-requirements.md) · [03 Аналіз →](./03-analysis.md)
