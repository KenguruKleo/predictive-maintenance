# Hackathon Scope vs Target Architecture — Compromises & Post-Hackathon Backlog

> **Purpose of this document.** [`02-architecture.md`](../02-architecture.md) describes the **target architecture** of Sentinel Intelligence - how the system should look in production. This document captures what was deliberately cut from the target architecture for the hackathon prototype, for what reasons, and where it was moved in the roadmap.
>
> For judges/architectural review: **the architecture is fully developed**, the demo shows a prototype of its critical paths (alert → multi-agent reasoning → human approval → execution + audit).

← [README](../README.md) · [02 Architecture](../02-architecture.md) · [04 Action Plan](../04-action-plan.md)

---

## Contents

1. [Principle of Reduction](#1-Principle of Reduction)
2. [What is implemented in the prototype](#2-what-is-implemented-in-the-prototype)
3. [Security - compromises] (#3-security--compromises)
4. [Reliability - trade-offs] (#4-reliability--trade-offs)
5. [Operational Excellence & Performance — trade-offs] (#5-operational-excellence--performance--trade-offs)
6. [Responsible AI - trade-offs](#6-responsible-ai--trade-offs)
7. [Data & Integration — trade-offs](#7-data--integration--trade-offs)
8. [Post-hackathon backlog - tasks](#8-post-hackathon-backlog--tasks)
9. [WAR assessment mapping](#9-war-assessment-mapping)

---

## 1. Principle of reduction

The target architecture is fully designed as a production-ready GMP system. For the demo we leave:

- all **structural elements** (services, data streams, API contracts, data schema);
- all **AI-specific mechanisms** (multi-agent pipeline, HITL, confidence gate, evidence citations, agent observability);
- **audit trail + RBAC** (because this is the core of the GxP value of the solution).

Everything that requires:

- **Entra ID P2 license** (Conditional Access, PIM) — not available in the hackathon sandbox;
- **Flex Consumption / Premium plan** (VNet Integration, Private Endpoints) — the hackathon uses Consumption Y1;
- **Multi-region, DR-testing, load testing, chaos engineering** — operational activities that go beyond the 10-day demo;
- **Formal processes** (red-team testing, model governance lifecycle) — human processes, not code.

---

## 2. What is implemented in the prototype

The demo covers the **critical path** of the target end-to-end architecture:

- POST `/api/alerts` → Service Bus `alert-queue` (with DLQ and retry);
- Durable Functions orchestrator: `create_incident` → `enrich_context` → `run_foundry_agents` → `notify_operator` → `waitForExternalEvent` → `run_execution_agent` → `finalize_audit`;
- Foundry Connected Agents pipeline: Orchestrator Agent → Research Agent (5 RAG indexes + MCP sentinel-db) → Document Agent (confidence gate 0.7) → Execution Agent (MCP-QMS + MCP-CMMS);
- Cosmos DB with 8 containers (`incidents`, `incident_events`, `notifications`, `equipment`, `batches`, `capa-plans`, `approval-tasks`, `templates`);
- Azure AI Search with 5 indexes (SOP, equipment manuals, GMP policies, BPR, incident history);
- Azure SignalR push for real-time UX (operator approve/reject/more_info);
- React + Vite SPA on Azure Static Web Apps, MSAL-authorization, 5 RBAC roles;
- Azure Key Vault + Managed Identities;
- Application Insights with `FOUNDRY_PROMPT_TRACE` structured traces;
- Bicep IaC (`infra/main.bicep` + 5 modules), GitHub Actions CI/CD.

All of the components described in [`02-architecture.md`](../02-architecture.md) are in code or deployed - abbreviated to only the enhanced production configurations listed below.

---

## 3. Security — compromises

### 3.1 Network isolation (SE:06)

**Target Design:** VNet 10.0.0.0/16, `snet-functions` + `snet-private-endpoints`, Private Endpoints for Cosmos / AI Search / Service Bus / Storage / Key Vault / Azure OpenAI, `publicNetworkAccess = Disabled` for all PaaS, Private DNS Zones.

**Hackathon:** Consumption Y1 plan **does not support** VNet Integration → PaaS endpoints are public, protected by Managed Identity + RBAC + HTTPS-only.

**What removes the risk in the prototype:** all calls to Cosmos / Service Bus / AI Search / Key Vault go only through the Managed Identity Function App; there are no shared keys in the code; App Registration has `assignment_required = true`.

**Follow-up:** [T-047 — Network isolation (VNet + PE)](../tasks/)

### 3.2 Privileged access & MFA (SE:05)

**Target Design:**

- Conditional Access: MFA for all users, blocking of non-EU countries (pharma compliance), `compliant device` for IT Admin;
- Azure PIM: JIT-eligible activation of Contributor for IT Admin (1–4h with justification), eligible Reviewer for QA Manager;
- Entra Security Groups: `sg-sentinel-operators`, `sg-sentinel-qa-managers`, `sg-sentinel-auditors`, `sg-sentinel-it-admin`, Lifecycle Workflows for onboarding/offboarding.

**Hackathon:** CA and PIM require Entra ID **P2 license** - not available in sandbox. In the prototype, 5 RBAC roles are implemented through App Roles + assignment_required; MFA is not enforced by policy.

**Follow-up:** [T-048 — Conditional Access + PIM](../tasks/)

### 3.3 Easy wins — Defender, tagging, legacy auth, secret rotation

**Target Design:**

- Microsoft Defender for Cloud for App Service + Key Vault (`Microsoft.Security/pricings`);
- Tags `environment`, `team`, `cost-center`, `data-classification` on each resource;
- CA blocking Basic/NTLM/legacy OAuth;
- Key Vault `rotationPolicy` on all secrets (90 days) + Event Grid trigger.

**Hackathon:** not enabled — technically simple Bicep/config changes (≤ 4h), not included in the 10-day demo scope.

**Follow-up:** [T-049 — WAR easy wins](../tasks/)

---

## 4. Reliability — compromises

### 4.1 Implemented in the prototype

- Service Bus DLQ + 3 auto-retries on `alert-queue`;
- Durable Functions `RetryPolicy(max_number_of_attempts=3, first_retry_interval=5s)` with exponential backoff on all activities;
- Cosmos DB Serverless autoscale;
- `MAX_MORE_INFO_ROUNDS=10` — protection against an endless `more_info` cycle;
- 24h HITL timeout → auto-escalate path through Durable `create_timer`;
- App Insights structured logging + exception tracking.

### 4.2 Post-hackathon (T-039, T-050)

**Target Design:**

- **Fallback mode:** if Foundry Agent fail → degraded mode: operator receives pre-filled manual CAPA template instead of AI-recommendations;
- **Circuit breaker:** 3 consecutive Foundry failures → circuit open → fallback; auto-reset in 60s;
- **Latency SLOs + Azure Monitor alerts:** P95 POST `/api/alerts` < 2s; P95 GET `/incidents` < 500ms; E2E agent pipeline < 120s;
- **Chaos experiments:** Azure Chaos Studio scenarios (Foundry timeout, Service Bus unavailability, Cosmos throttling);
- **Multi-region DR:** Cosmos DB geo-redundancy + AI Search replica in secondary region;
- **Recovery runbook:** documented recovery process for incidents stuck after max retries + DLQ depth alert.

**Why not in the demo:** fallback mode requires a separate manual-CAPA UX; chaos/DR — operational activities with a week horizon.

**Follow-up:** [T-039 — Production reliability](../tasks/), [T-050 — Recovery runbook + DLQ alert](../tasks/)

---

## 5. Operational Excellence & Performance — compromises

### 5.1 Azure Load Testing (PE:05/06)

**Target Design:** Azure Load Testing with Locust/JMeter:

- `scenario-alert-spike` — POST `/api/alerts` × 200 RPS within 5 minutes;
- `scenario-signalr-concurrent` — 200 SignalR clients, join/leave incident groups;
- `scenario-agent-pipeline` — 10 concurrent orchestrations end-to-end;
- `scenario-api-read` — GET `/incidents` × 500 RPS, P95 < 500ms.

Expected production load:

- Alert ingestion spike: 50–200 concurrent with batch-close changes;
- SignalR: 50–200 operator sessions simultaneously;
- Foundry agent: 5–10 concurrent orchestrations (30–120s each);
- API P95 < 500ms (read), P95 < 2s (POST `/alerts`).

**Hackathon:** not implemented. Flex Consumption + Cosmos Serverless have autoscale without manual tuning; load test validates cold start and Cosmos RU throttling risks.

**Follow-up:** [T-051 — Load testing scenarios](../tasks/)

### 5.2 Cost alerts (CO:04)

**Target design:** `Microsoft.Consumption/budgets` + alert rule → email for $X/month.

**Hackathon:** not configured.

**Follow-up:** [T-049 — WAR easy wins](../tasks/)

---

## 6. Responsible AI — compromises

### 6.1 Implemented in the prototype

- Confidence gate 0.7: if `confidence < 0.7` → UI notices the recommendation as `LOW_CONFIDENCE`, operator comment is mandatory; if there is still no evidence → `BLOCKED` + QA Manager auto-escalation;
- Evidence citation contract: `document_id` + section + excerpt + relevance score; backend verification pass (document existence, section claim, excerpt anchor) — see [`02-architecture.md` §7.2](../02-architecture.md);
- Mandatory human approval before any execution;
- Full audit trail in `incident_events` + `FOUNDRY_PROMPT_TRACE` in App Insights;
- Azure Content Safety API — output screening before sending to the operator (partial, without Prompt Shield).

### 6.2 Post-hackathon (T-040)

**Target Design:**

- **Prompt injection detection:** Azure Content Safety Prompt Shield on SCADA input + operator messages;
- **Model versioning + rollback:** Foundry governed deployment — each version of the agent goes through the eval pipeline before promotion, rollback in 1 command;
- **Formal evaluation pipeline:** Groundedness / Coherence / Relevance / F1 through Azure AI Foundry Evaluation, nightly runs with thresholds;
- **Hallucination rate dashboard:** accuracy trend per agent per week → App Insights custom workbook;
- **Red-team testing protocol:** formal red-team session for GMP-critical recommendations before production deploy.

**Follow-up:** [T-040 — Production RAI controls](../tasks/)

---

## 7. Data & Integration — compromises

### 7.1 External systems

**Target design:** integration with production SCADA/MES/CMMS/QMS via REST/OPC UA/file exchanges.

**Hackathon:** all external systems are simulated:

- SCADA/MES → `scripts/simulate_alerts.py` publishes alerts in Service Bus;
- CMMS → MCP server `mcp-cmms` writes to Cosmos `capa-plans` (without real integration);
- QMS → MCP server `mcp-qms` writes to Cosmos `approval-tasks`;
- Equipment/batches — seed dataset in Cosmos (`scripts/seed_cosmos.py`).

MCP tools contracts are identical to production - the transition to real systems occurs by replacing the backend implementation of the MCP server without changing agents.

### 7.2 MCP transport

**Target design:** MCP servers as separate hosted services (HTTP/SSE transport) with own authentication through Managed Identity.

**Hackathon:** MCP servers are started as stdio subprocess with Function App (local transport).

**Follow-up:** moving MCP servers to separate Azure Functions or Container Apps is part of [T-039](../tasks/).

### 7.3 Document ingestion — Blob containers

**Target design:** 5 separate Blob containers (`blob-sop`, `blob-manuals`, `blob-gmp`, `blob-bpr`, `blob-history`) with 5 Azure Function blob triggers → 5 AI Search indexes.

**Hackathon:** 1 container `documents` with path-based routing; the rest of the containers in the roadmap.

**Follow-up:** [T-036 — Document ingestion pipeline](../tasks/), [T-041 — Blob containers in Bicep](../tasks/)

---

## 8. Post-hackathon backlog - tasks

| Task | Area | Evaluation | WAR items |
|---|---|---|---|
| T-039 — Production reliability (fallback, circuit breaker, SLOs, chaos, multi-region DR) | Reliability | ~2 weeks | RE:05, RE:08, RE:09, PE:05/06 |
| T-040 — Production RAI (prompt injection, model governance, eval pipeline, red-team) | Responsible AI | ~2 weeks | SE:08, OE:11, PE:06 |
| T-047 — Network isolation (VNet + Private Endpoints + Private DNS) | Security | ~3 days | SE:06 |
| T-048 — Conditional Access + Azure PIM | Security | ~2 days | SE:05 |
| T-049 — WAR easy wins (Defender, tags, legacy auth block, secret rotation, cost alerts) | Security + Cost | ~4 hours | SE:03, SE:08, SE:09, SE:10, CO:04 |
| T-050 — Recovery runbook + DLQ depth alert | Reliability | ~1 day | RE:09 |
| T-051 - Azure Load Testing scenarios | Performance | ~1 week | PE:05/06 |

---

## 9. WAR assessment mapping

Consolidation of target architecture WAR best practices and status in prototype.

| WAR Item | Priority | Target design in [`02-architecture.md`](../02-architecture.md) | Prototype | Post-hackathon |
|---|---|---|---|---|
| SE:03 — Resource tagging | — | Tags on each Bicep module | Partial (env only) | T-049 |
| SE:05 P:100 — Limit high-privilege accounts | 100 | RBAC 5 roles + no shared accounts | Implemented | — |
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

← [02 Architecture](../02-architecture.md) · [04 Action Plan](../04-action-plan.md)
