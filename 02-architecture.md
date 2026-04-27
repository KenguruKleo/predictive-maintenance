# 02 · Architecture

← [README](./README.md) · [01 Requirements](./01-requirements.md) · [03 Analysis](./03-analysis.md) · [04 Action Plan](./04-action-plan.md)

> **Target:** Sentinel Intelligence target architecture - what the system should look like in production (TO-BE). Related documents (history, ADR, prototype abbreviations) are listed in the [Related documents](#related-documents) section at the end.

---

## Contents

1. [Overview](#1-overview)
2. [AS-IS vs TO-BE processes](#2-as-is-vs-to-be processes)
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

**Sentinel Intelligence** — AI-powered multi-agent Operations Assistant on Azure AI Foundry for GMP manufacturing.

System:

- detects anomaly/deviation events from SCADA/MES/IoT signals;
- enriches them with context (batch, equipment, validated parameters);
- performs agent reasoning through RAG on SOP / BPR / GMP / CAPA history and MCP-tool access to structured data;
- generates CAPA recommendations, work-order draft and audit-ready records;
- stops at mandatory human approval before any execution (GxP requirement);
- logs full agent + business trace for compliance and post-mortem analysis.

**Stakeholders:**

| Role | Participation |
|---|---|
| Production Operator | Receives alert, views decision package, approves / denies / requests more info |
| QA Manager | Handles escalated incidents, final approval for complex cases
| Maintenance Technician | Read-only access to work orders |
| Auditor Read-only access to audit trail + agent telemetry |
| IT Admin | Manage templates, view agent telemetry, JIT-eligible Contributor |

---

## 2. AS-IS vs TO-BE processes

**AS-IS (manual, 30–60 min, operator-dependent result):**

```
Sensor Signal → Alert
  → Operator RECEIVES (manual, interprets context manually)
  → CHECK SOP/BPR (manual search)
  → MAKES DECISION (based on experience, incomplete info)
  → REGISTER CAPA (manual work order creation in QMS/CMMS)
  → CREATE REPORT (manual documentation for audit trail)
```

**TO-BE (AI-assisted, < 5 min for decision, standardized result):**

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
│ │ 6c. more_info → re-run step 3 with additional context │ │
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
│              ELECTRON DESKTOP APP (MULTI-PLATFORM)                 │
│  Same React operator console packaged for shop-floor desktops       │
│  Native unread badge · native incident notifications · deep links   │
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

> Infrastructure diagram with resource types and Bicep modules: [infra/diagram.md](./infra/diagram.md) (Mermaid) and [infra/architecture.drawio](./infra/architecture.drawio).
>
---

## 4. End-to-end data flow

**Step 1 — Detect.** SCADA/MES/IoT system publishes alert → `POST /api/alerts` (HTTP Function `ingest_alert`) → alert is recorded in Service Bus `alert-queue`. Idempotency: `ingest_alert` checks `sourceAlertId` in Cosmos before publishing.

**Step 2 — Trigger workflow.** Service Bus trigger `alert_processor` receives messages, generates `incident_id`, starts Durable orchestrator `deviation_orchestrator` via `client.start_new(...)`.

**Step 3 — Create & enrich.** Orchestrator sequentially calls:

- `create_incident` — records the basic incident in Cosmos `incidents`;
- `enrich_context` — reads `equipment` + `batches` by ID from alert.

**Step 4 — Agent reasoning.** Activity `run_foundry_agents` starts the Foundry **Orchestrator Agent**. Orchestrator manages the Connected Agents pipeline:

- **Research Agent** (sub-agent via `AgentTool`) uses RAG (Azure AI Search × 5 indexes) + MCP tools (`mcp-sentinel-db`) in parallel and returns `ResearchAgentOutput`;
- **Document Agent** (sub-agent via `AgentTool`) accepts `ResearchAgentOutput`, applies confidence gate 0.7, returns `DocumentAgentOutput` with recommendation, evidence citations, CAPA steps, work_order_draft, audit_entry_draft.

Foundry natively manages the reasoning loop and `max_iterations`. The backend performs a separate **verification pass** on citations before persisting.

**Step 5 — Notify operator.** Activity `notify_operator` writes entries in `approval-tasks`, `notifications`, `incident_events` and publishes event in Azure SignalR `deviationHub` → React UI and the Electron desktop shell. In web mode the operator sees the in-app notification center; in desktop mode the same unread count also drives the native badge and SignalR events can surface as native OS notifications.

**Step 6 — Human decision.** Operator looks at decision package: AI recommendation (`agent_recommendation: APPROVE | REJECT`), rationale, evidence, **edited forms** WO draft and audit entry draft (pre-filled by Document Agent; mandatory for Approve). Pushes `Approve` / `Reject` / `More info`. `POST /api/incidents/{id}/decision` calls Durable `raise_event("operator_decision", ...)` → orchestrator wakes up.

- `more_info` → orchestrator adds `operator_question` to the context, repeats `run_foundry_agents` (until `MAX_MORE_INFO_ROUNDS`);
- `approved` → `run_execution_agent`; payload for WO + audit entry is taken with operator edited forms; `operator_agrees_with_agent = (decision == agent_recommendation)`;
- `rejected` → `close_incident`; audit record stores `outcome = "rejected"` and `operator_agrees_with_agent`; async feedback event is sent to the alerting system (`ALERT_FEEDBACK_URL`, configurable) — allows SCADA/MES to learn from false positive signals;
- Timeout `HITL_TIMEOUT_HOURS` (default: 24h; **recommended ≤ 1h for continuous production**) → Durable escalate to QA Manager; operator switches to **read-only**; QA Manager gets full decision UI.

**Step 7 — Execute.** Activity `run_execution_agent` starts the Foundry Execution Agent, which through MCP servers performs real integrations: `create_work_order` (mcp-cmms → CMMS: SAP PM / IBM Maximo) and `create_audit_entry` (mcp-qms → QMS: SAP QM / TrackWise / Veeva Vault). Payload is formed with the operator of verified and edited forms (filled in manually in case of BLOCKED state).

**Step 8 — Finalize.** Activity `finalize_audit` writes the final audit record (`confidence_score`, `human_override`, `human_override_text`, `operator_comment`, `operator_agrees_with_agent`, timestamps, agent steps) to `incident_events` + updates `incidents` status. Blob trigger synchronizes closed incident in `idx-incident-history`.

---

## 5. Component catalog

| Component | Technology | Role |
|---|---|---|
| **Ingestion API** | Azure Functions HTTP (Python) | Receives external alerts, idempotency via `sourceAlertId`, publishes to Service Bus |
| **Alert Queue** | Azure Service Bus Standard | Decoupled ingestion, DLQ, 3 auto-retries, at-least-once delivery |
| **Workflow Orchestrator** | Azure Durable Functions (Python) | Stateful orchestration of the entire process, HITL pause, 24h timeout, retry/DLQ |
| **AI Orchestrator** | Azure AI Foundry Agent Service | Connected Agents routing, reasoning loop, native MCP + RAG tool connections |
| **Orchestrator Agent** | Foundry prompt agent | Coordinates Research → Document pipeline, manages reasoning loop and `max_iterations` |
| **Research Agent** | Foundry agent + 5 RAG tools + MCP | Collects equipment state, batch context, relevant SOPs, historical cases |
| **Document Agent** | Foundry agent + templates + confidence gate | Draft: recommendation, risk level, evidence citations, CAPA steps, WO/audit drafts |
| **Execution Agent** | Foundry agent + MCP-QMS/CMMS | After approval: `create_work_order` → CMMS + `create_audit_entry` → QMS |
| **mcp-sentinel-db** | Python stdio MCP server | Tools: `get_incident`, `get_equipment`, `get_batch`, `search_incidents`, `list_incidents` |
| **mcp-qms** | Python MCP server (HTTP/SSE + MI auth) | Integration adapter → QMS (SAP QM / TrackWise / Veeva Vault): `create_audit_entry` — GMP-compliant audit record in the external system |
| **mcp-cmms** | Python MCP server (HTTP/SSE + MI auth) | Integration adapter → CMMS (SAP PM / IBM Maximo): `create_work_order` — a real order to work in an external system |
| **Incident DB** | Azure Cosmos DB Serverless | 8 containers; partition keys are optimized for incident-centric access |
| **RAG Index** | Azure AI Search | 5 indexes: SOPs, equipment manuals, GMP policies, BPR specs, incident history; HNSW vector + semantic ranker |
| **Document Ingestion** | Blob Storage + blob-trigger Functions | Chunk → embed → AI Search; table-aware chunking for BPR |
| **Real-time Push** | Azure SignalR Service | Hub `deviationHub`, role-based groups, push approval/status events |
| **Backend API** | Azure Functions HTTP | REST endpoints for SPA and decision resume |
| **Frontend** | React 18 + Vite + TypeScript | SPA on Azure Static Web Apps, MSAL, role-based views |
| **Desktop App** | Electron + React/Vite preload bridge | Multi-platform desktop operator console reusing the SPA; native unread badge and incident notifications for shop-floor monitoring |
| **Identity** | Azure Entra ID | AuthN (MSAL), AuthZ (App Roles), Managed Identities, assignment_required |
| **Privileged Access** | Entra CA + Azure PIM | MFA + geo-restriction; JIT-eligible Contributor for IT Admin |
| **Secrets** | Azure Key Vault | Connection strings, API keys; 90-day rotation policy + Event Grid trigger |
| **Network** | VNet + Private Endpoints + NSGs | PaaS Isolation; `publicNetworkAccess = Disabled`; Private DNS Zones |
| **Security Monitoring** | Microsoft Defender for Cloud | Threat protection for App Service, Key Vault, Cosmos |
| **Observability** | App Insights + Log Analytics + Cosmos `incident_events` | Deep FOUNDRY_PROMPT_TRACE in App Insights; business timeline in Cosmos |
| **IaC** | Bicep | `infra/main.bicep` + modules per resource |
| **CI/CD** | GitHub Actions | Build, test, Bicep deploy, Foundry eval gate, functions deploy |

---

## 6. Two-level orchestration

In the target architecture, the Agent Orchestrator role is **split into two levels with different responsibilities** (see [ADR-001](./docs/architecture-decisions.md#adr-001--human-in-the-loop-mechanism), [ADR-002](./docs/architecture-decisions.md#adr-002--foundry-connected-agents)).

```
┌──────────────────────────────────────────────────────────────────────┐
│ LEVEL 1 — Workflow Orchestrator (Azure Durable Functions) │
│ Responsible for: sequence of steps, HITL pause (up to 24h), │
│ state of the entire process, retry/DLQ, escalation │
│                                                                      │
│  yield CallActivity("create_incident")                               │
│  yield CallActivity("enrich_context")                                │
│ yield CallActivity("run_foundry_agents") ──► Level 2 │
│  yield CallActivity("notify_operator")                               │
│  ⏸ decision = WaitForExternalEvent("operator_decision") / Timer(24h)│
│ (more_info) → repeat run_foundry_agents with new context │
│ (approved) → CallActivity("run_execution_agent") ──► Level 2 │
│  yield CallActivity("finalize_audit")                                │
└───────────────────────────────────────┬──────────────────────────────┘
             ↓ activity calls           │
┌──────────────────────────────────────▼──────────────────────────────┐
│ LEVEL 2 — AI Orchestrator (Azure AI Foundry Agent Service) │
│ Responsible for: agent logic, tool calls, reasoning loop, │
│ routing between agents via Connected Agents │
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

| Question | Durable Functions | Foundry Agent Service |
|---|---|---|
| Manages | workflow-steps of the process | AI reasoning and tool calls |
| HITL pause | `waitForExternalEvent` — 24h+ | function_call timeout — 10 min (not enough) |
| State between steps | persisted in Azure Storage | persisted in the thread within run |
| Retry / DLQ | built in | manual wrapper |
| Agent routing | does not understand LLM | Connected Agents natively |
| `max_iterations` | custom counter | natively |
| MCP + RAG tools | custom code | `AzureAISearchTool`, MCP connections natively |

---

## 7. Agent design

### 7.1 Orchestrator Agent

- **Type:** Foundry prompt agent with connected sub-agents as tools.
- **Goal:** to coordinate Research and Document agents through the Connected Agents pattern.
- **Input:** incident payload + enriched context (equipment + batch + operator questions, if `more_info`).
- **Controls:** reasoning loop, `max_iterations`, sequence Research → Document.
- **Output:** `DocumentAgentOutput` JSON for Durable.

### 7.2 Research Agent

- **Type:** Foundry agent, sub-agent via `AgentTool`.
- **Goal:** to collect all relevant context for the incident.
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

- **Type:** Foundry agent, sub-agent via `AgentTool`.
- **Goal:** to make a decision package with evidence and confidence.
- **Input:** `ResearchAgentOutput` + incident details + templates from Cosmos `templates`.
- **Output schema** (`DocumentAgentOutput`):

> `risk_level` (severity): `HIGH` / `MEDIUM` / `LOW` / `LOW_CONFIDENCE` / `BLOCKED`.
> `agent_recommendation` (verdict): The agent's explicit recommendation is `APPROVE` (action required) or `REJECT` (false positive or no action required). GMP requires the decision to be documented regardless of the outcome.

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

| Condition | Condition | UI behavior | Audit trail |
|---|---|---|---|
| **NORMAL** | confidence ≥ 0.7 | Recommendation + `agent_recommendation` (APPROVE/REJECT) + editable WO / audit drafts. Buttons: [Approve] [Reject] [More info] | `confidence_score`, `operator_agrees_with_agent` |
| **LOW_CONFIDENCE** | confidence < 0.7 | Banner: "AI Confidence Not Enough." Recommendation and drafts are shown, editable. Comment is required. Buttons: [Approve] [Reject] [More info] | `human_override = true`, mandatory comment |
| **BLOCKED** | agent failure / exception | Banner: "AI failed to generate recommendation." Empty forms WO draft + audit entry draft — the operator fills in manually (required for Approve). Buttons: [Approve] [Reject] | `confidence = 0`, `human_override = true`, mandatory free-text |

> **Escalation to QA Manager** occurs **exclusively** after the `HITL_TIMEOUT_HOURS` timeout. Low confidence or BLOCKED status **does not** trigger escalation — the operator can always make a decision on his own.

#### 7.3.2 Evidence verification pass

Reasoning and verification are two different steps. The Agent offers citations, but the final decision package undergoes a separate server-side check before being recorded in Cosmos and displayed in the UI.

| What are we checking | Who performs | Why |
|---|---|---|
| Availability of the document Backend normalization layer | The recommendation cannot refer to a non-existent SOP / GMP doc |
| Match `document_id` / title / link | Backend verification, regardless of the agent | So that generic labels (`sop`, `gmp`) do not fall into the decision package |
| Section claim (`§4.2`, `§6.3`) | Authoritative chunk match in Azure AI Search | So that the model does not issue a paragraph hallucination as verified evidence
| Excerpt anchor | Authoritative chunk text | Keep only quotes that can actually be traced to retrieved evidence |

**Behavior:** if the document is found and the section is confirmed → citation `verified`. If the document is found, but the section is not confirmed → the citation remains visible as `unresolved`, it is not raised to the top-level `regulatory_reference`. If the document/link is not verified → the citation is not considered as verified evidence.

### 7.4 Execution Agent

- **Type:** Foundry agent with MCP tools.
- **Trigger:** only after `operator_decision == "approved"`. With `rejected`, this agent **does not start**.
- **Input payload:** is formed with operator verified `work_order_draft` and `audit_entry_draft` (editable forms in UI; pre-filled by Document Agent; operator/QA can edit; other roles read-only). In the BLOCKED state, the fields are empty, the operator fills in manually.
- **MCP tools and external systems:**
- `create_work_order(payload)` → **mcp-cmms** → **CMMS** (SAP PM / IBM Maximo): physically creates a work order in the maintenance planning system. Returns `work_order_id`.
- `create_audit_entry(payload)` → **mcp-qms** → **QMS** (SAP QM / TrackWise / Veeva Vault): registers a GMP deviation record with all fields for regulatory audit. Returns `audit_entry_id`.
- **IDs** returned by external systems are stored in Cosmos `approval-tasks` and `incident_events` for traceability.
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
Operator sees:
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
│ confidence < 0.7: LOW_CONFIDENCE banner,
│ comment is mandatory
│ BLOCKED (agent fail): empty forms,
│ operator fills in manually
                                  │
          ┌───────────────┬────────┴───────┬──────────────────────────────┐
          ↓               ↓               ↓                              ↓
       Approved        Rejected        More info        Timeout HITL_TIMEOUT_HOURS
          │               │               │             (default 24h;
│ │ │ ≤1h for continuous. whirlwind)
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

### 9.1 Cosmos DB — container schema

**Database:** `sentinel-intelligence` · Serverless · 8 containers.

| Container | Partition Key | Purpose |
|---|---|---|
| `incidents` | `/equipmentId` | Main incident + AI analysis + workflow state |
| `incident_events` | `/incidentId` | Business audit trail, operator transcript, coarse agent lifecycle events |
| `notifications` | `/incidentId` | SignalR-facing notification records + delivery state |
| `equipment` | `/id` | CMMS master data: validated params, PM history |
| `batches` | `/equipmentId` | MES data: current and completed batch records |
| `capa-plans` | `/incidentId` | Draft CAPA plans from Document Agent |
| `approval-tasks` | `/incidentId` | HITL approval tasks + execution results |
| `templates` | `/id` | IT Admin editable work order / audit entry templates |

> **Cross-partition query:** `incidents` is partitioned by `/equipmentId`. Queries `GET /api/incidents` (list of all) and filters on `status`/`date`/`severity` — cross-partition. Materialized view via Change Feed → secondary index by `status + createdAt` serves dashboard streams.

### 9.2 Access matrix

| Container | Service / Agent | Operation | Tool |
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

| Data | Method | Why |
|---|---|---|
| Equipment validated parameters (PAR) | MCP (Cosmos) | Structured — exact meaning is more important than semantic match; equipment-level validated range |
| Current batch context | MCP (Cosmos) | Structured, current state |
| **BPR product specs (NOR)** | **RAG (`idx-bpr-documents`)** | Semantic search — product-specific CPP ranges narrower than equipment PAR |
| Historical incidents (semantic) | RAG (`idx-incident-history`) | Semantic similarity — «find similar cases» |
| SOPs / procedures | RAG (`idx-sop-documents`) | Semantic search on the text of procedures |
| Equipment manuals | RAG (`idx-equipment-manuals`) | Semantic search on technical documentation |
| GMP policies / regulations | RAG (`idx-gmp-policies`) | Semantic search on regulatory text |
| Work order status | MCP (CMMS) | Structured, external system |
| Audit entry IDs | MCP (QMS) | Structured, external system |

---

## 11. Backend API surface

| Method + path | Trigger | Role |
|---|---|---|
| `POST /api/alerts` | HTTP | Ingest alert → Service Bus (idempotent via `sourceAlertId`) |
| `GET /api/incidents` | HTTP | List of incidents (filter by status / severity / date) |
| `GET /api/incidents/{id}` | HTTP | Details incident + latest AI analysis |
| `GET /api/incidents/{id}/events` | HTTP | Chronological timeline for UI |
| `GET /api/incidents/{id}/agent-telemetry` | HTTP | IT Admin / auditor — structured agent trace with App Insights |
| `POST /api/incidents/{id}/decision` | HTTP | Takes operator decision → `raise_event` on Durable |
| `GET /api/notifications` | HTTP | Unread notifications for operator UX |
| `GET /api/notifications/summary` | HTTP | Counters for the header |
| `GET /api/equipment/{id}` | HTTP | Read equipment master data |
| `GET /api/batches/current/{equipment_id}` | HTTP | Read current batch for equipment |
| `GET/PUT /api/templates/{id}` | HTTP | IT Admin template management |
| `POST /api/negotiate` | HTTP | SignalR negotiate endpoint (bearer token → role-based groups) |

AuthN: Bearer token from Entra ID. AuthZ: App Roles are checked in every HTTP trigger.

---

## 12. Azure Functions map

### 12.1 Flow from Service Bus to pause

```
Service Bus: alert-queue
      │  trigger
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│  alert_processor  (Service Bus Trigger)                             │
│                                                                     │
│ • Receives alert from queue │
│ • Generates incident_id (uuid) │
│ • Calls client.start_new("deviation_orchestrator", input=...) │
│ • Terminates immediately — the orchestrator starts independently │
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
│ (serialized in Azure Storage; RAM is freed) │
│                                                                     │
│ # more_info loop (max rounds via MAX_MORE_INFO_ROUNDS) │
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

### 12.2 How the orchestrator wakes up

```
React UI: operator clicks [Approve] / [Reject] / [More info]
      │
      │  POST /api/incidents/{id}/decision
      │  { "decision": "approved", "comment": "LIMS verified" }
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│  decision_handler  (HTTP Trigger)                                   │
│                                                                     │
│  1. Validates request (Entra ID bearer)                             │
│ 2. Reads instance_id from approval-tasks (by incident_id) │
│  3. await client.raise_event(                                       │
│         instance_id, "operator_decision",                           │
│         { "decision": ..., "comment": ... })                        │
│  4. HTTP 200                                                        │
│                                                                     │
│ → Durable finds an instance in Azure Storage │
│ → replay orchestrator from the beginning │
│ → reaches WaitForExternalEvent → event already exists → continues │
└─────────────────────────────────────────────────────────────────────┘
```

### 12.3 Full feature map

| Function | Trigger type | File | Role |
|---|---|---|---|
| `ingest_alert` | HTTP | `function_app.py` | REST `POST /api/alerts` → Service Bus (idempotent) |
| `alert_processor` | Service Bus | `function_app.py` | Workflow entry point: alert → orchestrator start |
| `deviation_orchestrator` | Durable Orchestrator | `function_app.py` | Coordinates the entire workflow
| `create_incident` | Durable Activity | `function_app.py` | Cosmos write: new incident |
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

**Idempotency.** `POST /api/alerts` accepts `alert_id` in payload; `ingest_alert` checks an existing incident with `sourceAlertId == alert_id` before publishing to Service Bus. Duplicates return `HTTP 200` from existing `incident_id`.

**Foundry.** Not an Azure Function - an external service that `run_*_agent` activities call through the `azure-ai-projects` SDK.

---

## 13. Real-time layer — SignalR

Hub: `deviationHub` · Negotiate: `POST /api/negotiate` (Bearer → role-based groups).

The real-time layer is consumed by both delivery channels: the browser SPA and the Electron desktop app. This matters for production operations because operators may keep the console minimized while working on the shop floor. Electron maps the same unread notification state to a native app badge and uses a narrow preload bridge (`window.sentinelDesktop`) for native notifications and incident deep links. The web path remains unchanged and uses the in-app notification center/browser notification fallback.

| Group | Events |
|---|---|
| `role:operator` | `incident_pending_approval`, `incident_updated` |
| `role:qa-manager` | `incident_escalated`, `incident_pending_approval` |
| `incident:{id}` | `incident_status_changed`, `agent_step_completed` |

> Full contract (events, payloads, negotiation flow): [docs/signalr-contract.md](./docs/signalr-contract.md).

---

## 14. Document ingestion

5 Blob containers → 5 Azure Function blob triggers → 5 Azure AI Search indexes (one per source type). BPR-ingestor uses table-aware chunking for GMP compliance.

| Container | Index | Notes |
|---|---|---|
| `blob-sop` | `idx-sop-documents` | 500 tokens, 50 overlap |
| `blob-manuals` | `idx-equipment-manuals` | + `equipment_id` tag |
| `blob-gmp` | `idx-gmp-policies` | + clause metadata |
| `blob-bpr` | `idx-bpr-documents` | Table-aware, max ~1200 tokens |
| `blob-history` | `idx-incident-history` | Generated from Cosmos on `finalize_audit` |

> Full specification (rationale, agent → index mapping, Bicep): [docs/document-ingestion.md](./docs/document-ingestion.md).

---

## 15. Agent observability

A structured agent trace for incident-level troubleshooting is emitted from `run_foundry_agents`.

### 15.1 What we observe

- outer prompt sent to Foundry Orchestrator Agent;
- system prompts Orchestrator / Research / Document;
- final thread messages from Foundry;
- raw top-level response;
- parsed JSON package;
- normalized final result that persists in Cosmos and is shown in the UI.

> SDK limitations: current `azure-ai-agents` SDK does not expose connected sub-agent run steps directly → internal Research/Document invocation payloads are partially visible. The target architecture involves switching to the SDK version with deep-step visibility as soon as it stabilizes.

### 15.2 Trace contract

Marker: `FOUNDRY_PROMPT_TRACE`. Fields: `incident_id`, `round`, `trace_kind`, `chunk_index`, `chunk_count`, `thread_id`, `run_id`.

Trace kinds: `prompt_context`, `orchestrator_user_prompt`, `thread_messages`, `raw_response`, `parsed_response`, `normalized_result`.

### 15.3 Separation of Repositories

- **Cosmos `incident_events`** — business-facing timeline (`analysis_started`, `agent_response`, `more_info`, approval / rejection / escalation). Optimized for incident-centric UI reads.
- **App Insights / Log Analytics** — deep Foundry trace by `FOUNDRY_PROMPT_TRACE`. Optimized for troubleshooting, prompt inspection, post-mortem.

### 15.4 Admin delivery path

`GET /api/incidents/{id}/agent-telemetry`:

1. Query App Insights / Log Analytics for `FOUNDRY_PROMPT_TRACE` rows by `incident_id`.
2. Normalize trace records in frontend-friendly DTO (summary cards + chronological items).
3. Merge in `incident_events` lines so that admin can see business + deep trace on one page.

Optional optimization — persist compact admin-relevant projection in `incident_events` with `type = "agent_telemetry"` for fast UI rendering.

---

## 16. Security architecture

### 16.1 Identity & access

- **Azure Entra ID** — AuthN for SPA through MSAL; AuthZ via App Roles on App Registration.
- **`assignment_required = true`** — only designated users/groups can log in.
- **Managed Identity (System-assigned)** on Function App — roles on Cosmos, Service Bus, AI Search, Key Vault, Azure OpenAI, SignalR, Storage. No connection strings in the code.
- **Conditional Access** (Entra P2): MFA for all users, blocking non-EU countries (GMP pharma compliance), require compliant device for IT Admin.
- **Azure PIM** (Entra P2): JIT-eligible Contributor for IT Admin (1-4h activation with justification), eligible Reviewer for QA Manager. Constantly active: `operator`, `maint-tech`, `auditor` (read-only).
- **Entra Security Groups:** `sg-sentinel-operators`, `sg-sentinel-qa-managers`, `sg-sentinel-auditors`, `sg-sentinel-it-admin`. Lifecycle Workflows: auto MFA setup on onboarding, auto group removal on offboarding.

### 16.2 Network isolation

```
VNet: 10.0.0.0/16
snet-functions (10.0.1.0/24) — VNet Integration for Function App (Flex Consumption)
    NSG: allow outbound → snet-private-endpoints, deny internet
snet-private-endpoints (10.0.2.0/24) — Private Endpoints for all PaaS
    NSG: deny all inbound except VNet
    PE: Cosmos DB · AI Search · Service Bus · Storage · Key Vault · Azure OpenAI · SignalR
    Private DNS Zones: auto-resolution per service

PaaS: publicNetworkAccess = Disabled after PE activation
```

### 16.3 Secrets

- **Key Vault** keeps all secrets and API keys. Functions are read via `DefaultAzureCredential` + Managed Identity.
- **Rotation policy:** 90 days for all secrets + Event Grid trigger for rotation → notification in IT Admin.
- **No shared accounts, no keys in repo, no keys in App Settings.**

### 16.4 Threat protection

- **Microsoft Defender for Cloud** — plans for App Service + Key Vault + Cosmos DB + Storage.
- **Block legacy auth** via CA: deny Basic / NTLM / legacy OAuth.
- **TLS 1.2+** enforced on all endpoints; HSTS on SWA.
- **Input validation** on all HTTP triggers; ORM parameterization; no dynamic SQL.

### 16.5 Resource governance

- **Tags** on each Bicep module: `environment`, `team`, `cost-center`, `data-classification`, `owner`.
- **Azure Policy** enforcement: `publicNetworkAccess = Disabled`, allowed regions, enforced tags.

---

## 17. Reliability architecture

### 17.1 Ingestion + workflow

- **Service Bus** `alert-queue`: DLQ after 3 auto-retries, at-least-once delivery, idempotency via `sourceAlertId`.
- **Durable Functions** `RetryPolicy(max_number_of_attempts=3, first_retry_interval=5s)` with exponential backoff on all activities.
- **Cosmos DB Serverless** — autoscale without manual provisioning; change-feed for materialized view on `status + createdAt`.
- **`MAX_MORE_INFO_ROUNDS = 3`** — protection against an endless `more_info` loop.
- **24h HITL timeout** → Durable `create_timer` + race-pattern escalate to QA Manager.

### 17.5 Orchestrator Watchdog - Autodetection and Recovery

Azure Durable Functions store state in Azure Storage Tables. If the Function App restarts during deployment or the orchestrator crashes — Cosmos DB remains in `pending_approval` status, but the Durable instance disappears (NOT_FOUND). Operator cannot submit a decision.

**Solution - `orchestrator_watchdog` Timer Trigger (every 5 minutes):**

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

**Key features:**
- **Two types of detection:**
- *Stuck analysis* — `open/queued/analyzing/analyzing_agents` is older than the threshold (15 min by default)
- *Orphaned approval* — `pending_approval` + Durable NOT_FOUND (grace period 2 min)
- **Idempotent recovery** — only republish to Service Bus; the orchestrator itself will reset the status in Cosmos at startup
- **Safety cap** — no more than 10 recoveries per run

### 17.2 Fallback & circuit breaker

- **Fallback mode:** if Foundry Agent is unavailable or citations validation fails → operator receives pre-filled manual CAPA template instead of AI-recommendations + explicit `degraded_mode=true` in UI.
- **Circuit breaker:** 3 consecutive Foundry failures → circuit open → fallback; auto-reset after 60s with half-open probe.

### 17.3 SLOs + alerts

| Metric | SLO | Alert |
|---|---|---|
| P95 `POST /api/alerts` latency | < 2s | > 2s × 5 min |
| P95 `GET /incidents` latency | < 500ms | > 500ms × 5 min |
| E2E agent pipeline latency (alert → approval-ready) | < 120s | > 180s × 3 events |
| DLQ depth | 0 | > 0 |
| Foundry failure rate | < 1% | > 5% × 10 min |
| Cosmos RU throttling | 0 | > 0 |

Alerts — Azure Monitor action group → email + Teams webhook.

### 17.4 Chaos & DR

- **Azure Chaos Studio** scenarios: Foundry timeout, Service Bus outage, Cosmos throttling, Key Vault unavailability. They are rushed to staging every month.
- **Multi-region DR:** Cosmos DB geo-redundancy (primary Sweden Central, secondary North Europe); AI Search replica in secondary region; Service Bus geo-recovery pair.
- **Recovery runbook** in [docs/operations-runbook.md](./docs/operations-runbook.md): how to recover incidents stuck after max retries; how to replay DLQ; how to switch to DR region.

---

## 18. Operational Excellence & Performance

### 18.1 Observability stack

- **Application Insights** — traces (including `FOUNDRY_PROMPT_TRACE`), exceptions, dependencies, metrics.
- **Log Analytics** workspace — 30 days retention (hot) + archive in Storage for audit (2 years).
- **Cosmos `incident_events`** — business timeline for inspection-ready reports.
- **Custom workbooks:** agent performance, hallucination rate, confidence distribution, HITL latency, DLQ health.

### 18.2 Cost management

- **Azure Budgets** (`Microsoft.Consumption/budgets`) per environment with 50/80/100% alerts.
- **Cosmos Serverless** + **AI Search Free/Basic scaled to Standard** — pay-per-use, no idle cost.
- **Function App Flex Consumption** — autoscale + VNet Integration.
- **Tags** `cost-center` allow cost allocation per product line.

### 18.3 Performance & load testing

Expected production load:

- **Alert ingestion spike:** 50–200 concurrent alerts at batch-close changes;
- **SignalR:** 50–200 operator sessions simultaneously;
- **Foundry agent:** 5–10 concurrent orchestrations (30–120s each);
- **API:** P95 < 500ms (read), P95 < 2s (`POST /alerts`).

**Azure Load Testing** scripts (Locust/JMeter):

1. `scenario-alert-spike` — POST `/api/alerts` × 200 RPS × 5 min;
2. `scenario-signalr-concurrent` — 200 SignalR clients, join/leave incident groups;
3. `scenario-agent-pipeline` — 10 concurrent orchestrations end-to-end;
4. `scenario-api-read` — GET `/incidents` × 500 RPS.

They are launched in staging before each prod release via GitHub Actions `load-test.yml` workflow.

### 18.4 Deployment governance

- **Bicep IaC** — `infra/main.bicep` + modules per resource. What-if analysis in PR check.
- **GitHub Actions:**
  - `ci.yml` — build, lint, unit tests, Bicep lint + what-if;
  - `deploy.yml` — bicep deploy + functions deploy + Foundry eval gate + smoke test;
  - `load-test.yml` — staging performance gate.
- **Foundry eval gate** — before promotion of the new version of the agent: groundedness / coherence / relevance / F1 vs baseline in Azure AI Foundry Evaluation.

---

## 19. Responsible AI

### 19.1 Guardrails at runtime

- **Confidence gate 0.7** (see [§7.3.1](#731-confidence-gate)).
- **Evidence-grounded output** + backend verification pass (see [§7.3.2](#732-evidence-verification-pass)).
- **Azure Content Safety + Prompt Shield** — input screening (SCADA payloads, operator messages) + output screening (agent responses) before persisting or displaying in the UI.
- **Mandatory human approval** — no execution takes place without an operator decision (GxP).
- **Separate reasoning vs verification** — the model suggests, the backend verifies citations.

### 19.2 Governance lifecycle

- **Model versioning:** each new version of the agent has a semantic version (`orchestrator-v1.3.2`); deployment via Bicep.
- **Eval pipeline gate:** nightly runs Groundedness / Coherence / Relevance / F1 via Azure AI Foundry Evaluation; promotion is possible only if metrics ≥ baseline thresholds.
- **Rollback:** one command `make agent-rollback VERSION=...` — returns the previous `assistant_id` in Functions config.
- **Red-team testing protocol** — a formal session before each major release for GMP-critical recommendations.

### 19.3 Transparency & auditability

- Evidence citations from `document_id`, section, excerpt, relevance score in the decision package.
- `human_override`, `operator_comment`, `confidence_score` in the audit record.
- Hallucination rate dashboard in App Insights workbook (trend per agent per week).
- `GET /api/incidents/{id}/agent-telemetry` — complete prompt/response trace for IT Admin and auditor.

---

## 20. Identity, roles & RBAC

### 20.1 App Roles (Entra ID App Registration)

| Role | App Role value | Access |
|---|---|---|
| Production Operator | `operator` | Incident list + decision UI for assigned incidents |
| QA Manager | `qa-manager` | All incidents + escalation queue + manager approvals |
| Maintenance Technician | `maint-tech` | Read-only work orders |
| Auditor | `auditor` | Read-only audit trail + agent telemetry |
| IT Admin | `it-admin` | Templates CRUD + agent telemetry + config management |

### 20.2 Enforcement

- On SPA: MSAL bearer, role claims are checked in route guards.
- On Backend API: decorator `@require_role("...")` on each HTTP trigger.
- On Azure resources: the Managed Identity Function App has only minimal data-plane roles (Cosmos `DocumentDB Data Contributor`, AI Search `Search Index Data Contributor`, etc.); control-plane - only through IT Admin JIT.

> Details of role mapping in Entra: [docs/entra-role-assignment.md](./docs/entra-role-assignment.md).

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
| Desktop shell | Electron | Secure preload bridge, `HashRouter` for `file://`, native unread badge + OS notifications |
| Auth | Azure Entry ID (MSAL) | Managed Identities on all Functions |
| Secrets | Azure Key Vault | `azure-keyvault-secrets` + MI + rotation |
| Network | VNet + Private Endpoints + Private DNS | Flex Consumption plan |
| Monitoring | App Insights + Log Analytics + Defender for Cloud | Custom workbooks |
| IaC | Bicep | `infra/main.bicep` + modules |
| CI/CD | GitHub Actions | `ci.yml`, `deploy.yml`, `load-test.yml` |

---


---

## Related documents

Architecture consciously contains only **TO-BE design**. Companion artifacts live in their own documents:

| Topic | Document |
|---|---|
| Architectural solutions (ADR-001, ADR-002, ...) | [docs/architecture-decisions.md](./docs/architecture-decisions.md) |
| Version history + AS-SUBMITTED v1.0 scheme + evolution of components | [docs/architecture-history.md](./docs/architecture-history.md) |
| Reduction of prototype and post-hackathon backlog (T-039, T-040, T-047–T-051) | [docs/hackathon-scope.md](./docs/hackathon-scope.md) |
| Infrastructure Diagram (Mermaid + Draw.io) | [infra/diagram.md](./infra/diagram.md), [infra/architecture.drawio](./infra/architecture.drawio) |
| Document ingestion pipeline | [docs/document-ingestion.md](./docs/document-ingestion.md) |
| SignalR contract | [docs/signalr-contract.md](./docs/signalr-contract.md) |
| Electron desktop app task | [tasks/T-056-electron-desktop-app.md](./tasks/T-056-electron-desktop-app.md) |
| Operations runbook (DR, recovery, chaos) | [docs/operations-runbook.md](./docs/operations-runbook.md) |
| Entra ID role assignment | [docs/entra-role-assignment.md](./docs/entra-role-assignment.md) |
| Frontend design system | [docs/design-system.md](./docs/design-system.md), [docs/frontend-design.md](./docs/frontend-design.md) |
| Platform reference (resources, endpoints, Cosmos schema) | [docs/platform-reference.md](./docs/platform-reference.md) |

---

← [01 Requirements](./01-requirements.md) · [03 Analysis →](./03-analysis.md)
