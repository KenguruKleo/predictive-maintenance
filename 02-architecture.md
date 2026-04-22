# 02 · Архітектура

← [README](./README.md) · [01 Вимоги](./01-requirements.md) · [03 Аналіз](./03-analysis.md) · [04 План дій](./04-action-plan.md)

> **Призначення:** цільова архітектура Sentinel Intelligence — як система має виглядати у production (TO-BE). Пов'язані документи (історія, ADR, скорочення прототипу) перераховані у розділі [Related documents](#related-documents) наприкінці.

---

## Зміст

1. [Overview](#1-overview)
2. [Процеси AS-IS vs TO-BE](#2-процеси-as-is-vs-to-be)
3. [High-level architecture](#3-high-level-architecture)
4. [End-to-end data flow](#4-end-to-end-data-flow)
5. [Component catalog](#5-component-catalog)
6. [Two-level orchestration](#6-two-level-orchestration)
7. [Agent design](#7-agent-design)
8. [Human-in-the-loop](#8-human-in-the-loop)
9. [Data persistence](#9-data-persistence)
10. [RAG vs Direct data access](#10-rag-vs-direct-data-access)
11. [Backend API surface](#11-backend-api-surface)
12. [Azure Functions map](#12-azure-functions-map)
13. [Real-time layer — SignalR](#13-real-time-layer--signalr)
14. [Document ingestion](#14-document-ingestion)
15. [Agent observability](#15-agent-observability)
16. [Security architecture](#16-security-architecture)
17. [Reliability architecture](#17-reliability-architecture)
18. [Operational Excellence & Performance](#18-operational-excellence--performance)
19. [Responsible AI](#19-responsible-ai)
20. [Identity, roles & RBAC](#20-identity-roles--rbac)
21. [Technical stack](#21-technical-stack)
22. [Related documents](#related-documents)

---

## 1. Overview

**Sentinel Intelligence** — AI-powered multi-agent Operations Assistant на Azure AI Foundry для GMP-виробництва.

Система:

- детектує anomaly/deviation events із SCADA/MES/IoT сигналів;
- збагачує їх контекстом (batch, equipment, validated parameters);
- виконує агентне reasoning через RAG на SOP / BPR / GMP / CAPA history та MCP-tool доступ до структурованих даних;
- генерує CAPA рекомендації, work-order draft та audit-ready записи;
- зупиняється на mandatory human approval перед будь-яким execution (GxP requirement);
- логує повний agent + business трейс для compliance та post-mortem аналізу.

**Стейкхолдери:**

| Роль | Участь |
|---|---|
| Production Operator | Отримує alert, переглядає decision package, approves / denies / запитує more info |
| QA Manager | Обробляє escalated incidents, фінальне approval по складних кейсах |
| Maintenance Technician | Read-only доступ до work orders |
| Auditor | Read-only доступ до audit trail + agent telemetry |
| IT Admin | Управління templates, перегляд agent telemetry, JIT-eligible Contributor |

---

## 2. Процеси AS-IS vs TO-BE

**AS-IS (manual, 30–60 хв, оператор-залежний результат):**

```
Sensor Signal → Alert
  → Operator RECEIVES (manual, interprets context manually)
  → CHECK SOP/BPR (manual search)
  → MAKES DECISION (based on experience, incomplete info)
  → REGISTER CAPA (manual work order creation in QMS/CMMS)
  → CREATE REPORT (manual documentation for audit trail)
```

**TO-BE (AI-assisted, < 5 хв для decision, стандартизований результат):**

```
Sensor Signal → Alert (automated anomaly detection)
  → Context built AUTO (equipment + batch + historical)
  → SOP & data retrieval AUTO (relevant SOPs, BPRs, historical cases)
  → AI decision support AUTO (classification + CAPA + evidence)
  → CAPA / Work Order prepared AUTO (pre-filled for review)
  → Human review & approval MANUAL (GxP requirement)
  → Report generated AUTO (structured, inspection-ready)
  → CAPA recorded in QMS/CMMS AUTO
```

---

## 3. High-level architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SOURCES                                 │
│   SCADA · MES · IoT    ──►   POST /api/alerts                       │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│              AZURE SERVICE BUS — alert-queue                        │
│   Reliability: DLQ, retry, at-least-once, idempotency via alert_id  │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│        AZURE DURABLE FUNCTIONS — Workflow Orchestrator              │
│                                                                     │
│  deviation_orchestrator                                             │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ 1. create_incident          ──► Cosmos DB                  │    │
│  │ 2. enrich_context           ──► Cosmos DB (equipment/batch)│    │
│  │ 3. run_foundry_agents       ──► Azure AI Foundry            │    │
│  │    └─ Orchestrator Agent (Connected Agents pipeline)       │    │
│  │         ├─ Research Agent  (RAG × 5 + MCP-sentinel-db)     │    │
│  │         └─ Document Agent  (structured output + conf.gate) │    │
│  │ 4. notify_operator          ──► SignalR + Cosmos           │    │
│  │ 5. ⏸ waitForExternalEvent("operator_decision") / 24h timer │    │
│  │ 6a. approved   → run_execution_agent (MCP-QMS + MCP-CMMS)  │    │
│  │ 6b. rejected   → close_incident                             │    │
│  │ 6c. more_info  → re-run step 3 з додатковим контекстом     │    │
│  │ 7. finalize_audit           ──► Cosmos DB                  │    │
│  └────────────────────────────────────────────────────────────┘    │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────────────┐
          ▼               ▼                       ▼
┌──────────────┐  ┌───────────────────┐  ┌──────────────────────────┐
│   AZURE      │  │  AZURE AI FOUNDRY │  │   AZURE COSMOS DB        │
│   SIGNALR    │  │  AGENT SERVICE    │  │   Serverless             │
│              │  │                   │  │   8 containers:          │
│  Real-time   │  │  Orchestrator     │  │   incidents              │
│  push to UI  │  │  ├─ Research Agt  │  │   incident_events        │
│  deviationHub│  │  ├─ Document Agt  │  │   notifications          │
│              │  │  └─ Execution Agt │  │   equipment / batches    │
└──────────────┘  │                   │  │   capa-plans             │
                  │  MCP Servers:     │  │   approval-tasks         │
                  │  ├─ mcp-sentinel- │  │   templates              │
                  │  │     db         │  └──────────────────────────┘
                  │  ├─ mcp-qms       │                              
                  │  └─ mcp-cmms      │                              
                  └───────────────────┘                              
                          │                                           
                          ▼                                           
              ┌───────────────────────────┐
              │  AZURE AI SEARCH          │
              │  5 indexes (RAG):         │
              │  ├─ idx-sop-documents     │
              │  ├─ idx-equipment-manuals │
              │  ├─ idx-gmp-policies      │
              │  ├─ idx-bpr-documents  ★  │
              │  └─ idx-incident-history  │
              └───────────────────────────┘
                    ★ product-specific CPP ranges
                      (NOR narrower than equipment PAR)

┌─────────────────────────────────────────────────────────────────────┐
│                  BACKEND API — Azure Functions HTTP                 │
│  POST /api/alerts              POST /api/incidents/{id}/decision    │
│  GET  /api/incidents           GET  /api/incidents/{id}             │
│  GET  /api/incidents/{id}/events                                    │
│  GET  /api/incidents/{id}/agent-telemetry                           │
│  GET  /api/notifications       GET  /api/notifications/summary      │
│  GET/PUT /api/templates/{id}                                        │
│  GET  /api/equipment/{id}      GET  /api/batches/current/{eq_id}    │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│              REACT + VITE FRONTEND (Azure Static Web Apps)          │
│  operator      → Incident list + decision package + approval       │
│  qa-manager    → All incidents + escalation queue                  │
│  maint-tech    → Work orders view (read-only)                      │
│  auditor       → Full audit trail + agent telemetry (read-only)    │
│  it-admin      → Template management + agent telemetry diagnostics │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│               CROSS-CUTTING CONCERNS                                │
│  Identity:   Entra ID · MSAL · Managed Identity · App Roles        │
│  Network:    VNet · Private Endpoints · Private DNS · NSGs          │
│  Access:     Conditional Access (MFA, geo) · Azure PIM (JIT)       │
│  Secrets:    Azure Key Vault · 90-day rotation · Event Grid trigger │
│  Reliability:Service Bus DLQ · Durable retry · Circuit breaker ·    │
│              Fallback mode · Multi-region DR                        │
│  RAI:        Confidence gate 0.7 · Content Safety + Prompt Shield · │
│              Evidence-grounded output · Verification pass           │
│  Observability: App Insights · Log Analytics · FOUNDRY_PROMPT_TRACE │
│                 · Cosmos incident_events (business timeline)        │
│  IaC + CI/CD: Bicep modules · GitHub Actions · Foundry eval gates   │
└─────────────────────────────────────────────────────────────────────┘
```

> Діаграма інфраструктури з типами ресурсів та Bicep-модулями: [infra/diagram.md](./infra/diagram.md) (Mermaid) та [infra/architecture.drawio](./infra/architecture.drawio).
>
---

## 4. End-to-end data flow

**Step 1 — Detect.** SCADA/MES/IoT система публікує alert → `POST /api/alerts` (HTTP Function `ingest_alert`) → alert записується у Service Bus `alert-queue`. Idempotency: `ingest_alert` перевіряє `sourceAlertId` у Cosmos перед публікацією.

**Step 2 — Trigger workflow.** Service Bus trigger `alert_processor` приймає повідомлення, генерує `incident_id`, запускає Durable orchestrator `deviation_orchestrator` через `client.start_new(...)`.

**Step 3 — Create & enrich.** Orchestrator послідовно викликає:

- `create_incident` — записує базовий incident у Cosmos `incidents`;
- `enrich_context` — дочитує `equipment` + `batches` за ID з alert-у.

**Step 4 — Agent reasoning.** Activity `run_foundry_agents` запускає Foundry **Orchestrator Agent**. Orchestrator керує Connected Agents pipeline:

- **Research Agent** (sub-agent via `AgentTool`) паралельно використовує RAG (Azure AI Search × 5 indexes) + MCP tools (`mcp-sentinel-db`) та повертає `ResearchAgentOutput`;
- **Document Agent** (sub-agent via `AgentTool`) приймає `ResearchAgentOutput`, застосовує confidence gate 0.7, повертає `DocumentAgentOutput` із recommendation, evidence citations, CAPA steps, work_order_draft, audit_entry_draft.

Foundry нативно керує reasoning loop та `max_iterations`. Backend виконує окремий **verification pass** над citations перед persist.

**Step 5 — Notify operator.** Activity `notify_operator` пише записи у `approval-tasks`, `notifications`, `incident_events` і публікує event у Azure SignalR `deviationHub` → React UI.

**Step 6 — Human decision.** Operator дивиться decision package: AI рекомендацію (`agent_recommendation: APPROVE | REJECT`), rationale, evidence, **редаговані форми** WO draft та audit entry draft (pre-filled від Document Agent; обов'язкові при Approve). Натискає `Approve` / `Reject` / `More info`. `POST /api/incidents/{id}/decision` викликає Durable `raise_event("operator_decision", ...)` → orchestrator прокидається.

- `more_info` → orchestrator додає `operator_question` до контексту, повторює `run_foundry_agents` (до `MAX_MORE_INFO_ROUNDS`);
- `approved` → `run_execution_agent`; payload для WO + audit entry береться з оператором відредагованих форм; `operator_agrees_with_agent = (decision == agent_recommendation)`;
- `rejected` → `close_incident`; audit record зберігає `outcome = "rejected"` та `operator_agrees_with_agent`; async feedback-подія надсилається до alerting-системи (`ALERT_FEEDBACK_URL`, configurable) — дозволяє SCADA/MES навчатись на false positive сигналах;
- Timeout `HITL_TIMEOUT_HOURS` (default: 24h; **рекомендовано ≤ 1h для безперервного виробництва**) → Durable escalate до QA Manager; operator переходить у **read-only**; QA Manager отримує повний decision UI.

**Step 7 — Execute.** Activity `run_execution_agent` запускає Foundry Execution Agent, який через MCP servers виконує реальні інтеграції: `create_work_order` (mcp-cmms → CMMS: SAP PM / IBM Maximo) та `create_audit_entry` (mcp-qms → QMS: SAP QM / TrackWise / Veeva Vault). Payload формується з оператором верифікованих та відредагованих форм (заповнені вручну у разі BLOCKED-стану).

**Step 8 — Finalize.** Activity `finalize_audit` записує фінальний audit record (`confidence_score`, `human_override`, `human_override_text`, `operator_comment`, `operator_agrees_with_agent`, timestamps, agent steps) у `incident_events` + оновлює `incidents` статус. Blob trigger синхронізує closed incident у `idx-incident-history`.

---

## 5. Component catalog

| Компонент | Технологія | Роль |
|---|---|---|
| **Ingestion API** | Azure Functions HTTP (Python) | Приймає зовнішні alert-и, idempotency через `sourceAlertId`, публікує у Service Bus |
| **Alert Queue** | Azure Service Bus Standard | Decoupled ingestion, DLQ, 3 auto-retries, at-least-once delivery |
| **Workflow Orchestrator** | Azure Durable Functions (Python) | Stateful orchestration всього процесу, HITL пауза, 24h timeout, retry/DLQ |
| **AI Orchestrator** | Azure AI Foundry Agent Service | Connected Agents routing, reasoning loop, native MCP + RAG tool connections |
| **Orchestrator Agent** | Foundry prompt agent | Координує Research → Document pipeline, керує reasoning loop та `max_iterations` |
| **Research Agent** | Foundry agent + 5 RAG tools + MCP | Збирає equipment state, batch context, relevant SOPs, historical cases |
| **Document Agent** | Foundry agent + templates + confidence gate | Draft: recommendation, risk level, evidence citations, CAPA steps, WO/audit drafts |
| **Execution Agent** | Foundry agent + MCP-QMS/CMMS | Після approval: `create_work_order` → CMMS + `create_audit_entry` → QMS |
| **mcp-sentinel-db** | Python stdio MCP server | Tools: `get_incident`, `get_equipment`, `get_batch`, `search_incidents`, `list_incidents` |
| **mcp-qms** | Python MCP server (HTTP/SSE + MI auth) | Integration adapter → QMS (SAP QM / TrackWise / Veeva Vault): `create_audit_entry` — GMP-compliant audit record у зовнішній системі |
| **mcp-cmms** | Python MCP server (HTTP/SSE + MI auth) | Integration adapter → CMMS (SAP PM / IBM Maximo): `create_work_order` — реальний наряд на роботи у зовнішній системі |
| **Incident DB** | Azure Cosmos DB Serverless | 8 containers; partition keys оптимізовані під incident-centric access |
| **RAG Index** | Azure AI Search | 5 indexes: SOPs, equipment manuals, GMP policies, BPR specs, incident history; HNSW vector + semantic ranker |
| **Document Ingestion** | Blob Storage + blob-trigger Functions | Chunk → embed → AI Search; table-aware chunking для BPR |
| **Real-time Push** | Azure SignalR Service | Hub `deviationHub`, role-based groups, push approval/status events |
| **Backend API** | Azure Functions HTTP | REST endpoints для SPA та decision resume |
| **Frontend** | React 18 + Vite + TypeScript | SPA на Azure Static Web Apps, MSAL, role-based views |
| **Identity** | Azure Entra ID | AuthN (MSAL), AuthZ (App Roles), Managed Identities, assignment_required |
| **Privileged Access** | Entra CA + Azure PIM | MFA + geo-restriction; JIT-eligible Contributor для IT Admin |
| **Secrets** | Azure Key Vault | Connection strings, API keys; 90-day rotation policy + Event Grid trigger |
| **Network** | VNet + Private Endpoints + NSGs | Ізоляція PaaS; `publicNetworkAccess = Disabled`; Private DNS Zones |
| **Security Monitoring** | Microsoft Defender for Cloud | Threat protection для App Service, Key Vault, Cosmos |
| **Observability** | App Insights + Log Analytics + Cosmos `incident_events` | Deep FOUNDRY_PROMPT_TRACE в App Insights; business timeline у Cosmos |
| **IaC** | Bicep | `infra/main.bicep` + модулі per ресурс |
| **CI/CD** | GitHub Actions | Build, test, Bicep deploy, Foundry eval gate, functions deploy |

---

## 6. Two-level orchestration

У цільовій архітектурі роль «Agent Orchestrator» **розбита на два рівні з різними відповідальностями** (див. [ADR-001](./docs/architecture-decisions.md#adr-001--human-in-the-loop-mechanism), [ADR-002](./docs/architecture-decisions.md#adr-002--foundry-connected-agents)).

```
┌──────────────────────────────────────────────────────────────────────┐
│  РІВЕНЬ 1 — Workflow Orchestrator (Azure Durable Functions)         │
│  Відповідає за: послідовність кроків, HITL пауза (до 24h),           │
│                 стан всього процесу, retry/DLQ, escalation           │
│                                                                      │
│  yield CallActivity("create_incident")                               │
│  yield CallActivity("enrich_context")                                │
│  yield CallActivity("run_foundry_agents")   ──► Рівень 2             │
│  yield CallActivity("notify_operator")                               │
│  ⏸ decision = WaitForExternalEvent("operator_decision") / Timer(24h)│
│  (more_info) → повтор run_foundry_agents з новим контекстом          │
│  (approved) → CallActivity("run_execution_agent")  ──► Рівень 2      │
│  yield CallActivity("finalize_audit")                                │
└───────────────────────────────────────┬──────────────────────────────┘
             ↓ activity calls           │
┌──────────────────────────────────────▼──────────────────────────────┐
│  РІВЕНЬ 2 — AI Orchestrator (Azure AI Foundry Agent Service)         │
│  Відповідає за: агентну логіку, tool calls, reasoning loop,          │
│                 routing між агентами через Connected Agents          │
│                                                                      │
│  run_foundry_agents:                                                 │
│    Orchestrator Agent                                                │
│      ├─ Research Agent (AgentTool)                                  │
│      │    ├─ AzureAISearchTool × 5 indexes                          │
│      │    └─ MCP: mcp-sentinel-db                                   │
│      └─ Document Agent (AgentTool)                                  │
│           └─ structured output + confidence gate 0.7                │
│                                                                      │
│  run_execution_agent:                                                │
│    Execution Agent                                                   │
│      ├─ MCP: mcp-cmms (create_work_order)                           │
│      └─ MCP: mcp-qms  (create_audit_entry)                          │
└──────────────────────────────────────────────────────────────────────┘
```

| Питання | Durable Functions | Foundry Agent Service |
|---|---|---|
| Керує | workflow-кроками процесу | AI reasoning та tool calls |
| HITL пауза | `waitForExternalEvent` — 24h+ | function_call timeout — 10 хв (недостатньо) |
| Стан між кроками | persisted у Azure Storage | persisted у thread в межах run |
| Retry / DLQ | вбудовано | ручний wrapper |
| Agent routing | не розуміє LLM | Connected Agents нативно |
| `max_iterations` | кастомний лічильник | нативно |
| MCP + RAG tools | кастомний код | `AzureAISearchTool`, MCP connections нативно |

---

## 7. Agent design

### 7.1 Orchestrator Agent

- **Тип:** Foundry prompt agent із підключеними sub-agents як tools.
- **Мета:** координувати Research та Document агентів через Connected Agents pattern.
- **Input:** incident payload + enriched context (equipment + batch + operator questions, якщо `more_info`).
- **Керує:** reasoning loop, `max_iterations`, послідовністю Research → Document.
- **Output:** `DocumentAgentOutput` JSON для Durable.

### 7.2 Research Agent

- **Тип:** Foundry agent, sub-agent via `AgentTool`.
- **Мета:** зібрати весь релевантний контекст для incident.
- **RAG tools** (Foundry `AzureAISearchTool`): `search_sop_documents`, `search_equipment_manuals`, `search_gmp_policies`, `search_bpr_documents`, `search_incident_history`.
- **MCP tools** (mcp-sentinel-db): `get_equipment(id)`, `get_batch(id)`, `search_incidents(equipment_id, date_range)`, `get_incident(id)`, `list_incidents(filters)`.
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

### 7.3 Document Agent

- **Тип:** Foundry agent, sub-agent via `AgentTool`.
- **Мета:** скласти decision package з evidence та confidence.
- **Input:** `ResearchAgentOutput` + incident details + templates з Cosmos `templates`.
- **Output schema** (`DocumentAgentOutput`):

> `risk_level` (severity): `HIGH` / `MEDIUM` / `LOW` / `LOW_CONFIDENCE` / `BLOCKED`.
> `agent_recommendation` (verdict): явна рекомендація агента — `APPROVE` (дія потрібна) або `REJECT` (ложно-позитивний або не потребує дій). GMP вимагає задокументувати рішення незалежно від результату.

```json
{
  "recommendation": "Stop granulator, inspect impeller bearing",
  "risk_level": "HIGH",
  "confidence": 0.84,
  "agent_recommendation": "APPROVE",
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

#### 7.3.1 Confidence gate

| Стан | Умова | Поведінка UI | Audit trail |
|---|---|---|---|
| **NORMAL** | confidence ≥ 0.7 | Recommendation + `agent_recommendation` (APPROVE/REJECT) + editable WO / audit drafts. Кнопки: [Approve] [Reject] [More info] | `confidence_score`, `operator_agrees_with_agent` |
| **LOW_CONFIDENCE** | confidence < 0.7 | Банер: «AI впевненість недостатня». Recommendation і drafts показуються, editable. Коментар обов'язковий. Кнопки: [Approve] [Reject] [More info] | `human_override = true`, mandatory comment |
| **BLOCKED** | agent failure / exception | Банер: «AI не зміг згенерувати рекомендацію». Порожні форми WO draft + audit entry draft — operator заповнює вручну (обов'язково для Approve). Кнопки: [Approve] [Reject] | `confidence = 0`, `human_override = true`, mandatory free-text |

> **Ескалація до QA Manager** відбувається **виключно** по таймауту `HITL_TIMEOUT_HOURS`. Низький confidence або BLOCKED стан **не** тригерять ескалацію — operator завжди може прийняти рішення самостійно.

#### 7.3.2 Evidence verification pass

Reasoning і verification — два різні кроки. Agent пропонує citations, але фінальний decision package проходить окрему server-side перевірку перед записом у Cosmos та показом у UI.

| Що перевіряємо | Хто виконує | Навіщо |
|---|---|---|
| Наявність документа | Backend normalization layer | Рекомендація не може посилатись на неіснуючий SOP / GMP doc |
| Відповідність `document_id` / title / link | Backend verification, незалежно від агента | Щоб generic labels (`sop`, `gmp`) не потрапляли в decision package |
| Section claim (`§4.2`, `§6.3`) | Authoritative chunk match у Azure AI Search | Щоб модель не видавала paragraph hallucination як verified evidence |
| Excerpt anchor | Authoritative chunk text | Зберігати тільки цитати, які реально можна простежити до retrieved evidence |

**Поведінка:** якщо документ знайдено і section підтверджено → citation `verified`. Якщо документ знайдено, але section не підтверджено → citation лишається видимою як `unresolved`, не піднімається у top-level `regulatory_reference`. Якщо документ/link не підтверджено → citation не рахується як verified evidence.

### 7.4 Execution Agent

- **Тип:** Foundry agent з MCP tools.
- **Trigger:** тільки після `operator_decision == "approved"`. При `rejected` цей агент **не запускається**.
- **Input payload:** формується з оператором верифікованих `work_order_draft` та `audit_entry_draft` (editable forms у UI; pre-filled від Document Agent; operator/QA може редагувати; інші ролі read-only). При BLOCKED-стані — поля порожні, operator заповнює вручну.
- **MCP tools та зовнішні системи:**
  - `create_work_order(payload)` → **mcp-cmms** → **CMMS** (SAP PM / IBM Maximo): фізично створює наряд на роботи в системі планування ТО. Повертає `work_order_id`.
  - `create_audit_entry(payload)` → **mcp-qms** → **QMS** (SAP QM / TrackWise / Veeva Vault): реєструє GMP deviation record із усіма полями для регуляторного аудиту. Повертає `audit_entry_id`.
- **Ідентифікатори**, повернуті зовнішніми системами, зберігаються у Cosmos `approval-tasks` та `incident_events` для трасабельності.
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

## 8. Human-in-the-loop

```
                          Durable Orchestrator
                                  │
                    Activity: notify_operator
                                  │
              Azure SignalR ──► React UI push
                                  │
                   Operator бачить:
                   ┌──────────────────────────────┐
                   │ ⚠ DEVIATION: GR-204           │
                   │ Impeller Speed: 580 RPM       │
                   │ (limit: 600–800 RPM | 4 min)  │
                   │                               │
                   │ AI Risk: MEDIUM (84%)         │
                   │ Root cause: motor load...     │
                   │ CAPA: 1. Moisture check...    │
                   │ Evidence: SOP-DEV-001 §4.2    │
                   │                               │
                   │ AI: APPROVE / REJECT          │
                   │ WO draft:    [editable ─────] │
                   │ Audit draft: [editable ─────] │
                   │                               │
                   │ [Approve] [Reject] [More info]│
                   └──────────────────────────────┘
                                  │
                                  │ confidence < 0.7: LOW_CONFIDENCE банер,
                                  │   comment обов'язковий
                                  │ BLOCKED (agent fail): порожні форми,
                                  │   operator заповнює вручну
                                  │
          ┌───────────────┬────────┴───────┬──────────────────────────────┐
          ↓               ↓               ↓                              ↓
       Approved        Rejected        More info        Timeout HITL_TIMEOUT_HOURS
          │               │               │             (default 24h;
          │               │               │              ≤1h для безперерв. вир-ва)
          │               │               │                              │
      run_exec         close +        append ctx                  escalate
       agent          outcome=         → re-run                  to QA Mgr
     (WO+audit       "rejected"          agents             Operator: read-only
    from edited   feedback async                            QA Manager: full UI
      drafts)    → alerting sys.
          │               │               │                              │
          └───────────────┴───────────────┴──────────────────────────────┘
                                  ↓
                           finalize_audit:
                           outcome, confidence_score,
                           human_override, human_override_text,
                           operator_agrees_with_agent,
                           work_order_id (if executed),
                           audit_entry_id (if executed)
```

---

## 9. Data persistence

### 9.1 Cosmos DB — схема контейнерів

**Database:** `sentinel-intelligence` · Serverless · 8 containers.

| Контейнер | Partition Key | Призначення |
|---|---|---|
| `incidents` | `/equipmentId` | Основний incident + AI analysis + workflow state |
| `incident_events` | `/incidentId` | Business audit trail, operator transcript, coarse agent lifecycle events |
| `notifications` | `/incidentId` | SignalR-facing notification records + delivery state |
| `equipment` | `/id` | CMMS master data: validated params, PM history |
| `batches` | `/equipmentId` | MES data: поточні та завершені batch records |
| `capa-plans` | `/incidentId` | Draft CAPA плани від Document Agent |
| `approval-tasks` | `/incidentId` | HITL approval tasks + execution results |
| `templates` | `/id` | IT Admin editable work order / audit entry templates |

> **Cross-partition query:** `incidents` партиціоновано по `/equipmentId`. Запити `GET /api/incidents` (список усіх) та фільтри по `status`/`date`/`severity` — cross-partition. Materialized view через Change Feed → secondary index по `status + createdAt` обслуговує dashboard-потоки.

### 9.2 Access matrix

| Контейнер | Сервіс / Агент | Операція | Інструмент |
|---|---|---|---|
| `incidents` | Azure Functions | Create, Read, Update | `azure-cosmos` SDK |
| `incidents` | Research Agent | Read (semantic search) | MCP: `search_incidents(equipment_id, date_range)` |
| `incident_events` | Azure Functions | Write decision, transcript, audit, lifecycle events | `azure-cosmos` SDK |
| `incident_events` | Backend API | Read timeline | `GET /api/incidents/{id}/events` |
| `notifications` | Azure Functions | Write pending + delivered | `azure-cosmos` SDK |
| `notifications` | Backend API | Read unread center | `GET /api/notifications`, `GET /api/notifications/summary` |
| `equipment` | Azure Functions | Read | `azure-cosmos` SDK |
| `equipment` | Research Agent | Read by ID | MCP: `get_equipment(id)` |
| `batches` | Azure Functions | Read | `azure-cosmos` SDK |
| `batches` | Research Agent | Read by ID | MCP: `get_batch(id)` |
| `capa-plans` | Document Agent | Write (draft CAPA) | `azure-cosmos` SDK |
| `capa-plans` | Execution Agent | Read (before execution) | MCP: read CAPA plan |
| `approval-tasks` | Azure Functions | Write (create), Read (poll) | `azure-cosmos` SDK |
| `approval-tasks` | Execution Agent | Write (audit entry result) | MCP: `create_audit_entry` |
| `templates` | Azure Functions | Read, Update | `GET/PUT /api/templates/{id}` |

---

## 10. RAG vs Direct data access

| Дані | Спосіб | Чому |
|---|---|---|
| Equipment validated parameters (PAR) | MCP (Cosmos) | Структуровані — точне значення важливіше за semantic match; equipment-level validated range |
| Current batch context | MCP (Cosmos) | Structured, current state |
| **BPR product specs (NOR)** | **RAG (`idx-bpr-documents`)** | Semantic search — product-specific CPP ranges narrower than equipment PAR |
| Historical incidents (semantic) | RAG (`idx-incident-history`) | Semantic similarity — «find similar cases» |
| SOPs / procedures | RAG (`idx-sop-documents`) | Semantic search по тексту процедур |
| Equipment manuals | RAG (`idx-equipment-manuals`) | Semantic search по технічній документації |
| GMP policies / regulations | RAG (`idx-gmp-policies`) | Semantic search по regulatory тексту |
| Work order status | MCP (CMMS) | Structured, external system |
| Audit entry IDs | MCP (QMS) | Structured, external system |

---

## 11. Backend API surface

| Метод + шлях | Trigger | Роль |
|---|---|---|
| `POST /api/alerts` | HTTP | Ingest alert → Service Bus (idempotent через `sourceAlertId`) |
| `GET /api/incidents` | HTTP | Список incident-ів (filter by status / severity / date) |
| `GET /api/incidents/{id}` | HTTP | Деталі incident + latest AI analysis |
| `GET /api/incidents/{id}/events` | HTTP | Chronological timeline для UI |
| `GET /api/incidents/{id}/agent-telemetry` | HTTP | IT Admin / auditor — структурований agent trace з App Insights |
| `POST /api/incidents/{id}/decision` | HTTP | Приймає operator decision → `raise_event` на Durable |
| `GET /api/notifications` | HTTP | Unread notifications для operator UX |
| `GET /api/notifications/summary` | HTTP | Counters для header-у |
| `GET /api/equipment/{id}` | HTTP | Read equipment master data |
| `GET /api/batches/current/{equipment_id}` | HTTP | Read поточний batch для обладнання |
| `GET/PUT /api/templates/{id}` | HTTP | IT Admin template management |
| `POST /api/negotiate` | HTTP | SignalR negotiate endpoint (bearer token → role-based groups) |

AuthN: Bearer token від Entra ID. AuthZ: App Roles перевіряються у кожному HTTP trigger.

---

## 12. Azure Functions map

### 12.1 Потік від Service Bus до паузи

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
│                                                                     │
│  yield CallActivity("create_incident")                              │
│  yield CallActivity("enrich_context")                               │
│  yield CallActivity("run_foundry_agents")   ──► Foundry             │
│  yield CallActivity("notify_operator")      ──► SignalR + Cosmos    │
│                                                                     │
│  ⏸  decision = yield WaitForExternalEvent("operator_decision")     │
│     (serialized у Azure Storage; RAM звільняється)                  │
│                                                                     │
│  # more_info loop (max rounds через MAX_MORE_INFO_ROUNDS)          │
│  while decision.action == "more_info" and rounds < MAX_ROUNDS:     │
│      context.operator_questions.append(decision.question)          │
│      yield CallActivity("run_foundry_agents", context)             │
│      yield CallActivity("notify_operator")                          │
│      decision = yield WaitForExternalEvent("operator_decision")    │
│      rounds += 1                                                   │
│                                                                     │
│  if decision.action == "approved":                                 │
│      yield CallActivity("run_execution_agent")                     │
│  elif decision.action == "rejected":                               │
│      yield CallActivity("close_incident")                          │
│                                                                     │
│  yield CallActivity("finalize_audit")                              │
└─────────────────────────────────────────────────────────────────────┘
```

### 12.2 Як оркестратор прокидається

```
React UI: operator натискає [Approve] / [Reject] / [More info]
      │
      │  POST /api/incidents/{id}/decision
      │  { "decision": "approved", "comment": "LIMS verified" }
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│  decision_handler  (HTTP Trigger)                                   │
│                                                                     │
│  1. Validates request (Entra ID bearer)                             │
│  2. Читає instance_id з approval-tasks (by incident_id)             │
│  3. await client.raise_event(                                       │
│         instance_id, "operator_decision",                           │
│         { "decision": ..., "comment": ... })                        │
│  4. HTTP 200                                                        │
│                                                                     │
│  → Durable знаходить instance у Azure Storage                       │
│  → replay orchestrator від початку                                  │
│  → доходить до WaitForExternalEvent → event вже є → продовжує       │
└─────────────────────────────────────────────────────────────────────┘
```

### 12.3 Повна карта функцій

| Функція | Тип тригера | Файл | Роль |
|---|---|---|---|
| `ingest_alert` | HTTP | `function_app.py` | REST `POST /api/alerts` → Service Bus (idempotent) |
| `alert_processor` | Service Bus | `function_app.py` | Вхідна точка workflow: алерт → старт оркестратора |
| `deviation_orchestrator` | Durable Orchestrator | `function_app.py` | Координує весь workflow |
| `create_incident` | Durable Activity | `function_app.py` | Cosmos write: новий incident |
| `enrich_context` | Durable Activity | `function_app.py` | Cosmos read: equipment + batch |
| `run_foundry_agents` | Durable Activity | `function_app.py` | Foundry: Orchestrator Agent → CAPA draft → App Insights trace |
| `notify_operator` | Durable Activity | `function_app.py` | Cosmos write + SignalR push |
| `run_execution_agent` | Durable Activity | `function_app.py` | Foundry: Execution Agent → QMS/CMMS |
| `close_incident` | Durable Activity | `function_app.py` | Cosmos update: status=rejected |
| `finalize_audit` | Durable Activity | `function_app.py` | Cosmos write: audit record + trigger history sync |
| `decision_handler` | HTTP | `function_app.py` | `POST /api/incidents/{id}/decision` → `raise_event` |
| `get_incidents` | HTTP | `function_app.py` | `GET /api/incidents` |
| `get_incident_by_id` | HTTP | `function_app.py` | `GET /api/incidents/{id}` |
| `get_incident_events` | HTTP | `function_app.py` | `GET /api/incidents/{id}/events` |
| `get_agent_telemetry` | HTTP | `function_app.py` | `GET /api/incidents/{id}/agent-telemetry` (App Insights query) |
| `get_notifications` | HTTP | `function_app.py` | `GET /api/notifications`, `/summary` |
| `get_templates` / `put_template` | HTTP | `function_app.py` | IT Admin template CRUD |
| `negotiate` | HTTP | `function_app.py` | SignalR negotiate (role → groups) |
| `blob_ingest_{sop,manuals,gmp,bpr}` | Blob trigger | `function_app.py` | Document ingestion → chunk → embed → AI Search |

**Idempotency.** `POST /api/alerts` приймає `alert_id` у payload; `ingest_alert` перевіряє існуючий incident з `sourceAlertId == alert_id` перед публікацією у Service Bus. Дублі повертають `HTTP 200` з existing `incident_id`.

**Foundry.** Не Azure Function — зовнішній сервіс, який `run_*_agent` activities викликають через `azure-ai-projects` SDK.

---

## 13. Real-time layer — SignalR

Hub: `deviationHub` · Negotiate: `POST /api/negotiate` (Bearer → role-based groups).

| Group | Events |
|---|---|
| `role:operator` | `incident_pending_approval`, `incident_updated` |
| `role:qa-manager` | `incident_escalated`, `incident_pending_approval` |
| `incident:{id}` | `incident_status_changed`, `agent_step_completed` |

> Повний контракт (events, payloads, negotiation flow): [docs/signalr-contract.md](./docs/signalr-contract.md).

---

## 14. Document ingestion

5 Blob containers → 5 Azure Function blob triggers → 5 Azure AI Search indexes (один на тип джерела). BPR-інгестор використовує table-aware chunking для GMP compliance.

| Container | Index | Notes |
|---|---|---|
| `blob-sop` | `idx-sop-documents` | 500 tokens, 50 overlap |
| `blob-manuals` | `idx-equipment-manuals` | + `equipment_id` tag |
| `blob-gmp` | `idx-gmp-policies` | + clause metadata |
| `blob-bpr` | `idx-bpr-documents` | Table-aware, max ~1200 tokens |
| `blob-history` | `idx-incident-history` | Generated from Cosmos on `finalize_audit` |

> Повна специфікація (rationale, agent → index mapping, Bicep): [docs/document-ingestion.md](./docs/document-ingestion.md).

---

## 15. Agent observability

Структурований agent trace для incident-level troubleshooting, emit-иться з `run_foundry_agents`.

### 15.1 Що спостерігаємо

- outer prompt, відправлений до Foundry Orchestrator Agent;
- system prompts Orchestrator / Research / Document;
- final thread messages від Foundry;
- raw top-level response;
- parsed JSON package;
- normalized final result, що persist-иться у Cosmos та показується в UI.

> Обмеження SDK: поточний `azure-ai-agents` SDK не експозить connected sub-agent run steps напряму → внутрішні Research/Document invocation payloads видимі частково. Цільова архітектура передбачає перехід на SDK-версію з deep-step visibility щойно вона стабілізується.

### 15.2 Trace контракт

Marker: `FOUNDRY_PROMPT_TRACE`. Поля: `incident_id`, `round`, `trace_kind`, `chunk_index`, `chunk_count`, `thread_id`, `run_id`.

Trace kinds: `prompt_context`, `orchestrator_user_prompt`, `thread_messages`, `raw_response`, `parsed_response`, `normalized_result`.

### 15.3 Розділення сховищ

- **Cosmos `incident_events`** — business-facing timeline (`analysis_started`, `agent_response`, `more_info`, approval / rejection / escalation). Оптимізовано під incident-centric UI reads.
- **App Insights / Log Analytics** — deep Foundry trace за `FOUNDRY_PROMPT_TRACE`. Оптимізовано під troubleshooting, prompt inspection, post-mortem.

### 15.4 Admin delivery path

`GET /api/incidents/{id}/agent-telemetry`:

1. Query App Insights / Log Analytics за `FOUNDRY_PROMPT_TRACE` rows по `incident_id`.
2. Normalize trace records у frontend-friendly DTO (summary cards + chronological items).
3. Merge in `incident_events` рядки, щоб admin бачив business + deep trace на одній сторінці.

Опціональна оптимізація — persist compact admin-relevant projection у `incident_events` з `type = "agent_telemetry"` для швидкого UI rendering.

---

## 16. Security architecture

### 16.1 Identity & access

- **Azure Entra ID** — AuthN для SPA через MSAL; AuthZ через App Roles на App Registration.
- **`assignment_required = true`** — тільки призначені users/groups можуть логінитись.
- **Managed Identity (System-assigned)** на Function App — ролі на Cosmos, Service Bus, AI Search, Key Vault, Azure OpenAI, SignalR, Storage. Жодних connection strings у коді.
- **Conditional Access** (Entra P2): MFA для всіх users, блокування non-EU countries (GMP pharma compliance), require compliant device для IT Admin.
- **Azure PIM** (Entra P2): JIT-eligible Contributor для IT Admin (1–4h активація з justification), eligible Reviewer для QA Manager. Постійно active: `operator`, `maint-tech`, `auditor` (read-only).
- **Entra Security Groups:** `sg-sentinel-operators`, `sg-sentinel-qa-managers`, `sg-sentinel-auditors`, `sg-sentinel-it-admin`. Lifecycle Workflows: auto MFA setup on onboarding, auto group removal on offboarding.

### 16.2 Network isolation

```
VNet: 10.0.0.0/16
  snet-functions (10.0.1.0/24) — VNet Integration для Function App (Flex Consumption)
    NSG: allow outbound → snet-private-endpoints, deny internet
  snet-private-endpoints (10.0.2.0/24) — Private Endpoints для всіх PaaS
    NSG: deny all inbound except VNet
    PE: Cosmos DB · AI Search · Service Bus · Storage · Key Vault · Azure OpenAI · SignalR
    Private DNS Zones: auto-resolution per service

PaaS: publicNetworkAccess = Disabled після PE активації
```

### 16.3 Secrets

- **Key Vault** тримає всі secrets та API keys. Functions читають через `DefaultAzureCredential` + Managed Identity.
- **Rotation policy:** 90 днів на всіх secrets + Event Grid trigger на ротацію → notification у IT Admin.
- **No shared accounts, no keys у repo, no keys у App Settings.**

### 16.4 Threat protection

- **Microsoft Defender for Cloud** — plans для App Service + Key Vault + Cosmos DB + Storage.
- **Block legacy auth** через CA: deny Basic / NTLM / legacy OAuth.
- **TLS 1.2+** enforced на всіх endpoint-ах; HSTS на SWA.
- **Input validation** на всіх HTTP triggers; ORM parametrization; no dynamic SQL.

### 16.5 Resource governance

- **Теги** на кожному Bicep module: `environment`, `team`, `cost-center`, `data-classification`, `owner`.
- **Azure Policy** enforcement: `publicNetworkAccess = Disabled`, allowed regions, enforced tags.

---

## 17. Reliability architecture

### 17.1 Ingestion + workflow

- **Service Bus** `alert-queue`: DLQ після 3 auto-retries, at-least-once delivery, idempotency через `sourceAlertId`.
- **Durable Functions** `RetryPolicy(max_number_of_attempts=3, first_retry_interval=5s)` з exponential backoff на всіх activities.
- **Cosmos DB Serverless** — autoscale без manual provisioning; change-feed для materialized view на `status + createdAt`.
- **`MAX_MORE_INFO_ROUNDS = 3`** — захист від нескінченного `more_info` циклу.
- **24h HITL timeout** → Durable `create_timer` + race-pattern escalate до QA Manager.

### 17.5 Orchestrator Watchdog — автовиявлення та відновлення

Azure Durable Functions зберігають стан у Azure Storage Tables. Якщо Function App перезапускається під час деплою або оркестратор впав — Cosmos DB залишається у статусі `pending_approval`, але Durable instance зникає (NOT_FOUND). Operator не може подати рішення.

**Рішення — `orchestrator_watchdog` Timer Trigger (кожні 5 хвилин):**

```
┌───────────────────────────────────────────────────────┐
│  Timer Trigger  ─►  Cosmos query (stuck statuses)     │
│  every 5 min        open / queued / analyzing /       │
│                     analyzing_agents → > 15 min old   │
│                     pending_approval → > 2 min old    │
│                                                        │
│  For each candidate:                                   │
│    client.get_status("durable-{incident_id}")          │
│    ├─ Running / Pending → SKIP (healthy)               │
│    └─ NOT_FOUND / Failed / null → REQUEUE              │
│         └─ publish_alert(payload) → Service Bus        │
│              └─ fresh orchestrator starts              │
└───────────────────────────────────────────────────────┘
```

**Ключові властивості:**
- **Два типи виявлення:**
  - *Stuck analysis* — `open/queued/analyzing/analyzing_agents` старше порогу (15 хв за замовчуванням)
  - *Orphaned approval* — `pending_approval` + Durable NOT_FOUND (grace period 2 хв)
- **Idempotent recovery** — лише republish до Service Bus; orchestrator сам переставить статус у Cosmos при старті
- **Safety cap** — не більше 10 відновлень за один запуск

### 17.2 Fallback & circuit breaker

- **Fallback mode:** якщо Foundry Agent недоступний або валидація citations fail → operator отримує pre-filled manual CAPA template замість AI-рекомендацій + explicit `degraded_mode=true` у UI.
- **Circuit breaker:** 3 послідовні Foundry failures → circuit open → fallback; auto-reset через 60s з half-open probe.

### 17.3 SLOs + alerts

| Метрика | SLO | Alert |
|---|---|---|
| P95 `POST /api/alerts` latency | < 2s | > 2s × 5 хв |
| P95 `GET /incidents` latency | < 500ms | > 500ms × 5 хв |
| E2E agent pipeline latency (alert → approval-ready) | < 120s | > 180s × 3 events |
| DLQ depth | 0 | > 0 |
| Foundry failure rate | < 1% | > 5% × 10 хв |
| Cosmos RU throttling | 0 | > 0 |

Alerts — Azure Monitor action group → email + Teams webhook.

### 17.4 Chaos & DR

- **Azure Chaos Studio** scenarios: Foundry timeout, Service Bus outage, Cosmos throttling, Key Vault unavailability. Прогоняються у staging щомісяця.
- **Multi-region DR:** Cosmos DB geo-redundancy (primary Sweden Central, secondary North Europe); AI Search replica у secondary region; Service Bus geo-recovery pair.
- **Recovery runbook** у [docs/operations-runbook.md](./docs/operations-runbook.md): як відновити incident-и, які застрягли після max retries; як replay DLQ; як перемикнути на DR region.

---

## 18. Operational Excellence & Performance

### 18.1 Observability stack

- **Application Insights** — traces (включно з `FOUNDRY_PROMPT_TRACE`), exceptions, dependencies, metrics.
- **Log Analytics** workspace — 30 днів retention (hot) + archive у Storage для audit (2 роки).
- **Cosmos `incident_events`** — business timeline для inspection-ready звітів.
- **Custom workbooks:** agent performance, hallucination rate, confidence distribution, HITL latency, DLQ health.

### 18.2 Cost management

- **Azure Budgets** (`Microsoft.Consumption/budgets`) per environment з alert-ами на 50/80/100%.
- **Cosmos Serverless** + **AI Search Free/Basic scaled to Standard** — pay-per-use, no idle cost.
- **Function App Flex Consumption** — автоскейл + VNet Integration.
- **Теги** `cost-center` дозволяють cost allocation per product line.

### 18.3 Performance & load testing

Очікуваний production load:

- **Alert ingestion spike:** 50–200 concurrent alerts при batch-close зміни;
- **SignalR:** 50–200 operator sessions одночасно;
- **Foundry agent:** 5–10 concurrent orchestrations (30–120s кожна);
- **API:** P95 < 500ms (read), P95 < 2s (`POST /alerts`).

**Azure Load Testing** сценарії (Locust/JMeter):

1. `scenario-alert-spike` — POST `/api/alerts` × 200 RPS × 5 хв;
2. `scenario-signalr-concurrent` — 200 SignalR clients, join/leave incident groups;
3. `scenario-agent-pipeline` — 10 concurrent orchestrations end-to-end;
4. `scenario-api-read` — GET `/incidents` × 500 RPS.

Запускаються у staging перед кожним prod release через GitHub Actions `load-test.yml` workflow.

### 18.4 Deployment governance

- **Bicep IaC** — `infra/main.bicep` + модулі per ресурс. What-if analysis у PR check.
- **GitHub Actions:**
  - `ci.yml` — build, lint, unit tests, Bicep lint + what-if;
  - `deploy.yml` — bicep deploy + functions deploy + Foundry eval gate + smoke test;
  - `load-test.yml` — staging performance gate.
- **Foundry eval gate** — перед promotion нової версії агента: groundedness / coherence / relevance / F1 vs baseline у Azure AI Foundry Evaluation.

---

## 19. Responsible AI

### 19.1 Guardrails на runtime

- **Confidence gate 0.7** (див. [§7.3.1](#731-confidence-gate)).
- **Evidence-grounded output** + backend verification pass (див. [§7.3.2](#732-evidence-verification-pass)).
- **Azure Content Safety + Prompt Shield** — input screening (SCADA payloads, operator messages) + output screening (agent responses) перед persist або показом у UI.
- **Mandatory human approval** — жодне execution не відбувається без operator decision (GxP).
- **Separate reasoning vs verification** — модель пропонує, backend верифікує citations.

### 19.2 Governance lifecycle

- **Model versioning:** кожна нова версія агента має semantic version (`orchestrator-v1.3.2`); deployment через Bicep.
- **Eval pipeline gate:** nightly runs Groundedness / Coherence / Relevance / F1 через Azure AI Foundry Evaluation; promotion можлива тільки якщо metrics ≥ baseline thresholds.
- **Rollback:** один команд `make agent-rollback VERSION=...` — повертає попередній `assistant_id` у Functions config.
- **Red-team testing protocol** — формальна сесія перед кожним major release для GMP-критичних рекомендацій.

### 19.3 Transparency & auditability

- Evidence citations з `document_id`, section, excerpt, relevance score у decision package.
- `human_override`, `operator_comment`, `confidence_score` у audit record.
- Hallucination rate dashboard у App Insights workbook (тренд per agent per тиждень).
- `GET /api/incidents/{id}/agent-telemetry` — повний prompt/response trace для IT Admin та auditor.

---

## 20. Identity, roles & RBAC

### 20.1 App Roles (Entra ID App Registration)

| Роль | App Role value | Доступ |
|---|---|---|
| Production Operator | `operator` | Incident list + decision UI для призначених incident-ів |
| QA Manager | `qa-manager` | Всі incident-и + escalation queue + manager approvals |
| Maintenance Technician | `maint-tech` | Read-only work orders |
| Auditor | `auditor` | Read-only audit trail + agent telemetry |
| IT Admin | `it-admin` | Templates CRUD + agent telemetry + config management |

### 20.2 Enforcement

- На SPA: MSAL bearer, role claims перевіряються у route guards.
- На Backend API: декоратор `@require_role("...")` на кожному HTTP trigger.
- На Azure resources: Managed Identity Function App-у має лише мінімальні data-plane ролі (Cosmos `DocumentDB Data Contributor`, AI Search `Search Index Data Contributor` тощо); control-plane — тільки через IT Admin JIT.

> Деталі role mapping у Entra: [docs/entra-role-assignment.md](./docs/entra-role-assignment.md).

---

## 21. Technical stack

| Layer | Tech | Notes |
|---|---|---|
| Backend | Python 3.11 | Azure Functions v2 programming model, Durable Functions |
| Agents | Azure AI Foundry Agent Service | Python SDK `azure-ai-projects` + `azure-ai-agents` |
| MCP servers | Python `mcp` library | HTTP/SSE transport (Managed Identity auth) |
| Workflow | Azure Durable Functions | `azure-durable-functions` |
| Database | Azure Cosmos DB Serverless | `azure-cosmos` SDK |
| Queue | Azure Service Bus Standard | `azure-servicebus` SDK |
| SignalR | Azure SignalR Service | Serverless mode, REST negotiate |
| AI Search | Azure AI Search | `azure-search-documents` SDK, HNSW vector + semantic ranker |
| Frontend | React 18 + Vite + TypeScript | `@azure/msal-react` |
| Auth | Azure Entra ID (MSAL) | Managed Identities на всіх Functions |
| Secrets | Azure Key Vault | `azure-keyvault-secrets` + MI + rotation |
| Network | VNet + Private Endpoints + Private DNS | Flex Consumption plan |
| Monitoring | App Insights + Log Analytics + Defender for Cloud | Custom workbooks |
| IaC | Bicep | `infra/main.bicep` + модулі |
| CI/CD | GitHub Actions | `ci.yml`, `deploy.yml`, `load-test.yml` |

---


---

## Related documents

Архітектура свідомо містить тільки **цільовий (TO-BE) дизайн**. Супутні артефакти живуть у власних документах:

| Тема | Документ |
|---|---|
| Архітектурні рішення (ADR-001, ADR-002, ...) | [docs/architecture-decisions.md](./docs/architecture-decisions.md) |
| Історія версій + AS-SUBMITTED v1.0 схема + еволюція компонентів | [docs/architecture-history.md](./docs/architecture-history.md) |
| Скорочення прототипу та post-hackathon backlog (T-039, T-040, T-047–T-051) | [docs/hackathon-scope.md](./docs/hackathon-scope.md) |
| Інфраструктурна діаграма (Mermaid + Draw.io) | [infra/diagram.md](./infra/diagram.md), [infra/architecture.drawio](./infra/architecture.drawio) |
| Document ingestion pipeline | [docs/document-ingestion.md](./docs/document-ingestion.md) |
| SignalR контракт | [docs/signalr-contract.md](./docs/signalr-contract.md) |
| Operations runbook (DR, recovery, chaos) | [docs/operations-runbook.md](./docs/operations-runbook.md) |
| Entra ID role assignment | [docs/entra-role-assignment.md](./docs/entra-role-assignment.md) |
| Frontend design system | [docs/design-system.md](./docs/design-system.md), [docs/frontend-design.md](./docs/frontend-design.md) |
| Platform reference (ресурси, endpoints, Cosmos schema) | [docs/platform-reference.md](./docs/platform-reference.md) |

---

← [01 Вимоги](./01-requirements.md) · [03 Аналіз →](./03-analysis.md)
