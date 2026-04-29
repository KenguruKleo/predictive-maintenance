# 04 · Action plan

← [README](./README.md) · [01 Requirements](./01-requirements.md) · [02 Architecture](./02-architecture.md) · [03 Analysis](./03-analysis.md)

> **Purpose:** Live backlog of implementation phase tasks. We update as we work. Each task is tied to a specific gap or requirement.

---

## Contents
1. [Current Focus](#1-current-focus)
2. [Backlog tasks] (#2-backlog-tasks)
3. [Sprint / Iteration plan] (#3-sprint--iteration-plan)
4. [Definition of Done](#4-definition-of-done)
5. [Blockers and risks] (#5-blockers-and-risks)

---

## 1. Current focus

> **April 2026 — Implementation Phase**
> Deadline for final submission: 1st week of May 2026
> Stack: Python 3.11 · Azure Durable Functions · Azure AI Foundry · Cosmos DB · React + Vite

**Currently working:** T-027 (Execution Agent — placeholder impl, full Foundry Agent spec pending) · T-039 (Reliability hardening) · T-040 (RAI observability) · T-061 (operator follow-up guardrails)

T-002 close-out beat should now explicitly mention controlled tool invocation: pre-approval AI prepares drafts only, while backend write actions to QMS/CMMS execute only after human approval. Expand this later with prompt-protection messaging.
`more_info` follow-up retrieval now reuses the latest operator question in backend Azure AI Search queries, so clarification rounds can surface newly requested SOP/manual/BPR evidence without reopening pre-approval tool writes.
Evidence Synthesizer Agent now prepares a compact explicit-evidence brief before Orchestrator for both initial decisions and follow-up questions, helping explanations preserve supported facts, unknowns, and evidence gaps without backend answer hardcoding.

> **ADR-002 - Foundry Connected Agents:** Research Agent + Document Agent are implemented as sub-agents of Foundry Orchestrator Agent.
> Durable calls one activity `run_foundry_agents` — Foundry manages the Research → Document pipeline natively.
> `more_info` loop: Durable accumulates `operator_questions`, runs `run_foundry_agents` again. Foundry manages internal iterations.
> See [02-architecture §8.10b](./02-architecture.md#810b-adr-002-foundry-connected-agents-vs-manual-orchestration).





**Next step:** T-034 (frontend manager/auditor/IT views) → T-001 architecture presentation → T-002 final video

---

## 2. Backlog of tasks

> Execution order in [§3 Sprint plan](#3-sprint--iteration-plan).
> Each task is a separate file `tasks/T-NNN-*.md`.

### Critical (Must-have for finals)

| ID | Task | Gap / Requirement | Priority | Status | Blocks |
|---|---|---|---|---|---|
| T-001 | **[Update architectural presentation](./tasks/T-001-architecture-presentation.md)** — close all gaps, show the real built architecture (Track A, Security, Reliability, RAI, UX, IaC) | Gap #1–6 | 🔴 CRITICAL | 🔜 TODO | T-002 |
| T-002 | **[5-minute final video](./tasks/T-002-final-video.md)** — demo-first app walkthrough + architecture slides | Deliverables | 🔴 CRITICAL | 🟡 IN PROGRESS | final |
| T-020 | **[Cosmos DB — schema + provisioning](./tasks/T-020-cosmos-db.md)** — 8 containers, indexes, seed script | T-023, T-024 | 🔴 CRITICAL | ✅ DONE | — |
| T-021 | **[Mock data seed](./tasks/T-021-mock-data.md)** — equipment(3), batches(20), incidents(30), templates(2) | demo | 🔴 CRITICAL | ✅ DONE | — |
| T-023 | **[Ingestion API](./tasks/T-023-ingestion-api.md)** — POST /api/alerts + context enrichment + Service Bus publish | Gap #3 | 🔴 CRITICAL | ✅ DONE | — |
| T-024 | **[Durable Functions orchestrator](./tasks/T-024-durable-orchestrator.md)** — workflow: enrich→run_foundry_agents→notify→wait (24h HITL)→more_info loop→execute→finalize; ADR-002 | Gap #3 | 🔴 CRITICAL | ✅ DONE | T-029 |
| T-025 | **[Research Agent](./tasks/T-025-research-agent.md)** — Foundry sub-agent (Connected Agents) + MCP + AzureAISearchTool; connects to the Orchestrator Agent as `AgentTool` | Gap #4 | 🔴 CRITICAL | ✅ DONE | T-024 |
| T-026 | **[Document Agent](./tasks/T-026-document-agent.md)** — Foundry sub-agent (Connected Agents) + template fill; confidence gate in `run_foundry_agents.py` | Gap #4, #5 | 🔴 CRITICAL | ✅ DONE | T-024 |
| T-027 | **[Execution Agent](./tasks/T-027-execution-agent.md)** — Foundry Agent + MCP-QMS + MCP-CMMS (placeholder impl in `run_execution_agent.py`, full Foundry Agent spec pending) | — | 🔴 CRITICAL | 🟡 IN PROGRESS | T-028 |
| T-028 | **[MCP servers](./tasks/T-028-mcp-servers.md)** — mcp-sentinel-db, mcp-qms, mcp-cmms (stdio) | — | 🔴 CRITICAL | ✅ DONE | T-025–T-027 |
| T-029 | **[Human approval flow](./tasks/T-029-human-approval.md)** — POST /decision API + waitForExternalEvent | Gap #5 | 🔴 CRITICAL | ✅ DONE | — |
| T-031 | **[Backend API Functions](./tasks/T-031-backend-api.md)** — incidents CRUD, templates, equipment, batches endpoints | Gap #5 | 🔴 CRITICAL | ✅ DONE | T-032 |
| T-032 | **[React frontend — core](./tasks/T-032-frontend-core.md)** — incident list, details, status timeline | Gap #5 | 🔴 CRITICAL | ✅ DONE | — |
| T-033 | **[React frontend — approval UX](./tasks/T-033-frontend-approval.md)** — decision package view + approve/reject/more-info buttons | Gap #5 | 🔴 CRITICAL | ✅ DONE | — |

### Important (Should-have)

| ID | Task | Gap / Requirement | Priority | Status | Blocks |
|---|---|---|---|---|---|
| T-010 | **[Cartoon / animation "Before and After"](./tasks/T-010-cartoon-animation.md)** — descoped for finals, optional post-submission asset | Deliverables | 🟡 LOW | ✅ CLOSED | — |
| T-022 | **[Azure Service Bus setup](./tasks/T-022-service-bus.md)** — alert-queue + DLQ config | Gap #3 | 🟠 HIGH | ✅ DONE | T-023 |
| T-030 | **[Azure SignalR setup](./tasks/T-030-signalr.md)** — negotiate endpoint + notification service + unread notification center contract | Gap #5 | 🟠 HIGH | ✅ DONE | T-033 |
| T-034 | **[React frontend — manager/auditor/IT views](./tasks/T-034-frontend-other-roles.md)** | Gap #5 | 🟠 HIGH | ✅ DONE | — |
| T-043 | **[Agent telemetry + admin incident view](./tasks/T-043-agent-telemetry-admin-view.md)** — App Insights trace delivery + normalized admin timeline per incident | Gap #4, #5 | 🟠 HIGH | ✅ DONE | — |
| T-045 | **[Evidence citations quality + historical evidence links](./tasks/T-045-evidence-citation-quality.md)** — canonical document cards, strict citation contract, excerpt backfill, unresolved evidence state, historical incident linkability | Gap #4, #5 | 🟠 HIGH | ✅ DONE | — |
| T-035 | **[RBAC setup](./tasks/T-035-rbac.md)** — Entra ID app registration, 5 roles, token validation in Functions | Gap #2 | 🟠 HIGH | ✅ DONE | T-031 |
| T-036 | **[Document ingestion pipeline](./tasks/T-036-ingestion-pipeline.md)** — Blob → chunk → embed → AI Search (one-shot script; live triggers out of scope) | Gap #4 | 🟠 HIGH | ✅ DONE | T-037 |
| T-037 | **[AI Search indexes + mock docs](./tasks/T-037-ai-search.md)** — 5 indexes, 9 docs, 117 chunks from HNSW vector search | Gap #4 | 🟠 HIGH | ✅ DONE | — |
| T-041 | **[Bicep IaC templates](./tasks/T-041-bicep-iac.md)** — infra/main.bicep + modules for all resources | Gap #1, #6 | 🟠 HIGH | ✅ DONE | T-042 |
| T-042 | **[GitHub Actions CI/CD](./tasks/T-042-cicd.md)** — build, test, Bicep deploy, Foundry eval pipeline | Gap #1 | 🟠 HIGH | ✅ DONE | finals |

### Nice-to-have

| ID | Task | Gap / Requirement | Priority | Status |
|---|---|---|---|---|
| T-046 | **[Foundry Agent code hardening](./tasks/T-046-foundry-agent-code-hardening.md)** — post-demo cleanup: remove `_infer_known_document()` hardcode, replace keyword-matching `_has_direct_stop_requirement()` with LLM response in Document Agent prompt, add `agent_recommendation: APPROVE | REJECT` to Document Agent output schema, remove startup sleep from Activity, add `RAG_TOP_K`/`RAG_EXCERPT_CHARS` env vars | post-demo | 🟢 LOW | 🔜 TODO |
| T-057 | **[Config externalization + environment portability](./tasks/T-057-config-externalization-portability.md)** — remove hardcoded dev tenant/client/resource IDs and endpoints from runtime code, centralize config for frontend/backend/scripts, add reusable local config templates and fail-fast validation so the app can run in another tenant/subscription without source edits | Reuse, multi-environment support | 🟢 LOW | 🔜 TODO |
| T-058 | **[Frontend unit test coverage](./tasks/T-058-frontend-unit-test-coverage.md)** — add a minimal unit/integration test layer for React auth, role guards, optimistic React Query cache updates, pure analytics/utils logic, and interaction-heavy UI like Command Palette / Approval Panel; keep Playwright smoke as the browser-level layer | Frontend quality, regression prevention | 🟢 LOW | ✅ DONE |
| T-059 | **[Backend test coverage](./tasks/T-059-backend-test-coverage.md)** — expand focused Python backend tests for HTTP triggers, auth/access helpers, and workflow-side utilities; Python pytest already runs in CI, the gap is deeper module-level coverage | Backend quality, regression prevention | 🟢 LOW | ✅ DONE |

### Post-hackathon (Security, Reliability, RAI & Operational Excellence)

> Architecturally documented in §8.15 (Security), §8.17 (Reliability), §8.18 (RAI), §8.16 (Operational Excellence) — we show what we know and designed; implementation after finals.

| ID | Task | Gap / §Arch | Priority | Status |
|---|---|---|---|---|
| T-038 | **[Security layer](./tasks/T-038-security.md)** — Managed Identities for all Functions, Key Vault managed identity auth, retention policy (21 CFR Part 11), data classification tags | Gap #2, §8.15 | 🟡 MEDIUM | 🔜 TODO |
| T-039 | **[Reliability layer](./tasks/T-039-reliability.md)** — fallback mode (degraded manual CAPA), circuit breaker for Foundry calls, latency SLO alerts, chaos experiments baseline | Gap #3, §8.17 | 🟡 MEDIUM | 🔜 TODO |
| T-040 | **[RAI layer](./tasks/T-040-rai.md)** — prompt injection guard (Content Safety Prompt Shield), model versioning + rollback via Foundry governed deployment, formal eval pipeline (groundedness/coherence/relevance), low-confidence escalation UI state | Gap #4, §8.18 | 🟡 MEDIUM | 🔜 TODO |
| T-061 | **[Operator follow-up + document safety guardrails](./tasks/T-061-operator-followup-and-document-safety.md)** — protect `more_info.question` input path and document channel (ingest + retrieval + generation safety filters), including trust metadata and blocked-content audit trace | Gap #2, Gap #4 | 🟡 MEDIUM | 🟡 IN PROGRESS |

| ID | Task | WAR Gap | Priority | Status |
|---|---|---|---|---|
| T-047 | **[VNet / NSGs / Private Endpoints](./tasks/T-047-vnet-private-endpoints.md)** — Function App → Flex Consumption; VNet 10.0.0.0/16 with 2 subnets; NSGs; Private Endpoints for Cosmos DB, AI Search, Service Bus, Storage, Key Vault, Azure OpenAI; Private DNS Zones; `publicNetworkAccess=Disabled` on all PaaS | SE:06 | 🟡 MEDIUM | 🔜 TODO |
| T-048 | **[JIT / Conditional Access](./tasks/T-048-jit-conditional-access.md)** — 4 Entra ID Security Groups; CA Policy: MFA for all, block non-EU, compliant device for IT Admin; Azure PIM eligible Contributor for IT Admin (JIT 1-4h); Lifecycle Workflows for Onboarding/Offboarding | SE:05 | 🟡 MEDIUM | 🔜 TODO |
| T-049 | **[WAR Easy Wins — Security & Cost](./tasks/T-049-war-easy-wins.md)** — Defender for Cloud (SE:10), resource tags (SE:03), block legacy auth (SE:08), KV secret rotation (SE:09), Azure Budget alerts (CO:04) — ~4h, all Bicep/config changes | SE:03/08/09/10, CO:04 | 🟢 LOW | 🔜 TODO |
| T-050 | **[Recovery Procedures Runbook](./tasks/T-050-recovery-runbook.md)** — extend `docs/operations-runbook.md` with 3 recovery scenarios (orchestrator hang, DLQ, Foundry timeout) + DLQ depth Azure Monitor alert in Bicep | RE:09 | 🟢 LOW | 🔜 TODO |
| T-051 | **[Azure Load Testing](./tasks/T-051-load-testing.md)** — 4 Locust scenarios (alert spike 200 RPS, SignalR 200 concurrent, agent E2E 10 parallel, read API 500 RPS); Azure Load Testing resource in Bicep; GitHub Actions CI gate | PE:05/06 | 🟡 MEDIUM | 🔜 TODO |
| T-055 | **[AI pipeline status contract hardening](./tasks/T-055-ai-pipeline-status-contract.md)** — remove the demo workaround and fix the backend status contract: `ingested/analyzing/awaiting_agents` should actually be placed in Cosmos, and `incident_status_changed` / `agent_step_completed` should actually fly through SignalR; cleanup legacy `queued` / `analyzing_agents` in watchdog | Gap #3, UX consistency, T-024/T-030/T-031 | 🟡 MEDIUM | 🔜 TODO |
| T-056 | **[Electron desktop app shell](./tasks/T-056-electron-desktop-app.md)** — multi-platform desktop operator console for production floors, reusing the React UI with native unread badge and SignalR-driven OS notifications | Demo UX, production operator UX, T-030/T-032/T-033 | 🟡 MEDIUM | ✅ DONE |

### New tasks (HITL UX hardening)

| ID | Task | Gap / Requirement | Priority | Status |
|---|---|---|---|---|
| T-052 | **[Editable WO / Audit entry forms](./tasks/T-052-editable-wo-audit-forms.md)** — WO draft and audit entry draft in the approval UI as pre-filled editable fields (operator/QA can change); empty + mandatory in BLOCKED state; other read-only roles; backend payload from verified drafts is transferred to CMMS/QMS | Gap #5, HITL | 🟠 HIGH | 🔜 TODO |
| T-053 | **[Alert feedback loop](./tasks/T-053-alert-feedback-loop.md)** — at Reject: async POST to `ALERT_FEEDBACK_URL` (configurable, optional); payload with `source_alert_id`, `outcome`, `operator_agrees_with_agent`; retry 3×; event in `incident_events`; frontend shows the status in the timeline | SCADA/MES learning | 🟡 MEDIUM | 🔜 TODO |
| T-054 | **[Agent recommendation visibility](./tasks/T-054-agent-recommendation-visibility.md)** — `agent_recommendation: APPROVE\|REJECT` everywhere: badge in ApprovalPanel (above buttons), AI column in IncidentTable + IncidentHistoryPage, AiVsHumanBadge in AuditTrail, agreement rate KPI in RecentDecisions; backend: store in `ai_analysis`, `finalDecision`, `recent_decisions` stats | Demo story, Analytics | 🟠 HIGH | 🔜 TODO |
| T-060 | **[Microsoft Teams app integration](./tasks/T-060-teams-app-integration.md)** — Teams app package with personal/channel tab, Teams SSO, proactive notification bot, Adaptive Card approve/reject/more-info actions wired to the existing decision API, audit metadata for Teams-originated decisions, and automated package create/update/publish flow via Microsoft 365 Agents Toolkit or Graph; Bicep provisions only Azure-side dependencies | Collaboration, HITL, Enterprise adoption | 🟢 LOW | 🔜 TODO |

---

## 3. Sprint / Iteration plan

> Deadline: 1st week of May 2026. Approximately 2 weeks before submission.

### Week 1 (April 17-23) — Infrastructure + Backend + Agents
| Day | Tasks
|---|---|
| April 17 ✅ T-041 · ✅ T-042 · ✅ T-022 · ✅ T-020/T-021 · ✅ T-037 · ✅ T-023 · ✅ T-028 |
| April 18–19 ✅ T-024 (Durable orchestrator + all activities) · ✅ T-025 (Research Agent) · ✅ T-026 (Document Agent) · ✅ T-041 ext (AI Foundry Bicep) |
| April 20-21 T-027 (Execution Agent) · T-029 (Human Approval API) · ✅ T-036 (document ingestion) |
| April 22-23 ✅ T-031 (Backend API) · T-030 (SignalR) · ✅ T-035 (RBAC) |

### Week 2 (April 24-30) — Agents + Frontend + Integration
| Day | Tasks
|---|---|
| April 24-25 T-027 (Execution Agent) · T-029 (human approval API) · T-030 (SignalR) |
| April 26-27 ✅ T-031 (backend API) · ✅ T-035 (RBAC) |
| April 28–29 ✅ T-032 (React core) · ✅ T-033 (approval UX) |
| April 30 T-034 (other frontend roles) · T-040 (RAI layer) · T-043 (agent telemetry admin view) |

### Week 3 (May 1–7) — Polish + Submission
| Subtask |
|---|
| T-034 (other frontend roles) · T-038/039/040 (security/reliability/RAI layers) · T-043 (agent telemetry admin view) · ✅ T-058 (frontend unit test baseline) · ✅ T-059 (backend test baseline) |
| T-001 (update presentation) · T-002 (demo-first video) |
| Final submission |

---

## 4. Definition of Done

The task is considered completed if:

**For architectural changes:**
- [ ] The change is reflected in [02 · Architecture](./02-architecture.md)
- [ ] The corresponding gap is marked as "fixed" in [03 · Analysis](./03-analysis.md#9-progress-fixing-gaps)
- [ ] The corresponding item is marked in [01 · Requirements checklist](./01-requirements.md#10-checklist-compliance-live)
- [ ] Changelog updated in [02 · Architecture §9](./02-architecture.md#9-changelog-architecture)

**For code:**
- [ ] Code in GitHub repo
- [ ] CI pipeline passes
- [ ] Deployed to dev environment
- [ ] The basic smoke test passes

**For demo scenario:**
- [ ] One final scenario with real mock data
- [ ] Decision package shows recommendation + evidence + SOP reference
- [ ] Evidence verification state shows **verified** vs **unresolved** citations separately
- [ ] Human approval flow is demonstrated
- [ ] Audit trail is generated

---

## 5. Blockers and risks

| Blocker/Risk | Description | Mitigation |
|---|---|---|
| _TBD_ | | |

---

## 6. Tasks - details

Each task is described in a separate file in the [`tasks/`](./tasks/README.md) folder:

| ID | File | Note |
|---|---|---|
| T-001 | [tasks/T-001-architecture-presentation.md](./tasks/T-001-architecture-presentation.md) | Close all 6 gaps in the presentation; architecture slide is required for T-002 |
| T-002 | [tasks/T-002-final-video.md](./tasks/T-002-final-video.md) | ⚡ This will decide whether we will win. Detailed video structure, script, DoD |
| T-010 | [tasks/T-010-cartoon-animation.md](./tasks/T-010-cartoon-animation.md) | Descoped for finals; optional storytelling asset after submission |

---

### Useful links for planning:
- Gaps that need to be closed → [03 · Analysis](./03-analysis.md#5-top-6-gaps-for-correction)
- Unfulfilled requirements → [01 · Requirements checklist](./01-requirements.md#10-checklist-compliance-live)
- Architectural changes in-progress → [02 · Architecture §8](./02-architecture.md#8-current-version-in-progress)

---

← [03 Analysis](./03-analysis.md) · [README →](./README.md)
