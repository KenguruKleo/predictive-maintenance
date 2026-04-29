# 01 · Hackathon Requirements

← [README](./README.md) · [02 Architecture](./02-architecture.md) · [03 Analysis](./03-analysis.md) · [04 Action Plan](./04-action-plan.md)

> **Purpose:** Single source of truth for all requirements. Review before every architecture iteration and every deliverable.

---

## Contents
1. [Hackathon — General Requirements](#1-hackathon--general-requirements)
2. [Use Case — LS / Supply Chain (our track)](#2-use-case--ls--supply-chain-our-track)
3. [Environments (Tracks)](#3-environments-tracks)
4. [Evaluation Criteria — Architecture (50 points)](#4-evaluation-criteria--architecture-50-points)
5. [Evaluation Criteria — Use Case (50 points)](#5-evaluation-criteria--use-case-50-points)
6. [Azure WAF Requirements](#6-azure-waf-requirements)
7. [Azure AI Pillar Requirements](#7-azure-ai-pillar-requirements)
8. [Security & Monitoring Requirements](#8-security--monitoring-requirements)
9. [Deliverables by Phase](#9-deliverables-by-phase)
10. [Compliance Checklist (living)](#10-compliance-checklist-living)

---

## 1. Hackathon — General Requirements

| Parameter | Value |
|---|---|
| Name | Microsoft Agentic Industry Hackathon 2026 |
| Organizers | Capgemini (Clemens Reijnen) + Microsoft |
| Goal | Build working agentic solutions on Microsoft AI Platforms |
| Team | 2–7 people |
| Scoring | Architecture (50 points) + Use Case (50 points) = 100 |

**General solution requirements:**
- The solution must use **Microsoft AI Platforms** comprehensively.
- It must demonstrate clear **industry impact** and **quality**.
- The team must choose one **Track (A/B/C/D)**, and architecture must align with it.
- Human-in-the-loop is **mandatory** for GxP/regulated processes.
- The solution is evaluated as an **MVP**, with focus on a concrete scenario.

---

## 2. Use Case — LS / Supply Chain (our track)

### Problem Statement (official hackathon statement)
> In life sciences (pharma/biotech/medical devices), GMP is the set of regulated quality standards that ensure products are consistently made and controlled so they are safe, effective, and meet specifications. Operations teams must keep assets and batches within validated limits while juggling equipment health, preventive maintenance, and strict SOP/BPR compliance, so monitoring assets in real time, detecting early failure signals, optimizing "golden batch" parameters, and identifying potential deviations fast without disrupting production.

### 4 approaches for this use case

| Approach (Track) | Name | Description |
|---|---|---|
| **A — Pro-code ✅ (ours)** | Predictive maintenance / Operations Assistant | Azure AI Foundry multi-agent, streaming SCADA/MES, RAG over SOP/BPR |
| B — Low-code | Maintenance Coach (Copilot Studio) | Teams-based NL-query over SOP, guided checklists, Power Automate |
| C — SaaS | Operations Copilot (Dynamics 365) | Closed-loop work orders, asset/field service, auditable workflows |
| D — Fine-tune | Manufacturing Support (Mistral) | Fine-tune on site alarms, batch deviations, maintenance notes |

### Our approach (Track A) — official description
> Using Microsoft AI Foundry, an Operations Agent orchestrates agents that stream real-time sensor/SCADA data to detect early wear patterns and cross-check them against SOP/BPR "golden batch" limits. Example: a vibration spike on a granulator triggers a predicted bearing failure alert plus a recommended PM plan and deviation-resolution playbook retrieved from validated SOPs. AI Foundry supports it with agent orchestration, RAG over controlled documents, evaluation, and governed deployment.

---

## 3. Environments (Tracks)

### Track A — our choice ✅
**Stack:**
- GitHub (repo, CI/CD, GitHub Actions)
- Azure (full stack)
- Azure AI Foundry (agents, orchestration, RAG, evaluation, governed deployment)
- Microsoft Fabric — **optional** (if needed for the data pipeline)

**What Microsoft provides to Track A teams:**
- GitHub Copilot
- Azure (Cognitive Services + OpenAI enabled)
- Foundry IQ (preview)
- Fabric IQ (preview, optional)

> ⚠️ **Critical requirement:** Track must be **explicitly declared** in the submission. This was missing in the first submission and became Gap #1. See [03 · Analysis Gap #1](./03-analysis.md#gap-1-track-not-declared)

---

## 4. Evaluation Criteria — Architecture (50 points)

| Dimension | Max | Criterion description |
|---|---|---|
| **Clarity & Flow** | 10 | Clear flow: detect → context → agents → approval → action. Agent roles and data sources are visible. Exception paths and runtime logic are defined. |
| **Platform Fit** | 10 | Correct Azure service selection for the problem. Track is declared. Developer/platform setup is shown. GitHub + CI/CD are integrated. |
| **Data / Governance / Security** | 10 | Identity (Entra ID), RBAC for all roles, Key Vault, private endpoints, encryption, data classification, retention policy, controlled access to SOP/BPR/CAPA. |
| **Reliability / Performance / Cost** | 10 | Event queuing, retries, dead-letter handling, fallback, latency SLOs (< 5 min), caching, token budgets, cost controls, model timeout handling. |
| **Scalability / Integration / Provisioning** | 10 | IaC/deployment approach, API contracts, environment topology, repeatable provisioning. Enterprise integrations with MES/SCADA/CMMS/QMS are detailed. |

> Current state: **33/50** → [Analysis details](./03-analysis.md#architecture-dimensions)

---

## 5. Evaluation Criteria — Use Case (50 points)

| Dimension | Max | Criterion description |
|---|---|---|
| **Value & KPI Impact** | 10 | Clear business pain points, evidence-based KPI quantification, measurable impact on regulated processes. |
| **Innovation** | 10 | Differentiated solution (not a basic chatbot/anomaly detector). Thoughtful multi-agent design tied to regulated workflow. |
| **AI Fit** | 10 | AI is an appropriate fit for the problem. Confidence thresholds, evidence gating, separate document/citation verification, hallucination controls, prompt-injection defenses, agent observability. Responsible AI is explicit. |
| **UX Simplicity** | 10 | Concrete operator interface is shown. Approval ergonomics and explainability are present. Sample decision package includes rationale/evidence. |
| **Build–Scale–Reuse** | 10 | MVP is clearly scoped (one asset type, one deviation class, small SOP/CAPA set). Reusable patterns and MCP assets. Production-scale constraints are defined. |

> Current state: **38/50** → [Analysis details](./03-analysis.md#use-case-dimensions)

---

## 6. Azure WAF Requirements

The hackathon explicitly evaluates the **Azure Well-Architected Framework**:

| Pillar | Requirement | Current state |
|---|---|---|
| **Reliability** | Retry strategy, queuing, dead-letter, fallback mode, degraded/manual-only mode | ❌ Missing |
| **Security** | Entra ID, secrets handling, network isolation, encryption, SIEM | ❌ Missing |
| **Cost Optimisation** | Token controls, caching, model routing, cost per event | ❌ Missing |
| **Operational Excellence** | Monitoring, alerting, CI/CD, observability | ❌ Missing |
| **Performance Efficiency** | Latency budgets, throughput, scaling triggers | ⚠️ Partial (< 5 min KPI exists) |

> Full WAF coverage analysis → [03 · Analysis](./03-analysis.md#azure-waf-gaps)

---

## 7. Azure AI Pillar Requirements

| Requirement | Description | Current state |
|---|---|---|
| **Agent Design** | Multi-agent orchestration, clear agent roles | ✅ Good |
| **Grounding / RAG** | Validated SOP/BPR, CAPA history retrieval | ✅ Good |
| **Document & Citation Verification** | Separate post-generation check validates document identity, section claim, and deep link against authoritative retrieved chunks before evidence is shown to user | ⚠️ Partial — backend citation normalization and unresolved-evidence downgrade exist, but the scenario still needs to be demonstrated consistently in UX/demo artifacts |
| **Model Lifecycle** | Evaluation, governed deployment, versioning/rollback | ⚠️ Partial (mentioned, not yet detailed) |
| **Responsible AI** | Confidence thresholds, evidence gating, separate document/citation verification | ⚠️ Partial — confidence gate, citation verification, and explicit evidence synthesis paths exist, but Content Safety and prompt-injection guard are still incomplete |
| **AI Observability** | Agent monitoring, output tracing | ⚠️ Partial — incident-scoped App Insights prompt/response traces are implemented in backend; Cosmos `incident_events` covers only business audit/transcript; dashboards, alerts, and admin retrieval UX are still pending |
| **Prompt Injection Defense** | Content safety, input validation | ❌ Missing |

---

## 8. Security & Monitoring Requirements

The hackathon explicitly evaluates **Microsoft Security & Monitoring**:

- [ ] Identity architecture (Entra ID / Managed Identities)
- [ ] RBAC model (operators / QA / compliance / IT roles)
- [ ] Secrets handling (Azure Key Vault)
- [ ] Network isolation (Private Endpoints, VNet integration)
- [ ] Encryption (at rest + in transit)
- [ ] Data classification and retention
- [ ] SIEM / monitoring (Azure Monitor, Log Analytics)
- [ ] Alerting
- [ ] Audit logging ✅ — already present, but only this part

---

## 9. Deliverables by Phase

### Semi-finals (end of March) — ✅ COMPLETED
- [x] PowerPoint with use case description
- [x] Business process AS-IS → TO-BE
- [x] High-level architecture
- [ ] ⚠️ Track declaration — **NOT CAPTURED** in submission

### Implementation (April 2026) — 🔄 CURRENT
- [ ] Working code in the GitHub repo
- [ ] Azure Foundry agents deployed
- [ ] RAG pipeline (Azure AI Search) configured
- [ ] Integration with mock data sources
- [ ] Security layer (Entra ID, RBAC, Key Vault)
- [ ] Reliability layer (queuing, retry)
- [ ] Responsible AI controls
- [ ] Demo scenario ready (one asset, one deviation class)

### Final submission (first week of May)
- [ ] **5-minute demo video** (detailed requirements below ↓)
- [ ] GitHub repo with full codebase
- [ ] Working implementation

#### 📹 Final video requirements (5 minutes)

> ⚡ **Critically important.** This is the only touchpoint for Capgemini executives and Microsoft judges at the final stage. 5 minutes can determine the winner.

**Mandatory video elements:**
- [ ] Hook: problem + key metric (30-60 min → < 5 min)
- [ ] Cartoon/animation of AS-IS process (without app) — ~60 sec
- [ ] Cartoon/animation of TO-BE process (with app) — ~60 sec
- [ ] Live demo of the working app (one full scenario: SCADA alert → decision package → approval → audit trail)
- [ ] Architecture shown on one slide (Track A + all components)
- [ ] KPI summary and impact
- [ ] Duration: ≤ 5:10 min
- [ ] Language: **English**
- [ ] Subtitles (judges may watch without audio)

**Detailed video plan:** [04 · Action Plan — T-002](./04-action-plan.md#final-video-t-002)

### Finals (second week of May)
- [ ] Top-10 presentation for Capgemini executives + Microsoft

---

## 10. Compliance Checklist (living)

Review at every architecture iteration:

### ✅ Implemented (code or infrastructure exists)
- [x] Strong GMP problem statement
- [x] Multi-agent design on Azure AI Foundry (architecture)
- [x] Human approval step (GxP) — Durable `waitForExternalEvent` mechanism documented (ADR-001)
- [x] Enterprise integrations identified (MES, SCADA, CMMS, QMS)
- [x] Clear KPIs (< 5 min decision time)
- [x] Stakeholders defined
- [x] **Track A explicitly declared** in 02-architecture.md v2.0, with GitHub Actions + Bicep
- [x] **GitHub + CI/CD** — `ci.yml` (lint+test+bicep validate) + `deploy.yml` (push main) are active and green
- [x] **Event Queue** — Azure Service Bus `alert-queue` + DLQ deployed (Bicep, Sweden Central)
- [x] **Cosmos DB** — 8 containers deployed (incidents, incident_events, notifications, equipment, batches, capa-plans, approval-tasks, templates)
- [x] **IaC** — Bicep `infra/main.bicep` + 5 modules, 7 resources deployed
- [x] **App Insights + Log Analytics** — deployed, traces available
- [x] **Mock data** — equipment (3), batches (2), incidents (3), templates (2) in `data/mock/`
- [x] **Concrete equipment scenario** — GR-204, Granulator, Plant-01, Line-2
- [x] **Separate document/citation verification** — backend normalizes `evidence_citations` against authoritative AI Search chunks; if a section is not validated, the citation remains visible as `unresolved` but is not promoted to summary as a verified fact

### 🎨 Designed (documented architecture, implementation not finished)
- [ ] **Entra ID / Managed Identities** — architecture in §8.1, implementation T-035, T-038
- [ ] **RBAC model** — 5 roles defined (§8.1), implementation T-035
- [ ] **Azure Key Vault** — architecture in §8.1, not deployed yet, T-038
- [ ] **Retry / DLQ / Fallback** — Service Bus DLQ deployed, retry logic in Durable orchestrator T-024, T-039
- [ ] **Responsible AI** — confidence gate + evidence schema in §8.3, implementation T-040
- [ ] **Prompt injection defenses** — described in §8, implementation T-040
- [ ] **Content Safety** — architecture documented in cross-cutting concerns, implementation T-040
- [ ] **Agent observability** — incident-scoped prompt and response traces implemented in backend, current frontend can only read `incident_events` business timeline, and dedicated admin retrieval / normalization is still pending (T-040, T-043)
- [ ] **RAG for SOP/BPR/CAPA** — 4 AI Search indexes documented (§8.5), AI Search not yet deployed, T-037
- [ ] **Operator UI** — wireframe in T-033, React project not created, T-032
- [ ] **Sample decision package** — schema in §8.3, implementation T-026

### 🔧 In development (implementation — April 2026)
- [ ] Private Endpoints / VNet — implementation T-038
- [ ] Latency SLOs — implementation during development (T-039)
- [ ] Token budgets / caching — T-039 nice-to-have
- [ ] Model versioning / rollback — T-040
- [ ] All implementation tasks T-020 → T-042 (see [04 · Action Plan](./04-action-plan.md))

---

← [README](./README.md) · [02 Architecture →](./02-architecture.md)
