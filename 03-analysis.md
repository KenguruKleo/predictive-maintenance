# 03 · Architecture analysis

← [README](./README.md) · [01 Requirements](./01-requirements.md) · [02 Architecture](./02-architecture.md) · [04 Action Plan](./04-action-plan.md)

> **Purpose:** Analysis of the submitted solution - what is good, what needs to be fixed. Based on the official Triage Report dated March 30, 2026. Updated with each iteration of the architecture.

---

## Contents
1. [Triage Report (March 30, 2026)](#1-triage-report-March-30-2026)
2. [Architecture Dimensions](#2-architecture-dimensions)
3. [Use Case Dimensions](#3-use-case-dimensions)
4. [Strengths] (#4-Strengths)
5. [Top-6 Gaps to Fix](#5-top-6-gaps-to-fix)
6. [Azure WAF Gaps](#6-azure-waf-gaps)
7. [Azure AI Pillar Gaps](#7-azure-ai-pillar-gaps)
8. [Cross-cutting checks](#8-cross-cutting-checks)
9. [Progress of patching gaps](#9-progress-patching-gaps)

---

## 1. Triage report (March 30, 2026)

> Source: `docs/triage-report-sentinel-intelligence-20260330_175839.pdf`
> Evaluation system: AI-powered triage system (Capgemini + Microsoft)

### Total result

| Category | Points | Maximum |
|---|---|---|
| Architecture | 33 | 50 |
| Use Case | 38 | 50 |
| **TOTAL** | **71** | **100** |

**Verdict: Good — 71/100**

### Brief summary of triage
> Sentinel Intelligence proposes an AI Foundry-based Operations Assistant for GMP manufacturing that detects anomaly/deviation events from SCADA/MES/IoT signals, enriches them with batch/equipment context, grounds decisions in SOP/BPR/CAPA history via RAG, generates CAPA recommendations and audit-ready reports, and keeps a human approval step before work-order execution.

---

## 2. Architecture Dimensions

| Dimension | Evaluation | Justification | Gaps |
|---|---|---|---|
| **Clarity & Flow** | 8/10 | The flow of detect → context → compliance → CAPA → approval → record is clear. Agent roles and data sources are visible. Exception paths and runtime decision logic remain high-level. | Exception paths are not described, model decision logic is not detailed
| **Platform Fit** | 7/10 | Azure Functions, Azure AI Search, Foundry Agent Service are the right choice for event ingestion, RAG, multi-agent. But: **track not declared**, full developer/platform setup not shown. | Track A not specified, GitHub + CI/CD missing |
| **Data / Governance / Security** | 6/10 | Data sources and governed retrieval are well identified. Human approval and audit logging. But: identity, access control, encryption, retention, classification, private connectivity, content safety — **not described**. | The entire security layer is missing
| **Reliability / Performance / Cost** | 5/10 | KPI < 5 min shows performance intent. But: retries, queues, failure recovery, fallback, model timeout, cost controls, token optimization — **not defined**. | The entire reliability layer is missing
| **Scalability / Integration / Provisioning** | 7/10 | Enterprise integrations are clearly identified. Azure services are named. But: **no IaC**, API contract children, environment topology, repeatable provisioning. | IaC/deployment missing |

---

## 3. Use Case Dimensions

| Dimension | Evaluation | Justification | Gaps |
|---|---|---|---|
| **Value & KPI Impact** | 9/10 | High-value regulated process. Clear business pain points, explicit KPI impact (decision time, QA effort, errors, inspection readiness). Value quantification can be more evidence-based. | KPI evidence-base can be strengthened |
| **Innovation** | 8/10 | The combination: predictive signal interpretation + GMP compliance validation + CAPA recommendation + audit trail is more differentiated than basic chatbot/anomaly detector. Thoughtful multi-agent design tied to regulated workflow. | — |
| **AI Fit** | 8/10 | AI is well suited for contextual retrieval, historical pattern interpretation, recommendation drafting, evidence packaging. Human approval is important for GxP. But: **Responsible AI controls are not explicit**. | RAI is not detailed |
| **UX Simplicity** | 6/10 | Process-level description is there, but **actual user interface/channel is not described**. Ease of use, explainability, approval ergonomics - cannot be estimated. | Operator UI is not defined |
| **Build–Scale–Reuse** | 7/10 | MVP feasible when narrowed down to 1 asset type, 1 deviation class, small SOP/CAPA set. Retrieval and agent patterns reusable. But: **reusable MCP assets/connectors and production-scale constraints are not specified**. | MVP scope is not narrowed |

---

## 4. Strengths

> We maintain and support in the following iterations:

### Architecture
- ✅ **Clarity & Flow** — detect → context → compliance → CAPA → human approval → record: clear and easy to understand
- ✅ **Platform Fit** — Azure Functions (event-driven ingest), Azure AI Search (RAG), Foundry Agent Service (orchestration): the right choice for a GMP scenario
- ✅ **Governance-aware design** — SOP/BPR/CAPA grounding, mandatory human review, audit logging correspond to regulated manufacturing
- ✅ **Enterprise integrations** — MES, SCADA, CMMS, QMS, asset history: operationally relevant, not an isolated demo

### Use Case
- ✅ **Strong GMP problem statement** — explicit stakeholder set, regulated industry context
- ✅ **KPI business-facing** — decision latency, manual QA effort, inspection preparation: understood by business
- ✅ **Innovation** — multi-agent design tied to real regulated workflow (not just a chatbot)
- ✅ **AI Fit for the task** — contextual retrieval, historical pattern interpretation, recommendation drafting

---

## 5. Top 6 Gaps to fix

### Gap #1: Track not declared

| Parameter | Value |
|---|---|
| **Severity** | 🔴 CRITICAL is a compliance failure
| **Evaluation check** | Environment Track declared → FAIL |
| **Affects** | Platform Fit (−2), failed cross-cutting check |

**Problem:** Track A (GitHub + Azure + Foundry) is not explicitly specified. Submission does not show where GitHub, CI/CD, deployment workflows are included in the lifecycle.

**What you need:**
- Explicitly indicate "Track A — GitHub + Azure + Azure AI Foundry"
- Add GitHub repo to architecture diagram
- Show CI/CD pipeline (GitHub Actions)
- Show deployment workflow: dev → staging → prod
- Evaluation pipeline through AI Foundry

**Where to fix:** → [02 · Architecture — GitHub + CI/CD section](./02-architecture.md#github--cicd-gap-1)
**Task:** → [04 · Action Plan](./04-action-plan.md)

---

### Gap #2: Security

| Parameter | Value |
|---|---|
| **Severity** | 🔴 HIGH |
| **Evaluation check** | Data/Governance/Security → 6/10, Microsoft Security & Monitoring → WARN |
| **Affects** | Architecture score −4, WAF Security pillar |

**Problem:** Audit logging is available, but the entire security layer is missing:
- There is no identity architecture
- No RBAC (who can do what)
- No secrets handling
- No network isolation
- There is no encryption specification
- No SIEM/monitoring

**What you need:**
```
Identity:
- Azure Entra ID (Managed Identities for Azure Functions, Foundry, AI Search)
- No hardcoded credentials — all via Managed Identity or Key Vault references

Secrets:
- Azure Key Vault for all API keys, connection strings, certificates

Network:
- Private Endpoints for AI Search, Foundry, Storage
- VNet Integration for Azure Functions
  - NSG rules

RBAC (minimum role set):
- Operator: can view alerts, approving/declining recommendations
- QA Engineer: can review + edit CAPA, escalate
  - Compliance Officer: read-only audit trail, reporting
  - Admin/IT: full access, deployment
  - Agent Service Principal: read-only SOP/CAPA (least privilege)

Data:
  - Encryption at rest: Azure Storage, AI Search (default AES-256)
  - Encryption in transit: TLS 1.2+ (default Azure)
  - Data classification: SOP (Confidential), CAPA (Restricted), audit logs (Restricted)

Monitoring:
  - Azure Monitor + Log Analytics workspace
- Alerts on failed events, security incidents
- (Optional) Microsoft Sentinel SIEM
```

**Where to fix:** → [02 · Architecture — Security section](./02-architecture.md#16-security-architecture)
**Requirements:** → [01 · Requirements — Security](./01-requirements.md#8-security--monitoring-requirements)

---

### Gap #3: Reliability

| Parameter | Value |
|---|---|
| **Severity** | 🔴 HIGH |
| **Evaluation check** | Reliability/Performance/Cost → 5/10 (lowest score), Azure WAF Reliability → WARN |
| **Affects** | Architecture score −5 |

**Problem:** GMP-critical workflow without visibility:
- No event queuing (if Functions crashed, the event is lost)
- There is no retry strategy
- No dead-letter handling
- There is no fallback mode
- No model timeout handling
- There are no cost controls

**What you need:**
```
Event Queuing:
- Azure Service Bus (preferred for reliable messaging) or Event Hubs (streaming)
  - SCADA/MES → Service Bus Topic → Azure Functions
- Dead Letter Queue for failed/unprocessable events

Retry:
  - Azure Functions: retry policy (exponential backoff, max 3 attempts)
- Agent calls: retry on transient failures (timeouts, throttling)
  - Per-service retry budgets

Circuit Breaker:
- At > N failures by window → circuit open → manual fallback mode

Fallback Mode:
- If AI is not available → alert operator without AI recommendation
- Manual-only operating mode for GMP continuity

Latency Budgets:
- Context enrichment: < 30 sec
- Compliance Agent: < 90 sec
- CAPA Agent: < 90 sec
- Total to decision package: < 5 min (our KPI)
  - Human approval: async (no timeout)

Cost Controls:
  - Token budgets per agent call
- Caching for frequently retrieved SOPs
- Model routing: cheapest model for simple classification, GPT-4 for complex reasoning
```

**Where to fix:** → [02 · Architecture — Reliability section](./02-architecture.md#17-reliability-architecture)
**Requirements:** → [01 · Requirements — WAF](./01-requirements.md#6-azure-waf-requirements)

---

### Gap #4: Responsible AI (RAI)

| Parameter | Value |
|---|---|
| **Severity** | 🟠 HIGH |
| **Evaluation check** | AI Fit → 8/10 with caveat, Azure WAF AI Pillar → WARN |
| **Affects** | Use Case score −2, AI Pillar compliance |

**Problem:** Partial RAI coverage:
- There are no confidence thresholds
- No evidence gating (recommendation without a source → not allowed)
- No hallucination controls
- There is no separately described verification-pass for document identity and citation section claims
- No prompt-injection defenses
- There is no agent observability
- No model versioning/rollback

**What you need:**
```
Confidence & Evidence:
- Each Compliance Agent recommendation MUST have: SOP reference + page + GMP clause
- Each CAPA recommendation MUST have: CAPA history case reference + similarity score
- Confidence threshold: < 0.7 → escalate to human (do not show as a recommendation)
- Evidence mandatory gate: without evidence → the recommendation is blocked

Hallucination Controls:
- Grounded generation only (RAG, not free generation)
- Source verification: the agent must confirm that the source exists in Azure AI Search
- Separate document/citation verification layer: after the agent output, the backend independently checks `document_id`, title, link, section claim, excerpt anchor
- If there is a document match, but the section claim is not confirmed by the authoritative chunk, the system shows the citation as `unresolved`, but does not raise the unverified section in the summary fields
- Structured output schema (JSON with mandatory evidence fields)

Prompt Injection:
- Input validation on SCADA/MES data (sanitize before transfer to the agent)
- System prompt hardening (boundaries between data and instructions)
- Azure AI Content Safety before egress

Observability:
- Azure Monitor + Application Insights tracing of each agent call
  - Log: prompt → retrieved docs → output → confidence score → human decision
- Alerting on abnormal behavior of agents

Model Lifecycle:
- Versioning of deployed models (model name + version explicit)
- Rollback plan during regression
- Evaluation runs before deployments (AI Foundry evaluation)
```

**Where to fix:** → [02 · Architecture — RAI section](./02-architecture.md#layer-responsible-ai-gap-4)
**Requirements:** → [01 · Requirements — AI Pillar](./01-requirements.md#7-azure-ai-pillar-requirements)

---

### Gap #5: UX

| Parameter | Value |
|---|---|
| **Severity** | 🟠 MEDIUM |
| **Evaluation check** | UX Simplicity → 6/10 |
| **Affects** | Use Case score −4 |

**Problem:** Process-level description without interface:
- It is not shown where the operator sees the decision package
- It is not shown how he approves/denies
- Explainability and trustworthiness cannot be assessed

**What you need:**
```
Operator interface (choose one option):
Option A: Microsoft Teams Adaptive Card
- Alert card in Teams channel
- Shows: summary + risk level + CAPA recommendation + evidence source
- Built-in buttons: [Approve] [Deny] [Ask Question]
- Teams bot for Q&A with an agent
✅ Pros: no new app, familiar UX, integrates with Teams
⚠️ Cons: limited layout

Option B: Power Apps portal (low-code)
    - Dedicated operator dashboard
    - Queue of pending approvals
- Detail view with full evidence
✅ Pros: rich UX, can be branded
⚠️ Cons: requires a Power Apps license

Option C: Custom Web App (Azure Static Web Apps)
    - React/minimal web app
- Hosted on Azure Static Web Apps
✅ Pros: full control, Track A aligned
⚠️ Cons: more work

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

**Where to fix:** → [02 · Architecture — UX section](./02-architecture.md#operator-ux-gap-5)

---

### Gap #6: IaC / Provisioning

| Parameter | Value |
|---|---|
| **Severity** | 🟡 MEDIUM |
| **Evaluation check** | Scalability/Integration/Provisioning → 7/10 |
| **Affects** | Architecture score −3 |

**Problem:** Architecture lists services but not deployment mechanisms.

**What you need:**
```
IaC:
- Bicep or Terraform templates for all Azure resources
  - Resource groups: rg-sentinel-dev / rg-sentinel-staging / rg-sentinel-prod
- Parameters for environment-specific values

Environments:
- dev: for development and testing
- staging: for validation before production
- prod: for demo/finals

GitHub Actions:
- CI: lint + unit tests on PR
- CD: deploy to staging on merge to main
  - Manual gate: promote staging → prod

Monitoring setup:
  - Log Analytics Workspace provisioned via IaC
- Application Insights for each Azure Function
- Dashboards in Azure Monitor
```

**Where to fix:** → [02 · Architecture — IaC section](./02-architecture.md#github--cicd-gap-1)

---

## 6. Azure WAF Gaps

| WAF Pillar | Status | What is missing | Priority |
|---|---|---|---|
| **Reliability** | ❌ WARN | Queuing, retry, DLQ, fallback, degraded mode | 🔴 HIGH |
| **Security** | ❌ WARN | Identity, RBAC, Key Vault, network isolation, SIEM | 🔴 HIGH |
| **Cost Optimisation** | ❌ WARN | Token controls, caching, model routing, per-event cost | 🟠 MEDIUM |
| **Operational Excellence** | ❌ WARN | Monitoring, alerting, CI/CD, observability | 🟠 MEDIUM |
| **Performance Efficiency** | ⚠️ PARTIAL | KPI < 5 min is available, latency SLOs are not detailed | 🟡 LOW |

---

## 7. Azure AI Pillar Gaps

| AI Pillar Requirement | Status | Details |
|---|---|---|
| Agent Design | ✅ GOOD | Multi-agent orchestration, clear roles |
| Grounding / RAG | ✅ GOOD | Validated SOP/BPR, CAPA history retrieval |
| Model Lifecycle | ⚠️ PARTIAL | Evaluation and governed deployment are mentioned but not detailed
| Responsible AI | ❌ MISSING | Confidence thresholds, evidence gating, hallucination controls |
| AI Observability | ⚠️ PARTIAL | Incident-scoped App Insights traces now cover the backend-visible Foundry path; Cosmos `incident_events` covers business audit / transcript only; dashboards, alerts, and admin retrieval UX are still pending |
| Prompt Injection Defense | ❌ MISSING | Content safety, input validation |

---

## 8. Cross-cutting checks

Official checks from the triage report:

| Check | Status (v1.0) | Status (current) | Action |
|---|---|---|---|
| Environment Track declared | ❌ FAIL | ❌ Not fixed | → [Gap #1](#gap-1-track-undeclared) |
| Industry Use Case aligned | ✅ PASS | ✅ | Save |
| Azure WAF aligned | ⚠️ WARN | ⚠️ | → [Gap #2](#gap-2-security), [#3](#gap-3-reliability) |
| Azure WAF AI Pillar aligned | ⚠️ WARN | ⚠️ | → [Gap #4](#gap-4-responsible-ai-rai) |
| Microsoft Security & Monitoring | ⚠️ WARN | ⚠️ | → [Gap #2](#gap-2-security) |

---

## 9. Gaps correction progress

> Last updated: April 17, 2026 — Architecture v2.0 DESIGNED

| Gap | Priority | Status | Solution in v2.0 | Task |
|---|---|---|---|---|
| #1 Track + GitHub/CI/CD | 🔴 CRITICAL | 🎨 DESIGNED | GitHub Actions CI/CD (T-042) + Bicep IaC (T-041) + Track A clearly in architecture | [T-041](./tasks/T-041-bicep-iac.md), [T-042](./tasks/T-042-cicd.md) |
| #2 Security | 🔴 HIGH | 🎨 DESIGNED | Entra ID + Key Vault + Managed Identities + VNet + 5 RBAC roles | [T-035](./tasks/T-035-rbac.md), [T-038](./tasks/T-038-security.md) |
| #3 Reliability | 🔴 HIGH | 🎨 DESIGNED | Azure Service Bus DLQ + Durable Functions retry + fallback mode + timeout escalation | [T-022](./tasks/T-022-service-bus.md), [T-039](./tasks/T-039-reliability.md) |
| #4 RAI | 🟠 HIGH | 🔧 IN PROGRESS | Confidence gate path already exists; separate document/citation verification and unresolved-evidence downgrade are now explicit architecture controls for anti-hallucination behavior; App Insights prompt and response traces are implemented for the backend-visible Foundry flow, while Content Safety, prompt-injection guard, admin retrieval UX, and dashboards remain pending | [T-040](./tasks/T-040-rai.md), [T-043](./tasks/T-043-agent-telemetry-admin-view.md) |
| #5 UX | 🟠 MEDIUM | 🎨 DESIGNED | React + Vite operator dashboard + approval UX + SignalR real-time + 5 role views | [T-032](./tasks/T-032-frontend-core.md), [T-033](./tasks/T-033-frontend-approval.md) |
| #6 IaC | 🟡 MEDIUM | 🎨 DESIGNED | Bicep `infra/main.bicep` + modules for all 12 resources | [T-041](./tasks/T-041-bicep-iac.md) |

**Status legend:**
🔜 TODO - not started
🎨 DESIGNED - v2.0 architecture is described, tasks are created, implementation begins
🔧 IN PROGRESS — implementation has started
✅ DONE - implemented and tested

---

← [02 Architecture](./02-architecture.md) · [04 Action Plan →](./04-action-plan.md)
