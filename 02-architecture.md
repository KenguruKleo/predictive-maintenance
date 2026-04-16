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

## 8. Поточна версія v2.0 (IN-PROGRESS — Implementation Phase)

> Архітектура v2.0 розроблена для Implementation Phase (квітень 2026).  
> Мова: **Python**. Frontend: **React + Vite** (Azure Static Web Apps).  
> MCP servers: **локальний stdio transport**.  
> Усі 6 gaps з тріажу закрито в цьому дизайні.

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
│   SIGNALR    │  │  AGENT SERVICE    │  │   (5 collections)        │
│              │  │                   │  │                          │
│  Real-time   │  │  Orchestrator     │  │  incidents               │
│  push to     │  │  ├─ Research Agt  │  │  incident_events         │
│  React UI    │  │  ├─ Document Agt  │  │  equipment (mock CMMS)   │
│  (Gap #5 ✅) │  │  └─ Execution Agt │  │  batches (mock MES)      │
└──────────────┘  │                   │  │  templates               │
                  │  MCP Servers:     │  └──────────────────────────┘
                  │  ├─ mcp-cosmos-db │
                  │  ├─ mcp-qms-mock  │
                  │  └─ mcp-cmms-mock │
                  └───────────────────┘
                          │
                          ▼
              ┌───────────────────────────┐
              │  AZURE AI SEARCH          │
              │  4 indexes (RAG):         │
              │  ├─ idx-equipment-manuals │
              │  ├─ idx-sop-documents     │
              │  ├─ idx-gmp-policies      │
              │  └─ idx-incident-history  │
              └───────────────────────────┘

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
| **Incident DB** | Azure Cosmos DB | 5 collections: incidents, events, equipment, batches, templates | — |
| **RAG Storage** | Azure AI Search | 4 indexes: manuals, SOPs, GMP policies, incident history | Gap #4 |
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
- **RAG tools:** `search_sop_documents`, `search_equipment_manuals`, `search_incident_history`, `search_gmp_policies`
- **MCP tools:** `get_equipment(id)`, `get_batch(id)`, `search_incidents(equipment_id, date_range)`
- **Output:** structured JSON `{ context_enrichment, relevant_sops, historical_cases, equipment_status }`

#### Document Agent
- **Мета:** скласти decision package з evidence
- **Input:** Research Agent output + incident details
- **Output:** `{ work_order_draft, audit_entry_draft, recommendation, risk_level, confidence, evidence_citations }`
- **RAI gate:** якщо `confidence < 0.7` → `risk_level = "LOW_CONFIDENCE"` → operator побачить попередження

#### Execution Agent
- **Мета:** виконати дії після human approval
- **Triggers:** тільки після `operator_decision == "approved"`
- **MCP tools:** `create_work_order(payload)` (CMMS mock), `create_audit_entry(payload)` (QMS mock)
- **Output:** `{ work_order_id, audit_entry_id, execution_timestamp }`

---

### 8.4 Cosmos DB — схема колекцій

| Колекція | Partition Key | Призначення |
|---|---|---|
| `incidents` | `/equipment_id` | Основний документ incident + AI analysis + workflow state |
| `incident_events` | `/incident_id` | Audit log кожної зміни (event sourcing) |
| `equipment` | `/id` | Mock CMMS: equipment master data, validated params, PM history |
| `batches` | `/equipment_id` | Mock MES: поточні та завершені batch records |
| `templates` | `/type` | Work order та audit entry templates (IT Admin manages) |

---

### 8.5 RAG vs Direct — коли що використовується

| Дані | Спосіб | Чому |
|---|---|---|
| Equipment validated parameters | MCP (Cosmos DB) | Структуровані — точне значення важливіше за semantic match |
| Current batch context | MCP (Cosmos DB) | Structured, current state |
| Historical incidents (semantic) | RAG (AI Search idx-incident-history) | Semantic similarity — "find similar cases" |
| SOPs/procedures | RAG (AI Search idx-sop-documents) | Semantic search по тексту процедур |
| Equipment manuals | RAG (AI Search idx-equipment-manuals) | Semantic search по технічній документації |
| GMP policies/regulations | RAG (AI Search idx-gmp-policies) | Semantic search по регуляторним вимогам |
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
          ┌───────────────┼─────────────────┐
          ▼               ▼                 ▼
       Approved        Rejected          More info
          │               │                 │
  ExecuteDecision   CloseRejected      loop → agents
  (Execution Agent)    + log              + more context
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
| IaC | Bicep | `infra/main.bicep` + modules |
| CI/CD | GitHub Actions | `.github/workflows/` |

---

## 9. Changelog архітектури

| Дата | Версія | Зміна | Пов'язаний Gap |
|---|---|---|---|
| 2026-03-26 | v1.0 | Initial submission | — |
| 2026-04-17 | v2.0 | Full implementation design: Durable Functions, Cosmos DB, SignalR, Service Bus, 3 MCP servers, React frontend, Entra ID RBAC, Key Vault, Bicep IaC, GitHub Actions | Gap #1–6 ✅ |

---

← [01 Вимоги](./01-requirements.md) · [03 Аналіз →](./03-analysis.md)
