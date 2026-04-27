# T-001 · Update the architectural presentation

← [04 · Action plan](../04-action-plan.md) · [02 · Architecture](../02-architecture.md) · [03 · Analysis](../03-analysis.md)

| Field | Value |
|---|---|
| **ID** | T-001 |
| **Priority** | 🔴 CRITICAL |
| **Status** | 🔜 TODO |
| **Dependencies** | None (first task) |
| **Blocks** | T-002 (the video needs an updated architecture slide) |

---

## Goal

Update the architectural presentation (PowerPoint/slides) so that:
1. Close all 6 gaps from the triage report
2. Display the **real built architecture** (not just the concept)
3. Explicitly declare **Track A**
4. To be ready as a slide for the final video [T-002](./T-002-final-video.md)

---

## Gaps that we close

| Gap | Details | What we add to the presentation
|---|---|---|
| **#1 Track** | Track A is not declared | Explicit label "Track A: GitHub + Azure + Azure AI Foundry" on the title page and architecture diagram |
| **#2 Security** | Identity, RBAC, Key Vault, network — absent | Security layer: Entra ID, Key Vault, Private Endpoints/VNet, RBAC roles + **PIM JIT** (Contributor 1–4h), **Conditional Access** (MFA + geo-block), **Microsoft Defender for Cloud**, **Azure Policy** (publicNetworkAccess=Disabled, allowed regions) |
| **#3 Reliability** | Queuing, retry, DLQ, fallback — absent | Service Bus between SCADA→Functions, retry/DLQ marks, Fallback mode + **specific SLOs**: E2E < 120s, P95 API < 500ms, DLQ=0 + **Chaos Studio** scenarios + **multi-region DR** (Cosmos geo-redundancy, AI Search replica) |
| **#4 RAI** | Confidence thresholds, content safety, observability | RAI layer: Content Safety + Prompt Shield, Confidence Gate (three states: NORMAL / LOW_CONFIDENCE / BLOCKED), **Evidence Verification Pass** (backend independently verifies citations, verified vs unresolved), Observability + **Foundry Eval Gate** as CI/CD deployment gate |
| **#5 UX** | Operator UI is not defined | React portal: notification bell, unread queue, approval package with editable WO/audit drafts, consistent status color language + **BLOCKED state** (empty forms when agent fails) + **operator_agrees_with_agent** tracking |
| **#6 IaC** | There is no deployment layer | GitHub Actions CI/CD + IaC (Bicep) + **Foundry Eval Gate** in deploy.yml (blocks promotion if Groundedness/F1 < baseline) |

> Details of each gap → [03 · Analysis](../03-analysis.md#5-top-6-gaps-for-correction)

---

## The structure of the updated presentation

### Slide 1: Title
```
Deviation Management & CAPA in GMP Manufacturing
Operations Assistant — Sentinel Intelligence
Track A: GitHub + Azure + Azure AI Foundry
```

### Slide 2: Problem Statement
- AS-IS process (30–60 min, manual, risks)
- KPI targets (< 5 min, auto-drafted, GMP compliant)

### Slide 3: Solution Overview
- High-level flow: Detect → Context → Agents → Approve → Execute
- Stakeholders

### Slide 4: Architecture Diagram (main)
Updated chart with all layers:
```
┌─────────────────────────────────────────────────────────┐
│ GITHUB + CI/CD (Track A) │ ← new
│  GitHub Actions: ci.yml | deploy.yml | load-test.yml    │
│  IaC: Bicep modules | Foundry Eval Gate (blocks deploy) │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│ SECURITY LAYER │ ← new
│  Entra ID (MSAL, App Roles) | Key Vault (90-day rot.)   │
│  VNet + Private Endpoints | Managed Identity            │
│  PIM JIT (1–4h Contributor) | Conditional Access (MFA)  │
│  Microsoft Defender for Cloud | Azure Policy            │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│ RELIABILITY LAYER │ ← new
│  Service Bus DLQ | Durable retry (3×, exponential)      │
│  Fallback/degraded mode | Circuit breaker               │
│  SLO: E2E <120s | P95 API <500ms | DLQ=0               │
│  Chaos Studio scenarios | Multi-region DR               │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ LEVEL 1 — Durable Functions (Workflow Orchestrator) │ ← two-level orchestration
│  create_incident → enrich_context → run_foundry_agents  │
│  ⏸ waitForExternalEvent("operator_decision") / 24h timer│
│  approved → run_execution_agent | rejected → close      │
│  more_info → re-run (max MAX_MORE_INFO_ROUNDS)          │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│ LEVEL 2 — Azure AI Foundry (AI Orchestrator) │ ← two-level orchestration
│  Orchestrator Agent                                     │
│   ├─ Research Agent (RAG ×5 + MCP sentinel-db)         │
│   └─ Document Agent (confidence gate 0.7 + ev.verify)  │
│  Execution Agent (MCP-QMS + MCP-CMMS after approval)   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  INTEGRATION LAYER (pluggable MCP servers)              │
│  mcp-sentinel-db | mcp-qms (SAP QM / TrackWise)        │
│  mcp-cmms (SAP PM / IBM Maximo)                        │
│  RAG: SOPs | BPR (NOR/CPP) | GMP | Manuals | History   │
│  Azure AI Search HNSW vector + semantic ranker          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ RAI + OBSERVABILITY LAYER │ ← new
│  Content Safety + Prompt Shield | Confidence Gate       │
│  NORMAL / LOW_CONFIDENCE / BLOCKED states               │
│  Evidence Verification Pass (verified vs unresolved)    │
│  App Insights FOUNDRY_PROMPT_TRACE | Foundry Eval Gate  │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│ OPERATOR UX (React + Azure Static Web Apps) │ ← new
│  Notification bell | Unread queue | Decision package    │
│  Editable WO/audit drafts | BLOCKED: manual fill        │
│  [Approve] [Reject] [More info] | SignalR real-time      │
│  Role views: operator / qa-manager / auditor / it-admin │
└─────────────────────────────────────────────────────────┘
```

### Slide 5: Data Sources & Integrations
- SCADA, MES, BPR, SOP, CMMS, QMS

### Slide 6: KPI Impact
- Before/After table

---

---

## 📋 Notes: Structured presentation in layers

The idea is to show the application not only as "here's a diagram", but to guide the audience through **6 layers**, each of which answers its own question.

---

### Layer 0: Infrastructure / Deployment Topology
*"What and where is spinning?"*

- Show what is in Azure that can be kept locally (for example, MCP servers as a sidecar or local Docker)
- Call it **Deployment Topology** or **Infrastructure Overview**
- Key components: Azure Functions, Cosmos DB, AI Search, Service Bus, Azure AI Foundry, Static Web App, SignalR
- Mark the cloud/on-premise boundary if there is one (SCADA, MES usually locally, agents — cloud)

---

### Layer 1: Functional Layer
*"How does it work and why?"*

- Go through the end-to-end flow: Sensor → Alert → Orchestrator → Agents → Approval → Execution
- Explain **why** Durable Orchestrator (stateful, retry, long-running), **why** individual agents (Research / Document / Execution), why Human-in-the-loop
- Show that the system DECIDES: reaction time from 30–60 min → < 5 min, GMP-compliant documents, audit of each step
- Show "failures" without a system (manual coordination, errors in documents, missed SLAs)
- **Innovation differentiator** is neither a chatbot nor an anomaly detector. This is the first class of solutions: **multi-agent regulated workflow**, where each agent has its responsibility (Research grounds, Document synthesizes, Execution performs), and MCP servers are a pluggable compliance layer. An organization can connect its CMMS or QMS without changing a single line of agent logic. A new class of solutions for GMP-regulated industries

> 📌 Slide pitch: *"Not a chatbot. Not an anomaly detector. A multi-agent regulated workflow — built for GMP from the ground up."*

---

### Layer 2: Security Layer
*"How do we protect data and access?"*

- **Entra ID** — authentication and authorization everywhere: frontend, API, agents, MCP servers
- **RBAC** — the operator sees only his incidents, the manager — summary, the auditor — logs. No extra data
- **No direct access to DB and documents** — only via API/MCP layer. This is a key design decision:
- Agent cannot "do SQL injection" or "flush all Cosmos"
- We monitor every request: who is asking, how much, within what limits
- You can limit, log, block suspicious activity even from AI
- **Key Vault** — all keys, connection strings, secrets on the server. A person does not have access to them, the frontend does not know anything about backend credentials at all. **90-day rotation policy** + Event Grid trigger → auto-notification IT Admin
- **Managed Identity** — Azure services communicate with each other without passwords in the code
- **Private Endpoints / VNet** — Cosmos DB, Service Bus, AI Search are not exposed to the public internet; traffic goes through Azure's internal network. `publicNetworkAccess = Disabled` after PE activation
- **Azure PIM (Privileged Identity Management)** — JIT-eligible Contributor for IT Admin: activation for 1–4h with justification, after which access is automatically withdrawn. Constantly active: operator, auditor (read-only). Even the IT Admin does not have permanent privileged access — he gets it only when needed and leaves a full audit trail
- **Conditional Access (Entra P2)** — MFA is mandatory for everyone; blocking of non-EU countries (GMP pharma compliance); require compliant device for IT Admin
- **Microsoft Defender for Cloud** — threat protection for App Service, Key Vault, Cosmos DB, Storage. Automatic detection of abnormal behavior
- **Azure Policy** enforcement — `publicNetworkAccess = Disabled` is mandatory on all PaaS resources, allowed regions enforced. Any deviation is blocked automatically
- **Encryption** — data is encrypted at rest (Cosmos DB, Blob) and in transit (TLS 1.2+); keys in Key Vault
- **Data classification & retention** — SOP/BPR documents have a separate access class; audit logs — immutable retention policy for compliance with 21 CFR Part 11

> 📌 Slide pitch: *"Security isn't an afterthought — it's structural. Every layer enforces it."*

---

### Layer 3: Integration Layer
*"How do we connect to external systems?"*

- **MCP servers** — each integration (CMMS, QMS, Sentinel DB, AI Search) is a separate small server
- Argument: an organization can replace ITS CMMS without affecting the agent logic
- Argument: new data source = new MCP server, the rest does not change
- Call it **"pluggable integration layer"**
- **RAG vs MCP — two different access patterns (architectural maturity):**
- **RAG** ​​(Azure AI Search, HNSW vector + semantic ranker) — for documentary knowledge: SOPs, BPR product specs (NOR/CPP ranges), GMP policies, Maintenance manuals, Historical incidents. Knowledge rarely changes, needs semantic similarity, needs chunking and embedding. Indexes: `idx-bpr-documents`, `idx-maintenance-docs`, `idx-incident-history`
- **MCP** — for operational data: equipment parameters (PAR — validated values), active incident records, QMS/CMMS records, real-time batch status. The data is structured, changes frequently, and requires accurate lookup. MCP gives the agent read/write access with full control
- **Conclusion:** the system responds to "know" and "find" with different mechanisms depending on the type of knowledge - this is not overengineering, this is the correct architectural solution
- **Azure AI Foundry** — allows you to reconfigure the agent for a specific organization through the system prompt or tool configuration, without changing the code
- Reusability: the same orchestrator + agents framework can be deployed for another industry (other MCP servers, other prompts — the same pipeline)
- **MVP scope is limited to data only:** but it is a **production-ready system** in everything else. To scale, you only need to connect new lightweight MCP servers to access new data (new CMMS, new QMS, new SOPs in AI Search index). No changes to agents, orchestrator or CI/CD pipeline. The architecture **does not change**. It is "Build–Scale–Reuse" by design

> 📌 Slide pitch: *"The process is universal. The integrations are configurable."*

---

### Layer 4: Reliability Layer
*"What happens if something goes wrong?"*

- **Service Bus queues** — SCADA and external systems drop alerts into the queue and release. No one is waiting or blocked. We process incidents at our own pace, even if a wave of alerts comes in at the same time
- **Durable Functions** — stateful orchestration by design. Human-in-the-loop approval can wait for hours or even several days - the function "sleeps" and wakes up when a person has responded. There are no HTTP request timeouts or chat limits. **3× retry with exponential backoff** at each activity step
- **Escalation** — if the operator has not confirmed within the allotted time, the system automatically escalates to the next level (manager, etc.). The deadline will not be passed silently
- **Push Notifications** - SignalR delivers real-time status updates. Relevant people see the new task immediately, without polling and without "I didn't notice the email"
- **Dead Letter Queue** — if processing fails after all retries, the message is not lost, but goes into the DLQ with full context for diagnosis and manual restart. **DLQ depth = 0** as operational SLO, Azure Monitor Alert when violated
- **Circuit breaker** — if the external service (QMS/CMMS) returns 5xx 3+ times in a row, the circuit breaker opens for 60s; subsequent fail-fast calls without a queue. Protection against cascading failures
- **Specific SLOs:**

| Metric | Target |
  |---|---|
  | E2E (SCADA alert → decision package ready) | < 120s |
  | P95 API read (incidents list, GET) | < 500ms |
  | DLQ depth | = 0 (alert if > 0) |
  | Foundry agent timeout | 90s (hard limit) |
  | SignalR delivery latency | < 2s |

- **Chaos Studio** — monthly fault injection scenarios: Foundry 429 (rate limit), Service Bus outage, Cosmos DB throttling. Confirms real behavior in production-like conditions, not only unit tests
- **Multi-region DR** — Cosmos DB with geo-redundancy (Sweden Central primary + North Europe secondary), AI Search replica. RPO < 1h, RTO < 4h. If the primary region is down, failover is automatic. This is not a buzzword, this is a specific Cosmos DB configuration with a switchover policy
- **Model timeout handling** — if the Foundry agent call did not return a response after the timeout window, the Durable orchestrator catches the exception, logs the timeout event and transfers the incident to manual review without crashing the entire workflow
- **Token budgets / Cost controls** — each incident has a limited token budget; gpt-4o-mini for Research (fact collection), gpt-4o for Document (synthesis and draft). Pay-per-execution: no alerts - no costs. The cost of one incident is logged (`incident_total_tokens`, `incident_cost_usd`)
- **Degraded / manual-only mode** — if the AI ​​pipeline is unavailable (Foundry rate limit, AI Search down, network partition), the system goes into degraded mode: the operator receives a SignalR notification about the degraded state, the incident is opened with an empty decision package for manual filling. No loss incidents

> 📌 Slide pitch: *"The system doesn't fail silently. It queues, retries, escalates — and always tells someone."*

---

### Layer 5: Audit & Compliance Layer
*"Who did what and when?"*

- Every action of the agent, every approval, every status change is logged in Cosmos DB with timestamp and user identity
- **Audit pages** — separate views:
- **Internal IT / Admin** — system settings, configuration viewing, role management
- **Internal Audit** — complete incident trail: from alert to completed CAPA, who confirmed which documents
- **External Audit / Regulatory** — read-only view for GMP inspectors: immutable logs, signed approvals
- The external auditor does not have access to operational data — only to the audit trail
- **One-click CSV export** — the auditor downloads a complete list of incidents to CSV with one click for inspection-readiness review and offline analysis. Zero requests to IT during the inspection
- This allows you to **pass 21 CFR Part 11 / GMP inspection** without "show us the database"

---

### Layer 6: Observability & Ops Layer
*"How do we know that the system is healthy?"*

- **Azure Monitor + Application Insights** — latency, error rates, agent execution times, number of escalations
- **Health dashboards** for the internal IT team — you can see where the queue is growing, where the agent is slow
- **Alerting** — if the agent did not respond in N seconds → automatic fallback to the manual process
- **Distributed tracing** — each incident has a correlation ID, you can track the entire path from alert to closure
- **Agent telemetry by incident (Admin view)** — a separate page for IT Admin/QA: chronology of agent -> sub-agent -> tools calls for a specific incident (run IDs, duration, retries, errors, tokens, estimated cost). This is critical for tuning prompt/tool ​​configuration and post-mortem analysis
- **Model lifecycle / Foundry Evaluation** — the evaluation pipeline in GitHub Actions runs Foundry eval after each deploy: checks the quality of agent responses to test incidents and compares them to the baseline. If the eval score decreases, deploy is blocked. Versioning and rollback of agents — through Foundry governed deployment. No "quiet" model degradations in production

---

### Layer 7: Responsible AI Layer
*"How do we control AI behavior and prevent it from inventing?"*

> This is a separate scoring dimension in the assessment — **AI Fit (10 points)**. Must be clear, not buried in other layers.

- **Confidence gate — three clear states:**
- `NORMAL` (score ≥ 0.7) — the recommendation is displayed in full, the operator decides
- `LOW_CONFIDENCE` (0.4 ≤ score < 0.7) — **warning banner** + mandatory comment from the operator + possibility to request "More Info". **Operator ALWAYS decides for himself** - LOW_CONFIDENCE does not mean automatic escalation. Escalation occurs ONLY after the `HITL_TIMEOUT_HOURS` timeout (24h), if no decision is made
- `BLOCKED` (score < 0.4 or AI pipeline failed) — AI pipeline failed; the operator receives an **empty decision package** for manual filling + an explicit "AI unavailable" banner. Graceful degradation — the incident is not lost
- This is not just a "show/hide button" — it is an explicit RAI policy with clear semantics for the regulatory mid in the GxP context
- **Evidence Verification Pass** — after the Document Agent completes the draft, the backend **independently** verifies each citation against AI Search (does not trust agent-generated citations blindly):
- Each citation receives the status: `verified` (found in the index, the text matches) or `unresolved` (not confirmed)
- Decision package shows these two lists **separately** — the operator immediately sees what is a fact that needs QA review
- This is a strong RAI differentiator: AI cannot pass an unverified link as a verified one
- **Evidence gating** — each recommendation in the decision package has a link to a specific SOP/BPR document and a specific parameter. If there is no source, the recommendation is blocked
- **Hallucination controls** — RAG over validated documents (AI Search); agent responds only based on verified SOP/CAPA, not "off the top of my head"
- **Prompt injection defense** — input text from SCADA/MES undergoes validation and sanitization; The Content Safety API filters malicious or manipulative content
- **Content Safety + Prompt Shield** — Azure AI Content Safety checks the entry and exit of agents; blocks abnormal requests and prompt injection attempts
- **Human-in-the-loop as a RAI mechanism** is not just a convenience, but a requirement for GxP: AI suggests, a person decides and takes responsibility. Each decision is signed by a specific person
- **Foundry Eval Gate (CI/CD deployment blocker)** — there is an explicit eval step in `deploy.yml` GitHub Actions: if Groundedness score or F1 falls below baseline → promotion is blocked. This is not an observability detail — it is a production safeguard that protects against regression in the quality of AI between deployments
- **Agent observability** — all agent calls are traced in App Insights (`FOUNDRY_PROMPT_TRACE` custom event): which prompt, which model, which response, how many tokens, confidence score. Post-facto analysis is possible
- **Pipeline exception contract** — explicit exception paths are defined: if Research Agent returns an empty result → Document Agent receives `no_grounding` status and blocks the recommendation; if confidence gate fails → the incident goes to `needs_review` instead of automatic approve. Every exception is logged and traced

> 📌 Slide pitch: *"The AI suggests. The human decides. The system proves it."*

---

### Layer 8: UX / Operator Experience
*"What does it look like for a person?"*

> **UX Simplicity (10 points)** is a separate scoring dimension. You need to show a specific UI, not a wireframe.

- **Operator dashboard** — a list of active incidents with priorities, statuses, and escalation timers. One click → details
- **Decision package** — on the approval screen, the operator sees: what happened, what data from SCADA, what equipment AI recommends and FROM WHICH documents (with links), confidence score, previous CAPA for similar cases
- **BLOCKED state (graceful degradation)** — if the AI ​​pipeline failed (score < 0.4, Foundry unavailable, etc.), the operator receives an **empty decision package** with an explicit "AI pipeline unavailable" banner. WO/audit entry forms are open for **manual completion**. The incident is not lost, the audit trail is maintained, everything is stored in Cosmos DB as usual
- **Approval ergonomics** — [Approve] / [Reject] / [More Info] with one click; comment field (required for LOW_CONFIDENCE); the signature is recorded automatically via Entra ID (who + when)
- **operator_agrees_with_agent tracking** — when Approve, the boolean flag `operator_agrees_with_agent` is fixed. With Reject, the reason for rejection is stored and **asynchronously sent as a feedback signal to SCADA/MES** (false positive learning loop). This is not only an audit trail - it is a mechanism for improving the quality of alerts over time
- **Explainability** — the operator can expand "why the AI ​​decided that way" and see a specific parameter from the SOP and deviations from the golden batch. Verified vs unresolved citations are shown separately
- **Real-time updates** — the status changes on the screen without rebooting (SignalR push); you can see where each incident in the pipeline is now
- **Operator awareness** — header bell shows unread count, dropdown opens unread queue, and new pending incidents are highlighted in the left rail even if the operator is currently on another screen
- **Consistent status color language** — the same color scheme for `pending_approval`, `escalated`, `approved`, `rejected`, `closed` is used in dashboard, sidebar, manager queue, badges and status history timeline. This reduces the cognitive load and allows the user to instantly read the status of the incident without re-reading the text
- **Role-based views** — operator, manager, QA, auditor — everyone sees their context, without unnecessary noise
- **Command Palette (⌘K)** — quick navigation between sections without the mouse, like in VS Code or Linear. Keyboard-first UX is a sign of an enterprise-grade product
- **Infinite scroll / one-screen UX** — all tables (incidents, history, templates) without classic pagination: the operator sees the full list and can quickly find what he needs without unnecessary clicks

> 📌 Slide pitch: *"Every screen answers one question: what do I need to do right now, and why?"*

---

### Layer 9: Business Value & KPI
*"Why is this at all?"*

> **Value & KPI Impact (10 points)** is the first Use Case dimension. It is better to start or end the presentation with this. We need specific numbers, not just "faster and better".

- **AS-IS pain points:**
- Deviation detection: manually during a bypass or after a change — 30–60 min delay
- CAPA document: 2–4 hours of assembly from several systems (SCADA prints, SOP PDF, Excel CAPA log)
- GMP audit prep: 2-3 days of preparation for one inspection request
- Human factor: missed escalations, wrong version of SOP, unsigned approval

- **TO-BE KPI targets:**
- Detection → Decision package ready: **< 5 min** (now 30–60 min)
- Manual CAPA drafting: **eliminiated** (AI generates draft, human approves)
- Audit prep: **real-time** (audit trail is always ready, one click)
- Missed escalations: **0** (automatic escalation + push notifications)

- **Regulated context** is not just efficiency. In GMP, every delay with CAPA = risk of regulatory violation, batch rejection, or recall. Not only is the system faster, it's document compliant by default

> 📌 Slide pitch: *"From 60 minutes of manual guesswork to 5 minutes of evidence-based decision — with full GMP traceability built in."*

---

### Coverage of scoring dimensions — final state

| Scoring dimension | Where in the notes | Condition |
|---|---|---|
| **Clarity & Flow** (10) | Layer 1: end-to-end flow + exception contract | ✅ Covered |
| **Platform Fit** (10) | Layer 0: deployment topology + Track A; Layer 6: CI/CD + Bicep IaC | ✅ Covered |
| **Data / Governance / Security** (10) | Layer 2: Entra ID, RBAC, Key Vault, VNet, encryption, 21 CFR | ✅ Covered |
| **Reliability / Performance / Cost** (10) | Layer 4: Service Bus, retry, DLQ, SLO, token budgets, timeout, degraded mode | ✅ Covered |
| **Scalability / Integration / Provisioning** (10) | Layer 3: MCP pluggable layer, API contracts, MVP → production scale | ✅ Covered |
| **Value & KPI Impact** (10) | Layer 9: AS-IS/TO-BE figures, GMP regulated context | ✅ Covered |
| **Innovation** (10) | Layer 1: multi-agent regulated workflow differentiator | ✅ Covered |
| **AI Fit** (10) | Layer 7: confidence gate, evidence gating, hallucination controls, RAI, pipeline exceptions | ✅ Covered |
| **UX Simplicity** (10) | Layer 8: decision package, approval ergonomics, role-based views, Command Palette | ✅ Covered |
| **Build–Scale–Reuse** (10) | Layer 3: MVP scope + production-ready architecture + MCP reuse | ✅ Covered |

---

> 💡 **General pitch for the entire presentation:**
> *"We didn't just automate the process — we built a system that is secure by design, reliable by default, integrates without lock-in, is audited at every step, and scales without architecture changes."*

---

## Definition of Done

- [ ] Track A is clearly indicated in the presentation
- [ ] Architecture diagram updated with all 6 gap fixes
- [ ] **Two-level orchestration is shown on the Architecture Diagram** (Durable Functions Level 1 + Foundry Level 2, with a clear division of responsibilities)
- [ ] Security layer is present (Entra ID, Key Vault, VNet, RBAC)
- [ ] **Azure PIM (JIT)**, **Conditional Access** and **Microsoft Defender for Cloud** are present in the Security layer
- [ ] Reliability layer present (Service Bus, retry, DLQ)
- [ ] **Specific SLO numbers** are present in the Reliability layer (E2E < 120s, P95 API < 500ms, DLQ = 0)
- [ ] **Chaos Studio** and **multi-region DR** are specified in the Reliability layer
- [ ] RAI layer present (Content Safety, Confidence Gate, Monitor)
- [ ] **LOW_CONFIDENCE behavior correctly described** — banner + mandatory comment, operator decides himself; escalation ONLY by timeout
- [ ] **Evidence Verification Pass** is present in the RAI layer (verified vs unresolved citations, backend-independent check)
- [ ] **Foundry Eval Gate** shown as CI/CD deployment blocker (in deploy.yml, blocks promotion)
- [ ] **RAG vs MCP access pattern** is described in the Integration layer (documentary knowledge → RAG; operational data → MCP)
- [ ] **BLOCKED state** is described in the UX layer (empty forms in case of AI pipeline failure)
- [ ] **operator_agrees_with_agent** tracking + rejection feedback loop to SCADA/MES mentioned
- [ ] Operator UX is shown (specific channel)
- [ ] GitHub + CI/CD present
- [ ] The presentation is approved by the team
- [ ] Architecture slide ready for installation in [T-002](./T-002-final-video.md)
- [ ] [02 · Architecture](../02-architecture.md) updated accordingly (Changelog §9)
- [ ] [03 · Analysis](../03-analysis.md#9-progress-correction-gaps) — all gaps are marked as closed
- [ ] [01 · Requirements checklist](../01-requirements.md#10-checklist-compliance-alive) updated

---

← [04 · Action Plan](../04-action-plan.md)
