# T-002 · Final video (up to 10 minutes)

← [04 · Action Plan](../04-action-plan.md) · [01 · Requirements §9](../01-requirements.md#9-deliverables-by-phases)

| Field | Value |
| --- | --- |
| **ID** | T-002 |
| **Priority** | 🔴 CRITICAL |
| **Status** | 🟡 IN PROGRESS |
| **Dependencies** | [T-001](./T-001-architecture-presentation.md) (architecture slides), live demo (working application) |
| **Deadline** | 1st week of May 2026 |

---

## Why this is critical

> ⚡ **Up to 10 minutes = decision about the top 10.**
> Judges should see a **working demo**, not just a conceptual pitch. Therefore, we build the video around the real product, not around the animation. We use the extra time to show depth — editable AI drafts, AI vs Human agreement, feedback loop.

---

## Video structure (up to 10 min = ~600 sec)

```text
[00:00–00:15]  HOOK
               Problem + value claim

[00:15–02:55]  LIVE DEMO — Operator workflow
               Dashboard (KPI cards, equipment health grid, Workflow Pipeline)
               → incident list AI Rec. column → bell → incident detail
               → summary → recommendation badge → evidence verification
               → Need More Info loop / preserved transcript
               → batch disposition → CAPA actions
               → editable WO draft + audit entry draft (T-052)
               → approval actions → execution state (WO task + audit record created)
               → incident history + Workflow Pipeline tracking

[02:55–03:50] CONFIDENCE GATE - three states
               LOW_CONFIDENCE banner + mandatory comment
BLOCKED state: empty decision package, manual filling

[03:50–05:15]  QA MANAGER VIEW + AUDIT + ADMIN
               Escalation queue → continue review
               Recent Decisions: AI Rec. badge, agreement KPI, infinite scroll (T-043, T-054)
History filters + CSV export (with AI rec column) + telemetry + token usage

[05:15–06:30]  ARCHITECTURE SLIDE
               Track A, Durable orchestration, Foundry agents, MCP,
               Service Bus, Cosmos DB, AI Search, SignalR, Entra ID / RBAC
Alert feedback loop to SCADA/MES when Reject (T-053)
**Watchdog recovery:** Timer Trigger (5 min) detects stuck/orphaned
orchestrators → auto-requeue to Service Bus without losing business context

[06:30–07:15]  IMPACT + CLOSE
KPI + three-state confidence gate differentiator + GxP audit trail + closing

[07:15–07:45]  OPTIONAL ADD-ON — DESKTOP OPERATIONS SURFACE
               Show the Electron app running on the desktop
               Native unread badge + OS notification from a new incident
               Why this matters: production operators need more than a web tab
               Future extension: Teams / collaboration notification channel
```

---

## What exactly should the demo prove

- **Working product** — judges do not see a mock concept, but real role-based screens and incident states
- **Document & citation verification** — AI uses RAG to retrieve relevant data and documents, but we still verify that every cited document and reference anchor actually exists before showing it as trusted evidence. Therefore, in the decision package evidence is clearly divided into **Verified** and **Unresolved**. This closes the requirement for separate document/citation verification
- **Human-in-the-loop** — the operator can approve / reject / ask for more info; without a human decision, the workflow does not complete the CAPA execution
- **Iterative follow-up loop** — the operator can request additional information several times, and the entire dialogue is saved in an incident both for the next reviewer and for the audit trail
- **Editable AI drafts** (T-052) — operator edits WO and audit entry draft before Approve; in the BLOCKED state, the forms are empty and **required** - this is a GxP differentiator: the person confirms not just "approve", but the specific content of the document
- **AI vs Human agreement** (T-054) — `AgentRecommendationBadge` and `AiVsHumanBadge` everywhere: in the list of incidents, in Recent Decisions, in CSV export. Governance becomes measurable
- **Closed-loop actionability** — decision package shows batch disposition, CAPA actions, work order draft and audit entry draft even before the execution step
- **Post-approval execution visibility** — after Approve the CAPA plan goes into execution: the system creates a work order task and an audit record, and this transition is visible both in the incident itself and in the **Workflow Pipeline** on the main screen
- **RBAC** — different roles are seen by different surfaces: Operator, QA Manager, Auditor, IT Admin
- **Three-state confidence gate** — NORMAL / LOW_CONFIDENCE (banner + mandatory comment) / BLOCKED (empty forms + manual fill)
- **Real-time UX** — notification bell, unread state, escalation queue, consistent status colors across views, plus Electron native badge/OS notifications for desktop operators
- **Long-running autonomy** — workflow can wait 24h or more without losing state, with escalation to QA
- **Traceability & observability** — status history, telemetry page, audit export, incident timeline, AI recommendations in CSV
- **Operational oversight** — manager surfaces show AI recommendation, AI confidence, response time, human override, agreement rate KPI
- **Infinite scroll** (T-043) — Recent Decisions uploads more records when scrolling — shows that the system scales to large volumes of data

---

## Complete inventory of what can be shown on the demo

### Operator

- Operations Dashboard with active incidents and status-based prioritization
- Incident Analytics table with period × status counts
- **Incident list — AI Rec. column** with `AgentRecommendationBadge` (APPROVE / REJECT label with color) (T-054)
- Notification bell with unread badge
- Sidebar with unread incident queue, timestamps, equipment, unread dot
- Footer live/offline indicator + active incident count
- Incident summary: equipment, batch, stage, parameter, measured value, limits, duration, severity
- Parameter excursion block
- **`AgentRecommendationBadge`** in decision package (APPROVE / REJECT icon + label) (T-054)
- AI recommendation: risk, confidence, classification, batch disposition, recommended action, root cause
- Evidence citations: document type, verified/unresolved status, relevance score, unresolved reason, deep link
- Batch Release Recommendation + disposition conditions
- CAPA actions list
- **Editable Work Order draft form** — the operator edits the fields (equipment, type, priority, title, description) (T-052)
- **Editable Audit entry draft form** — the operator edits the fields (deviation type, batch reference, action taken, comments) (T-052)
- **BLOCKED state: empty forms, mandatory to fill, Approve disabled to fill** (T-052)
- Approve / Reject / Need More Info controls
- Agent conversation transcript / multi-turn follow-up Q&A preserved for operator and audit
- Low confidence banner when applicable
- Event timeline / status history
- Post-approval execution state with created work order task and audit record
- Decision summary after resolution

### QA Manager

- Manager Dashboard stats cards: total, pending, escalated, resolved
- **AI–Operator Agreement KPI** (% where operator agreed with AI recommendation) (T-054)
- Escalation Queue
- **Recent Decisions table**: AI Rec. (`AgentRecommendationBadge`), `AiVsHumanBadge` (agreement icon), AI confidence, human override, response time (T-054)
- **Dynamic infinite scroll** in Recent Decisions — more records load seamlessly as the user scrolls, without pagination (T-043)
- Continue review on escalated incidents with full context preserved

### Auditor

- History & Audit table — **includes AI Rec. and agreement columns** (T-054)
- Filters: search, status, severity, date range
- CSV export of loaded incidents
- Read-only traceability surfaces

### IT Admin

- Incident Telemetry page with incident / agent / status / round filters
- Trace summary: items, started, completed, failed, rounds, duration, last trace
- Token usage summary: prompt, completion, total tokens
- Telemetry timeline / prompt trace cards / diagnostics copy
- Document Templates page: template list, versions, last modified metadata, template editor

### Cross-role / supporting UX

- Role-based sidebar navigation
- Role-targeted notifications
- **Workflow Pipeline** widget on the dashboard — shows both AI stages and the post-approval `Execution` stage
- Consistent status color language across dashboard, sidebar, badges, queue, and timeline
- Command palette (`Cmd+K`) with role-aware navigation
- **Electron desktop app** — same operator console as a multi-platform desktop app with native unread badge and OS notifications for production-floor monitoring

### Optional backup only

- Electron desktop add-on: native unread badge + OS notification
- Command palette demo
- Template editor deep dive
- E2E preview role switch

---

## Recommended demo scenarios

### Main cut scenarios

1. **Operator happy path — full editable draft flow** (T-052)
    - Primary candidate: `INC-2026-0001` (GR-204, pending approval, medium risk, conditional release)
    - Show: dashboard → Workflow Pipeline → AI Rec. badge in incident list → bell → incident detail → `AgentRecommendationBadge` (APPROVE) → evidence (verified/unresolved) → batch disposition → CAPA actions → **edit WO draft fields** → **edit Audit entry fields** → Approve enabled → click Approve → incident enters `Execution` → work order task + audit record created → return to dashboard and show Workflow Pipeline `Execution`
    - Proves: AI recommendation is visible upfront, operator edits structured documents not just clicks OK, GxP traceability, and post-approval execution is observable end to end

2. **Follow-up question / Need More Info**
    - Show: recorded multi-turn transcript or prepared follow-up responses inside the same incident, with the same conversation still visible when the case is reopened
    - Proves: human-in-the-loop is iterative, not only approve/reject, and the full dialogue is preserved for both operator context and audit

3. **BLOCKED state — mandatory form fill** (T-052)
    - Strong candidate: `INC-2026-0010` (BLOCKED, confidence `0.31`, no recommendation)
- Show: incident with empty WO and audit entry forms, fields marked required, Approve button disabled; operator fills in mandatory fields → Approve becomes enabled
- Proves: system enforces human accountability for decisions — a person signs a specific document, not just "clicks"

4. **Low confidence — mandatory comment**
    - Candidate: `INC-2026-0008` (`LOW_CONFIDENCE`, confidence ~0.55)
    - Show: warning banner + mandatory comment field before any decision
    - Proves: three-state confidence gate (NORMAL / LOW_CONFIDENCE / BLOCKED)

5. **QA escalation**
    - Primary candidate: `INC-2026-0007` (24h timeout escalation to QA Manager)
    - Show: escalated incident in Manager Dashboard / Escalation Queue
    - Proves: long-running workflow, timeout escalation, continuity of state

6. **Manager oversight — AI vs Human + infinite scroll** (T-043, T-054)
- Show: Recent Decisions table with `AgentRecommendationBadge`, `AiVsHumanBadge` ( ✅ agreed / ⚠️ overridden), AI confidence, response time → scroll down and show more rows loading dynamically in place, without pagination
    - Proves: measurable governance and business-application scale UX with fast, on-demand data loading

7. **Reject path — explicit override reason** (T-054)
    - Candidate: `INC-2026-0042` (rejected, AI recommended approve, closure reason `False positive`)
    - Show: open rejected incident detail → `AI Recommendation (Operator Override)` / struck-through recommendation → `Decision Outcome` / `Closure Reason`
    - Proves: the operator can reject the AI recommendation, must explain why, and the final record preserves both the original proposal and the human override reason

8. **Auditor export + AI columns** (T-054)
- Show: History & Audit with AI Rec. and agreement columns → Export CSV click
    - Proves: inspection readiness and auditability including AI recommendation tracking

9. **Admin telemetry**
    - Show: telemetry summary + token totals + trace/failure counters
    - Proves: observability, prompt traceability, token governance

### Setup checks before recording

- Verify one incident has clear **Verified** and **Unresolved** evidence rows
- Verify `INC-2026-0001` has `ai_analysis.work_order_draft` and `ai_analysis.audit_entry_draft` populated — inits the editable forms
- Verify after approving `INC-2026-0001` the incident shows execution events for work order + audit creation and appears in the Workflow Pipeline `Execution` stage
- Verify `INC-2026-0010` is in BLOCKED state with confidence ≤ 0.35 — forms empty, Approve disabled
- Verify one incident is in `escalated` state (`INC-2026-0007`)
- Verify one rejected incident (`INC-2026-0042`) clearly shows preserved AI recommendation plus required `Closure Reason` / override rationale
- Verify Recent Decisions table has **more than 20 entries** to demonstrate infinite scroll
- Verify telemetry for chosen admin incident contains trace items and token counts
- Verify a multi-turn follow-up transcript exists and remains visible in the incident for both operator review and audit, or record that scenario separately as its own take

---

## Technical requirements

| Parameter | Value |
| --- | --- |
| Duration | ≤ 10:10 minutes (hard limit) |
| Language | **English** |
| Subtitles | Mandatory (judges can watch without sound) |
| Format | MP4 |
| Video quality | ≥ 1080p |
| File size | ≤ 500 MB |

---

## Recording tools

| Role | Tool | Notes |
| --- | --- | --- |
| Screen record + narration | OBS / Loom / QuickTime | For demo segments |
| Installation | DaVinci Resolve (Free) / Camtasia | Collect several clean takes in one walkthrough |
| Subtitles | Auto-captions in DaVinci / Whisper | Manually check GMP / CAPA / Foundry terms |
| Architecture slides | → [T-001](./T-001-architecture-presentation.md) | 1-2 dense slides, no more |

---

## Recording notes

- Do not record as one take. It is better to have 6-8 clean segments and assemble them into one seamless flow
- Do not waste time on live sign-in. Use `e2e` auth mode and switch roles between takes
- The main happy path is one specific incident: **Granulator GR-204** (`INC-2026-0001`)
- Prepare separately: `INC-2026-0008` for LOW_CONFIDENCE beat, `INC-2026-0010` for BLOCKED beat, `INC-2026-0007` for QA escalation beat
- **Editable forms take**: seed `INC-2026-0001` must have `work_order_draft` and `audit_entry_draft` in `ai_analysis` → check before recording
- **Infinite scroll take**: Recent Decisions must have 20+ entries → check seed or generate via `scripts/seed_cosmos.py`
- If there is a prepared transcript, in the happy path show `Need More Info` loop as already recorded conversation, not live typing
- For manager beat, show `AiVsHumanBadge` — where ✅ (operator agreed) and ⚠️ (operator override AI). Better to have a mix of both in Recent Decisions
- For admin beat, target the incident with telemetry summary where there are `Prompt Tokens`, `Completion Tokens`, `Total Tokens`
- Optional only: Electron desktop notification beat after 07:15. Do not make it critical for the final cut

---

## Optional desktop / notification beat

- If the final cut has room after 07:15, show the Electron desktop app rather than a browser-only popup.
- Trigger a fresh incident and show the native unread badge / OS notification beside the in-app bell.
- Position it as a production-readiness point: real operators often need a desktop surface that survives normal work habits, minimized windows, and shift-floor monitoring.
- Mention this can be extended later to Teams or another collaboration notification channel.

---

## Video script (by seconds, aligned with the new tempo)

| Time | What is on the screen | What are we saying?
| --- | --- | --- |
| **00:00–00:07** | Title slide: `Sentinel Intelligence` + subtitle `GMP Deviation & CAPA Operations Assistant` | "In GMP manufacturing, one deviation can trigger thirty to sixty minutes of manual investigation." |
| **00:07–00:15** | Hook slide: `45 min -> < 2 min` + `Governed AI assistance` | "Sentinel Intelligence brings that below two minutes — end to end — with AI, human approval, and traceability at every step. And this is not just a concept demo: it is a reusable, production-ready application that is already designed to be distributed and applied in real operations." |
| **00:15–00:50** | Operations Dashboard - scroll from top to bottom: 4 KPI cards (Total / Pending / Escalated / Resolved), two-column block (pending decisions queue on the left + **Workflow Pipeline** on the right with Ingested → Analyzing → Execution counters), Equipment Health Grid with colored tiles for each piece of equipment (red = critical, blue = processed by AI, green = OK), Incident Analytics table, Recent Decisions table below, footer with live status. | "This is the live operations dashboard — the first screen every operator sees at shift start. The KPI cards show total active incidents, what is pending human review, what has escalated to QA, and what is resolved. In the center, the pending review queue sits beside the Workflow Pipeline, so the operator can see both what needs a decision and where each case sits in the end-to-end flow. The equipment health grid maps each asset by its worst status. Tracking active incidents is critical, which is why the left Active Incidents rail stays visible across screens. New incidents and status changes are highlighted there, so the operator is always aware when something changes. Incident Analytics and Recent Decisions complete the view." |
| **00:50–01:00** | Incident list — show AI Rec. column with `AgentRecommendationBadge` (green APPROVE / red REJECT) and one resolved row, where human override recommendation is visible. | "Notice that the AI ​​recommendation is visible directly in the incident list — before the operator even opens the case. Each row shows the AI ​​call, and resolved rows also show when the operator overrides it. Triage and governance start immediately." |
| **01:00–01:15** | Open bell dropdown, show unread sidebar item, click incident after real-time notification arrives. | "A new incident appears in the bell in real time via SignalR, is highlighted in the unread queue, and then opens directly into the decision workflow for the operator." |
| **01:15–01:35** | Incident detail summary + parameter excursion. Pause on equipment, batch, measured value, limits. | "Notice that the operator does not see raw telemetry alone. They get the equipment, the affected batch, the measured value, the validated range, the duration, and the severity in one view. That is the context needed for a regulated decision." |
| **01:35–01:53** | `AgentRecommendationBadge` in the decision package (APPROVE with an icon). AI recommendation block — risk, confidence, classification, batch disposition. | "The recommendation is visible immediately with a clear APPROVE or REJECT label. Below that, the operator sees risk, confidence, classification, and the proposed batch disposition, so they can see both what the system suggests and how certain it is." |
| **01:53–02:15** | Evidence section. Hold on verified and unresolved evidence rows. | "This is one of the most important screens. We use RAG to retrieve the most relevant documents for the case, but AI can still be imperfect, so we do a second verification step to confirm that every cited document and reference actually exists. Verified citations are grounded in retrieved source material, while unresolved items stay visibly unresolved, so the user can distinguish evidence from assumptions before approving anything in a regulated workflow." |
| **02:15–02:30** | Need More Info transcript, then Batch Release Recommendation + conditions + CAPA actions list. | "If the operator needs more context, they can ask follow-up questions multiple times. That dialogue stays attached to the incident for the operator and for audit. The system then returns with the batch path, explicit release conditions, and the full CAPA action list." |
| **02:30–02:55** | **Editable WO draft form** — scroll to Work Order section, show editable fields (equipment, type, priority, title, description). Operator modifies one field (e.g., priority or description). | "This is where the changes the GxP story. The operator is not just clicking Approve on an AI output — they are editing and confirming the actual work order document. Every field is pre-populated by the AI from the incident context, but the operator owns the final content." |
| **02:55–03:15** | **Editable Audit entry draft form** — scroll to Audit section, show deviation type, batch reference, action taken, comments fields. | "Same pattern for the audit entry: AI fills the draft, operator reviews and confirms each field. Only when both forms are complete does the Approve button become active. This is a governed co-authorship model, not a rubber stamp." |
| **03:15–03:35** | Click Approve. Status changes to `Execution` → show incident status history / audit timeline with created work order task and audit record → jump back to dashboard Workflow Pipeline. | "Approval commits both drafts and immediately moves the CAPA plan into execution. At that point the system creates the work order task and audit record. We can track that transition inside the incident itself and from the Workflow Pipeline on the home screen." |
| **03:35–03:50** | Incident with `LOW_CONFIDENCE` banner (INC-2026-0008, confidence ~0.55). Show banner + mandatory comment field. | "When confidence drops below the threshold, the system shows a warning and requires a comment before the operator can decide. The case stays human-led, just with extra caution." |
| **03:50–04:05** | Pivot to `BLOCKED` state incident (INC-2026-0010, confidence 0.31). Show empty WO and audit forms with red required indicators. Approve button visibly disabled. Operator fills mandatory field → Approve becomes enabled. | "When the AI cannot produce a grounded result, it does not force a recommendation. Both document forms start empty, every required field is marked, and approval stays locked until the operator fills them in." |
| **04:05–04:15** | RBAC slide or role-switch setup screen. Show Microsoft sign-in context and the role matrix: Operator, QA Manager, Maintenance Tech, Auditor, IT Admin. | "Access is not anonymous here. Users sign in with Microsoft, and RBAC controls what each role can see and do. Operators, QA, maintenance, auditors, and IT admins all work in the same system, but each one gets only the views and actions relevant to their responsibility." |
| **04:15–04:35** | QA Manager view: Manager Dashboard → stats cards → **AI–Operator Agreement KPI widget**. | "If a case sits too long, it escalates to QA with the full context intact. At the top, the manager can see the AI-operator agreement rate. In this run, operators agreed with the AI eighty-three percent of the time." |
| **04:35–05:00** | Escalation Queue → Recent Decisions table → open one rejected incident summary. Show `AgentRecommendationBadge` column, `AiVsHumanBadge` (✅ agreed / ⚠️ overridden), AI confidence, response time, `Decision Outcome`, `Closure Reason`. | "Recent Decisions shows the AI recommendation, whether the operator agreed or overrode it, the AI confidence, and the response time. And when we open a rejected case, we can see both what the AI proposed and why the operator rejected it." |
| **05:00–05:15** | Scroll down in Recent Decisions — show that the list works like a business application list: without pagination, with dynamic and fast loading of new lines right during scrolling. | "All scrolling here is designed for a business application. There is no pagination step, no context switch, and no waiting on separate pages. The table loads additional records dynamically and quickly, exactly when the user needs them." |
| **05:15–05:30** | Auditor view: History & Audit table with AI Rec. and agreement columns. Click `Export CSV`. | "For auditors, those same fields stay in the log: the AI ​​recommendation, the agreement status, and the rejection rationale. And the full set exports in one click for offline review." |
| **05:30–05:45** | IT Admin view: read-only Incident Telemetry summary with trace counters and token totals. | "IT does not make workflow decisions here, and those decision actions are blocked for this role. But admins can inspect trace counts, failures, rounds, duration, and token usage for each incident. This is where prompt tracing, troubleshooting, and cost visibility come together." |
| **05:45–06:00** | Architecture slide reveal step 1: Track A + two-level orchestration. | "Now let me show what makes all of this possible behind the scenes. This is Track A, where GitHub, Azure, and Azure AI Foundry work together. There are two orchestration layers here. Durable Functions runs the stateful workflow: incident creation, retry, escalation, and the HITL pause. Foundry handles the AI reasoning: research, synthesis, and then, after approval, execution through MCP tools." |
| **06:00–06:20** | Architecture slide reveal step 2: Service Bus, Cosmos DB, AI Search, SignalR, MCP, Entra ID, CI/CD. | "AI Search grounds the answers in validated documents. Service Bus is the incident processing queue: it absorbs alert bursts and feeds incidents into the workflow. Cosmos keeps the durable state. SignalR pushes real-time updates. MCP keeps the QMS and CMMS integrations modular. Entra ID and app roles enforce RBAC, while PIM, Conditional Access with MFA, and Defender for Cloud protect the platform. And the Foundry eval gate in CI/CD blocks any deployment if AI quality drops." |
| **06:20–06:30** | Architecture slide highlight: alert feedback loop arrow from Reject back to SCADA/MES. | "If an operator rejects a recommendation, the system records both the disagreement flag and the reason, then sends that back toward the source system. And if an orchestrator gets stuck or orphaned, a timer-trigger watchdog requeues it through Service Bus without losing business context. So every human decision feeds the loop, and the workflow stays resilient." |
| **06:30–06:50** | KPI slide: before/after numbers + three-state confidence gate summary. | "The result is a faster, more consistent, and fully traceable way to handle deviations in regulated manufacturing. And the three-state confidence gate — normal, low confidence, and blocked — keeps the system from sounding certain when it is not grounded." |
| **06:50–07:05** | Closing product screenshot or KPI slide. | "Instead of chasing documents, context, and approvals by hand, operators get a decision package in minutes, with evidence, actions, and next steps already laid out." |
| **07:05–07:15** | Final branded closing frame. | "This is Sentinel Intelligence, built to support governed pharma operations at scale." |
| **07:15–07:45** | Optional add-on block: show the Electron desktop app on macOS/Windows-style desktop, native unread badge, OS notification, and one final technical epilogue card. | "And this is not only a web dashboard. For real production floors, operators should not depend on keeping a browser tab visible. Sentinel Intelligence also runs as a multi-platform desktop app, using the same governed workflow but adding native unread badges and operating-system notifications. We now also keep a frontend unit-test baseline in CI, so every pull request must pass the web test layer before merge, and the next testing slice is deeper backend coverage. As a final engineering note, we also optimized the platform behind the scenes: when the AI concurrency limit is reached, incidents wait safely in a queue instead of failing, and during testing we reduced prompt footprint from about 14.7 kilobytes to 6.1 kilobytes, while the runtime orchestrator prompt dropped from roughly 6.0 thousand characters to 1.8 thousand. The same channel can later be extended to collaboration surfaces like Microsoft Teams." |

### Delivery notes

- Hold a pause of 1-2 seconds on `Verified` / `Unresolved` badges, `AgentRecommendationBadge`, and `AiVsHumanBadge` — so that the judges have time to read
- Do not show live login, role switching or technical transition steps. The roles can be changed between takes and reduced in the editing
- **Editable forms beat (02:30–03:15)** is the most important new beat. Seed incident `INC-2026-0001` must have `ai_analysis.work_order_draft` and `ai_analysis.audit_entry_draft` populated. Show editing, not just scrolling
- **Execution beat (03:15–03:35)** — after Approve, linger on the incident timeline / status history so that the creation of the work order task and audit record can be seen, then briefly return to the dashboard and show the incident in the Workflow Pipeline `Execution`
- **BLOCKED beat (03:50–04:15)** — `INC-2026-0010` should be in a state where Approve is disabled. Showing the moment when the operator fills in one field and Approve becomes enabled is a drama moment
- **Infinite scroll beat (05:00–05:15)** — make sure there are 20+ entries in Recent Decisions. Scroll slowly so judges can see seamless dynamic loading without pagination
- `operator_agrees_with_agent` flag is recorded at Approve and Reject. `AiVsHumanBadge` shows this result. If there is time, show the reject path where the badge becomes ⚠️
- **Reject beat** — use `INC-2026-0042`; linger on `AI Recommendation (Operator Override)` and `Closure Reason` so that the judges have time to read exactly what the AI ​​proposed and why the operator rejected the decision
- On the architecture slide, make a step-by-step reveal in 3 steps: orchestration → services → feedback loop
- If the approval click breaks the pacing, you can show the available actions and the audit timeline with a separate cut instead of the live click
- **Desktop add-on beat (after 07:15)** — optional if final timing allows. Show it after the main close as "one more production-ready surface", not in the critical path. The point is not Electron as technology; the point is native operator attention: taskbar/Dock badge, OS notification, CI-guarded frontend test coverage, and future Teams/collaboration extension.

---

## Definition of Done

- [ ] The complete script is written and approved by the team
- [ ] [T-001](./T-001-architecture-presentation.md) architecture slides are ready
- The frame-by-frame dry-run timing is verified: the narration is inserted in 7:15 without rushing (~3 minutes spare for editing pauses and transitions)
- [ ] At least 5 demo states have been prepared: operator happy path + editable drafts, LOW_CONFIDENCE, BLOCKED mandatory fill, QA escalation, auditor/admin traceability
- [ ] Evidence verification state (**verified** vs **unresolved**) is clearly visible in the recorded demo
- [ ] **Editable WO and Audit entry forms** shown with actual field editing (T-052)
- [ ] After Approve, the transition to `Execution` is shown: creation of work order task + audit record, visible both in the incident and in the Workflow Pipeline
- [ ] **BLOCKED state** shows Approve disabled → the operator fills in → Approve enabled (T-052)
- [ ] **`AgentRecommendationBadge`** can be seen in the incident list and in the decision package (T-054)
- [ ] **`AiVsHumanBadge`** can be seen in Recent Decisions (T-054)
- [ ] **AI–Operator Agreement KPI** visible in Manager Dashboard (T-054)
- [ ] Reject path shown clearly: preserved AI recommendation + explicit closure reason / override rationale
- [ ] **Infinite scroll** in Recent Decisions is shown (scroll → spinner → new lines) (T-043)
- [ ] Live demo recorded clean segments for editing
- [ ] Optional Electron desktop add-on recorded if the final cut has spare time: native badge/notification visible after a new incident
- [ ] The video is assembled into a single file
- [ ] Subtitles added and checked
- [ ] Duration ≤ 10:10
- [ ] Reviewed by team and approved
- [ ] Uploaded to the hackathon platform before the deadline

---

← [04 · Action Plan](../04-action-plan.md) · [T-001 Architecture](./T-001-architecture-presentation.md)
