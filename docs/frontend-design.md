# Frontend Design Document — Sentinel Intelligence

← [README](../README.md) · [02 Architecture](../02-architecture.md) · [T-032](../tasks/T-032-frontend-core.md) · [T-033](../tasks/T-033-frontend-approval.md) · [T-034](../tasks/T-034-frontend-other-roles.md)

> **Date:** April 17, 2026
> **Stack:** React 19 + Vite 8 + TypeScript 6 + TanStack Query + MSAL React
> **Deploy:** Azure Static Web Apps  
> **Auth:** Azure Entra ID (MSAL v5, redirect flow)

---

## Contents

1. [General philosophy](#1-general-philosophy)
2. [Information architecture] (#2-information-architecture)
3. [Roles and access](#3-roles-and-access)
4. [Layout and navigation](#4-layout-and-navigation)
5. [Pages and Screens](#5-pages-and-screens)
   - [5.1 Operational Dashboard (Operator)](#51-operational-dashboard-operator)
   - [5.2 Incident Card (Detail)](#52-incident-card-detail)
   - [5.3 Approval Panel + Chat](#53-approval-panel--chat)
   - [5.4 Incident History + Audit](#54-incident-history--audit)
   - [5.5 Manager Dashboard](#55-manager-dashboard)
   - [5.6 Template Management (IT Admin)](#56-template-management-it-admin)
6. [Real-time (SignalR)](#6-real-time-signalr)
7. [Routing Map](#7-routing-map)
8. [State Management](#8-state-management)
9. [API Integration](#9-api-integration)
10. [Component Tree](#10-component-tree)
11. [Design-solutions and add-ons](#11-design-solutions-and-additions)
12. [MVP Scope vs Nice-to-have](#12-mvp-scope-vs-nice-to-have)

---

## 1. General philosophy

- **Operational-first:** The UI is optimized for the operator under time pressure. A minimum of clicks to a decision.
- **Audit-ready:** every action is recorded and visualized. The auditor sees a complete trace without unnecessary transitions.
- **Role-aware:** one app, but each role sees only what it needs. Sidebar navigation adapts to the role.
- **Real-time:** SignalR push notifications. New incidents appear without a refresh. Statuses are updated live.
- **GMP-compliant UX:** clear visual separation between AI recommendation and human decision. Confidence gate is visible.

---

## 2. Information architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Sentinel Intelligence                      │
├─────────────┬───────────────────────────────────────────────────┤
│  SIDEBAR    │  MAIN CONTENT AREA                                │
│             │                                                    │
│  ┌───────┐  │  ┌──────────────────────────────────────────────┐ │
│  │ Active│  │  │  Selected view:                             │ │
│  │ Inc.  │  │  │  - Operational Dashboard (default)           │ │
│  │ List  │  │  │  - Incident Card (detail)                    │ │
│  │       │  │  │  - History / Audit                           │ │
│  │ ──────│  │  │  - Manager Dashboard                         │ │
│  │ Nav   │  │  │  - Templates                                 │ │
│  └───────┘  │  └──────────────────────────────────────────────┘ │
└─────────────┴───────────────────────────────────────────────────┘
```

### Key entities

| Essence | Description | Cosmos Container |
|---|---|---|
| **Incident** | Incident: alert → enrichment → AI analysis → decision → execution | `incidents` |
| **Approval Task** | Task for the operator: decision package + approve/reject/more_info | `approval-tasks` |
| **Work Order** | Order for correction (created after approval) | `approval-tasks` (execution_result) |
| **Audit Entry** | Audit record (GMP compliance) | `approval-tasks` (execution_result) |
| **Equipment** | Equipment (GR-204, TB-102, FBD-301) | `equipment` |
| **Batch** | Production batch | `batches` |
| **Template** | Document template (work order, audit entry) | `approval-tasks` (template_id ref) |

---

## 3. Roles and Access

> 5 roles defined in Azure Entra ID (T-035). The role comes in JWT access token → `roles` claim.

| Role | Sidebar | Operational | Incident Card | Approval | History | Manager | Templates |
|---|---|---|---|---|---|---|---|
| **operator** | ✅ Active incidents | ✅ (own) | ✅ Read + Decision | ✅ Approve/Reject/Chat | ✅ (own) | ❌ | ❌ |
| **qa-manager** | ✅ All incidents | ✅ (all) | ✅ Read + Decision | ✅ (escalated + override) | ✅ (all) | ✅ | ❌ |
| **maintenance-tech** | ✅ Closed incidents | ❌ | ✅ Read-only (WO focus) | ❌ | ✅ (read-only) | ❌ | ❌ |
| **auditor** | ❌ | ❌ | ✅ Read-only (audit focus) | ❌ | ✅ (all, export) | ❌ | ❌ |
| **it-admin** | ✅ All incidents | ✅ (all, read-only) | ✅ Read-only | ❌ | ✅ (all) | ✅ (stats) | ✅ Edit |

### Visibility rules

- **Operator** only sees incidents where `assigned_to === currentUser` or not yet assigned
- **QA Manager** sees all incidents + escalated (where timeout or `confidence < 0.7`)
- **Maintenance Tech** sees only approved/closed incidents (focus on Work Orders)
- **Auditor** sees only History/Audit view — full trail of all incidents
- **IT Admin** sees everything read-only + can edit Templates

---

## 4. Layout and navigation

### AppShell — general layout

```

**Header notification center:**
- `🔔` badge shows the number of unread notifications for the current user
- click opens dropdown only with unread items; each item leads to `/incidents/{id}`
- after opening the incident detail, the frontend calls `POST /api/incidents/{id}/notifications/read`, and the unread marker for this incident disappears
- browser/system notifications — optional enhancement: permission is requested only by user gesture from the dropdown, and the system alert is shown only when the tab is hidden / unfocused
┌──────────────────────────────────────────────────────────────────────┐
│ HEADER                                                                │
│ 🛡️ Sentinel Intelligence    Plant-01 ▾     Ivan Petrenko [Operator]  │
│                                              🔔 2         [Sign Out]  │
├──────────┬───────────────────────────────────────────────────────────┤
│ SIDEBAR  │  MAIN CONTENT                                             │
│ 240px    │                                                           │
│          │                                                           │
│ ┌──────┐ │                                                           │
│ │ NAV  │ │                                                           │
│ │──────│ │                                                           │
│ │📋 Op │ │                                                           │
│ │📂 His│ │                                                           │
│ │📊 Mgr│ │                                                           │
│ │📄 Tpl│ │                                                           │
│ │──────│ │                                                           │
│ │ACTIVE│ │                                                           │
│ │ INC. │ │                                                           │
│ │ LIST │ │                                                           │
│ │      │ │                                                           │
│ │INC-01│ │                                                           │
│ │🟠 Doc│ │                                                           │
│ │ready │ │                                                           │
│ │      │ │                                                           │
│ │INC-03│ │                                                           │
│ │🔵 AI │ │                                                           │
│ │work  │ │                                                           │
│ └──────┘ │                                                           │
└──────────┴───────────────────────────────────────────────────────────┘
```

### Sidebar - two parts

**Top: navigation** (adaptive for the role)

| Item | Route | Roles
|---|---|---|
| 📋 Operations | `/` | operator, qa-manager, it-admin |
| 📂 History & Audit | `/history` | all |
| 📊 Manager Dashboard | `/manager` | qa-manager, it-admin |
| 📄 Templates | `/templates` | it-admin |

**Bottom: Active Incidents** — live list of active incidents

```
──── Active Incidents (3) ────

INC-2026-0042                     17 Apr, 15:56
   GR-204 · Impeller speed
   ● Awaiting decision

INC-2026-0043                     17 Apr, 15:55
   TB-102 · Coating thickness
   ● AI preparing documents...

INC-2026-0044                     17 Apr, 15:55
   FBD-301 · Inlet temp
   ● Escalated to QA Manager

──────────────────────────────
```

Each element shows:
- **Incident number** (INC-YYYY-NNNN)
- **Short name** — generated by AI (Foundry Orchestrator Agent must generate `title` field)
- **Equipment** (equipment_id)
- **Date/time** — on the right in the header line, `tabular-nums`, muted
- **Status-indicator** — CSS-dot, not emoji, to avoid mixing system emoji fonts with UI typography:

| Status | Dot color | Text |
|---|---|---|
| `open` | blue | Open |
| `ingested` | blue | Ingesting... |
| `analyzing` | blue | AI analyzing... |
| `pending_approval` | orange | Awaiting decision |
| `escalated` | yellow | Escalated to QA Manager |
| `approved` | green | Approved, executing... |
| `rejected` | red | Rejected |
| `closed` | gray | Closed |

**Typography sidebar item:**
- incident number: sans-serif, 12px, 700; don't use mono as the main font in the list, because it reads like a debug ID
- equipment: 13px, 650/700, `text-heading`
- title: 12px, muted, ellipsis
- status: 12px, 700, colored by status
- avoid emoji in statuses; they are rendered by a different font stack and visually "break" the line

Click on an incident → opens the Incident Card in the main area.

**Unread state for sidebar:**
- if there is at least one unread notification for the incident, the item receives accent background + unread dot
- bell badge count and sidebar highlight are built from `GET /api/notifications/summary`, not from localStorage
- local cache is allowed only as React Query cache; source of truth — Cosmos `notifications`

---

## 5. Pages and screens

### 5.1 Operational Dashboard (Operator)

**Route:** `/`  
**Roles:** operator, qa-manager, it-admin
**Gist:** the operator's main screen. Shows only **active** incidents (not closed) that need attention.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Operations Dashboard                                                 │
│  3 incidents require attention                                        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ ⚠️  ACTION REQUIRED                                              │ │
│  │ INC-2026-0042 · GR-204 · Impeller Speed Deviation               │ │
│  │ Severity: 🟠 MAJOR   Risk: 🟠 MEDIUM   Confidence: 84%          │ │
│  │ AI recommends: Stop granulator, inspect impeller bearing         │ │
│  │ 12 min ago                           [View & Decide →]          │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ 🤖 AI PROCESSING                                                 │ │
│  │ INC-2026-0043 · TB-102 · Coating Thickness Out of Spec          │ │
│  │ Severity: 🟡 MODERATE                                            │ │
│  │ Agent is building analysis... (step 2/4: Document Agent)         │ │
│  │ 3 min ago                                                        │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ 🔴 LOW CONFIDENCE — QA MANAGER NOTIFIED                         │ │
│  │ INC-2026-0044 · FBD-301 · Inlet Temperature Spike               │ │
│  │ Severity: 🟠 MAJOR   Risk: ⚠️ LOW_CONFIDENCE   Confidence: 52%  │ │
│  │ Insufficient evidence. QA Manager review required.               │ │
│  │ 45 min ago                           [View Details →]           │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

**Behavior:**
- Sorting: `pending_approval` → `escalated` → `analyzing` → `ingested` → others
- Cards appear real-time through SignalR
- For operator: shows only `assigned_to === me`
- For qa-manager: shows all + separate section "Escalated to You"
- "View & Decide →" → opens `/incidents/{id}` with Approval Panel

---

### 5.2 Incident Card (Detail)

**Route:** `/incidents/{id}`  
**Roles:** all (with different access levels)

Main page of the incident. Layout — **2 columns** (or tabs on mobile):

```
┌──────────────────────────────────────────────────────────────────────┐
│  ← Back    INC-2026-0042 · Impeller Speed Deviation                  │
│  Status: 🟠 PENDING APPROVAL          Equipment: GR-204              │
├──────────────────────────┬───────────────────────────────────────────┤
│  LEFT COLUMN (60%)       │  RIGHT COLUMN (40%)                       │
│                          │                                           │
│  ┌────────────────────┐  │  ┌─────────────────────────────────────┐ │
│  │ INCIDENT INFO      │  │  │ APPROVAL PANEL                     │ │
│ │ Equipment: GR-204 │ │ │ (or Agent Chat if │ │
│ │ Batch: BPR-0042 │ │ │ already decided) │ │
│  │ Product: Metformin  │  │  │                                    │ │
│ │ Stage: Wet Gran.   │ │ │ → Block 5.3 below │ │
│  │ Reported: 08:42    │  │  │                                    │ │
│  │ Assigned: Ivan P.  │  │  │                                    │ │
│  └────────────────────┘  │  │                                    │ │
│                          │  │                                    │ │
│  ┌────────────────────┐  │  │                                    │ │
│  │ PARAMETER           │  │  │                                    │ │
│  │ EXCURSION           │  │  │                                    │ │
│  │ ████████░░░ 580 RPM │  │  │                                    │ │
│  │ NOR: 600-700 RPM   │  │  │                                    │ │
│  │ PAR: 580-750 RPM   │  │  │                                    │ │
│  │ Duration: 4m 7s    │  │  │                                    │ │
│  └────────────────────┘  │  │                                    │ │
│                          │  │                                    │ │
│  ┌────────────────────┐  │  │                                    │ │
│  │ AI ANALYSIS        │  │  └─────────────────────────────────────┘ │
│  │ Risk: 🟠 MEDIUM    │  │                                          │
│  │ Confidence: 84%    │  │                                          │
│  │ Classification:    │  │                                          │
│  │  Equipment Dev II  │  │                                          │
│  │ Root cause: Motor  │  │                                          │
│  │  load fluctuation  │  │                                          │
│  │                    │  │                                          │
│  │ CAPA Steps:        │  │                                          │
│  │ 1. Moisture check  │  │                                          │
│  │ 2. Motor calibr.   │  │                                          │
│  │ 3. Filter replace. │  │                                          │
│  └────────────────────┘  │                                          │
│                          │                                          │
│  ┌────────────────────┐  │                                          │
│  │ EVIDENCE           │  │                                          │
│  │ 📄 SOP-DEV-001 §4.2│  │                                          │
│  │ 📋 INC-2025-0311   │  │                                          │
│  │ 📖 GMP Annex 15    │  │                                          │
│  └────────────────────┘  │                                          │
│                          │                                          │
│  ┌────────────────────┐  │                                          │
│  │ DOCUMENTS          │  │                                          │
│  │ 📝 Work Order Draft│  │                                          │
│  │ 📝 Audit Entry     │  │                                          │
│  │   Draft            │  │                                          │
│  └────────────────────┘  │                                          │
│                          │                                          │
│  ┌────────────────────┐  │                                          │
│  │ TIMELINE / AUDIT   │  │                                          │
│  │ ● 08:42 Alert recv │  │                                          │
│  │ ● 08:42 Enrichment │  │                                          │
│  │ ● 08:43 AI start   │  │                                          │
│  │ ● 08:44 AI done    │  │                                          │
│  │ ● 08:44 Pending    │  │                                          │
│  │   approval         │  │                                          │
│  │ ● 08:51 Operator   │  │                                          │
│  │   asks question    │  │                                          │
│  │ ● 08:52 AI re-run  │  │                                          │
│  │ ● 08:53 Approved   │  │                                          │
│  │ ● 08:53 WO created │  │                                          │
│  │ ● 08:53 AE created │  │                                          │
│  │ ● 08:53 Batch      │  │                                          │
│  │   → Cond. Release  │  │                                          │
│  └────────────────────┘  │                                          │
└──────────────────────────┴──────────────────────────────────────────┘
```

### Incident Card sections

#### 1. Incident Info
Basic information: equipment, batch, product, production stage, time, operator.

#### 2. Parameter Excursion
Visual scale: measured value vs NOR (Normal Operating Range) vs PAR (Proven Acceptable Range). A clear display or the parameter went beyond NOR but still in PAR, or already beyond PAR.

#### 3. AI Analysis
Risk level (HIGH/MEDIUM/LOW + LOW_CONFIDENCE), confidence bar, deviation classification, root cause hypothesis, CAPA steps recommendation.

#### 4. Evidence Citations
SOP references, historical similar cases, GMP clauses — with clickable links.

#### 5. Documents (Work Order + Audit Entry drafts)
Pre-filled drafts of documents that the Execution Agent will create after approval. The operator can preview what will be created.

#### 6. Batch Disposition
After approval, the batch changes its status. The section shows the current and recommended disposition:

```
┌────────────────────────────────────────┐
│  📦 BATCH DISPOSITION                  │
│                                        │
│  Batch: BPR-2026-0042                  │
│  Product: Metformin 500mg              │
│  Current status: 🟢 In Production      │
│                                        │
│  AI Recommendation:                    │
│  ⚠️  Conditional Release               │
│  Condition: Pending extended sampling   │
│  results (moisture + granule size)     │
│                                        │
│  After approval:                       │
│  Status will change to:                │
│  🟡 CONDITIONAL RELEASE                │
└────────────────────────────────────────┘
```

Disposition statuses:

| Status | Color | Description |
|---|---|---|
| `in_production` | 🟢 green | Batch in production, everything is OK |
| `hold` | 🔴 red | Batch stopped (critical deviation or reject) |
| `conditional_release` | 🟡 yellow | Release with conditions (additional testing) |
| `released` | 🟢 green | Confirmed after meeting the conditions |
| `rejected` | ⚫ black | Batch rejected |

**Logic of status change:**
- Operator approves + AI recommends conditional release → batch → `conditional_release`
- Operator approves + AI recommends full release → batch → `released`
- Operator rejects → batch → `hold` (requires QA Manager review)
- LOW_CONFIDENCE + escalation → batch → `hold` (auto-hold until QA decision)

**Implementation:** Document Agent generates `batch_disposition` field in `DocumentAgentOutput`. Execution Agent updates batch status in Cosmos `batches` container after approval.

#### 7. Timeline / Audit Trail
A chronological log of all incident events. GMP audit-ready format. Each record: timestamp, actor (system/agent/human), action, result.

#### The difference depends on the role

| Role | What sees | Approval Panel |
|---|---|---|
| operator | All sections + Approval Panel | ✅ Active (if assigned) |
| qa-manager | All sections + Approval Panel | ✅ Active (escalated / override) |
| maintenance-tech | Incident Info + Documents + Timeline | ❌ Read-only, WO focus |
| auditor | All sections (read-only) + Timeline | ❌ Read-only |
| it-admin | All sections (read-only) | ❌ Read-only |

---

### 5.3 Approval Panel + Chat

**Location:** Right column on Incident Card (sticky, scrolls independently).
**Visibility:** only operator and qa-manager, only when `status === pending_approval` and incident assigned.

#### Approval Panel (when the AI ​​has finished the analysis)

```
┌──────────────────────────────────────┐
│  ⚠️  YOUR DECISION REQUIRED          │
│                                      │
│  AI Recommendation:                  │
│  Stop granulator, inspect bearing    │
│  Risk: 🟠 MEDIUM   Conf: 84%        │
│                                      │
│  WO will create:                     │
│  "Motor Load Calibration Check"      │
│  Priority: High · Est. 4h            │
│                                      │
│  Batch disposition after approval:   │
│  📦 BPR-0042 → Conditional Release   │
│  (pending extended sampling)         │
│                                      │
│  ┌──────────────────────────────┐   │
│  │      ✅ APPROVE              │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │      ❌ REJECT               │   │
│  └──────────────────────────────┘   │
│                                      │
│  ────── or ask the agent ──────     │
│                                      │
│  ┌────────────────────────┬─────┐   │
│  │ Ask a question...      │ ➤  │   │
│  └────────────────────────┴─────┘   │
└──────────────────────────────────────┘
```

#### Chat with an agent (Agent Conversation)

The chat panel is **embedded below the buttons** (or instead of them after making a decision). This is **not optional** - it is part of the audit. Each operator's question and agent's answer are recorded in the incident timeline.

```
┌──────────────────────────────────────┐
│  💬 Agent Conversation               │
│                                      │
│  ┌──────────────────────────────┐   │
│  │ 👤 You (08:47):              │   │
│  │ "Can this affect batch       │   │
│  │  integrity if speed was      │   │
│  │  below PAR for < 5 min?"    │   │
│  └──────────────────────────────┘   │
│                                      │
│  ┌──────────────────────────────┐   │
│  │ 🤖 Agent (08:48):            │   │
│  │ "Per BPR-MET-500-v3.2 §3.4, │   │
│  │  impeller speed within PAR   │   │
│  │  (580–750) for < 5 min has   │   │
│  │  no documented impact on     │   │
│  │  granule uniformity.         │   │
│  │  However, SOP-DEV-001 §4.2   │   │
│  │  requires logging even       │   │
│  │  within-PAR deviations       │   │
│  │  exceeding 10% NOR.          │   │
│  │                              │   │
│  │  📝 Updated: CAPA step 1    │   │
│  │  now includes extended       │   │
│  │  sampling instead of         │   │
│  │  production stop."           │   │
│  └──────────────────────────────┘   │
│                                      │
│  ┌────────────────────────┬─────┐   │
│  │ Ask a question...      │  ➤ │   │
│  └────────────────────────┴─────┘   │
└──────────────────────────────────────┘
```

**Chat logic:**
1. The operator enters the question → `POST /api/incidents/{id}/decision` from `action: "more_info"` and `question: "..."`
2. Backend: Durable orchestrator receives event → re-run `run_foundry_agents` with additional context (the operator requests X)
3. Agent can update documents (WO draft, audit entry draft, CAPA steps) → update comes via SignalR
4. The updated AI Analysis is displayed on the left, and the agent's response appears in the chat
5. The Approve/Reject buttons remain available — the operator can make a decision at any time

**Reject flow:**
- Clicking "Reject" → a modal window with a mandatory field "Reason for rejection" (textarea, min 10 chars)
- Reason is stored in the audit trail

**After decision:** chat panel becomes read-only, shows full history of correspondence as part of audit.

---

### 5.4 Incident History + Audit

**Route:** `/history`  
**Roles:** all (with different amount of data)

This is the main **retrospective view** — for auditors, managers, and operators who want to see past incidents.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Incident History & Audit                                             │
├──────────────────────────────────────────────────────────────────────┤
│  FILTERS                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐ │
│  │ Search 🔍│ │ Status ▾ │ │Severity ▾│ │Equipment▾│ │Date range │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └───────────┘ │
│                                                                       │
│  ┌──────────────────────────────┐  [📥 Export CSV]                   │
│  │ Showing 42 of 156 incidents  │                                    │
│  └──────────────────────────────┘                                    │
│                                                                       │
│  ┌────┬──────────┬─────────┬────────┬──────────┬────────┬─────────┐ │
│  │ ID │ Equipm.  │ Title   │ Sev.   │ Status   │ Decis. │ Batch   │ Date    │ │
│  ├────┼──────────┼─────────┼────────┼──────────┼────────┼─────────┼─────────┤ │
│  │0042│ GR-204   │ Impeller│ 🟠 MAJ │ ✅ Closed │Approved│ 🟡 Cond │ 17 Apr  │ │
│  │0041│ TB-102   │ Coating │ 🟡 MOD │ ❌ Reject │Rejected│ 🔴 Hold │ 16 Apr  │ │
│  │0040│ FBD-301  │ Inlet T │ 🟠 MAJ │ ⏫ Escal. │Pending │ 15 Apr  │ │
│  │0039│ GR-204   │ Spray R.│ 🟡 MOD │ ✅ Closed │Approved│ 14 Apr  │ │
│  │... │          │         │        │          │        │         │ │
│  └────┴──────────┴─────────┴────────┴──────────┴────────┴─────────┘ │
│                                                                       │
│  ← 1 2 3 4 ... 8 →                   Pagination                     │
└──────────────────────────────────────────────────────────────────────┘
```

**Features:**
- **Full-text search** by number, name, equipment, batch
- **Filters:** status (multi-select), severity, equipment, date range
- **Sorting:** by date (default desc), severity, status
- **Export CSV:** for auditor — all filtered records
- Click on the line → `/incidents/{id}` (Incident Card)

**Audit Trail view (expandable row or tab):**

When clicking on an incident in History, in addition to going to the Incident Card, the auditor can expand the inline timeline:

```
│ ▼ INC-2026-0042 · GR-204 · Impeller Speed Deviation                 │
│                                                                       │
│   08:42:11  SYSTEM   Alert received (SCADA vibration_trend)           │
│   08:42:15  SYSTEM   Context enrichment: GR-204, BPR-0042            │
│   08:42:18  AGENT    Research Agent: queried 5 indexes, 3 MCP calls   │
│   08:43:22  AGENT    Document Agent: risk=MEDIUM, conf=0.84           │
│   08:43:25  SYSTEM   Notification sent to ivan.petrenko (operator)    │
│   08:47:33  HUMAN    ivan.petrenko asked: "Can this affect batch..."  │
│   08:48:01  AGENT    Re-analysis: updated CAPA step 1                 │
│   08:51:10  HUMAN    ivan.petrenko: APPROVED                          │
│   08:51:12  AGENT    Execution Agent: WO-2026-0847 created            │
│   08:51:13  AGENT    Execution Agent: AE-2026-1103 created            │
│   08:51:13  SYSTEM   Batch BPR-0042 → CONDITIONAL RELEASE             │
│   08:51:14  SYSTEM   Incident closed                                  │
```

---

### 5.5 Manager Dashboard

**Route:** `/manager`  
**Roles:** qa-manager, it-admin

```
┌──────────────────────────────────────────────────────────────────────┐
│  Manager Dashboard                                                    │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │
│  │ 📊 Total   │  │ ⏳ Pending  │  │ ⏫ Escalated│  │ ✅ Resolved │    │
│  │    156     │  │     3      │  │     1      │  │    142     │    │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘    │
│                                                                       │
│  ESCALATION QUEUE (requires QA Manager attention)                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ ⚠️  INC-2026-0044 · FBD-301 · Inlet Temp                     │   │
│  │    LOW_CONFIDENCE (52%) — waiting 45 min                      │   │
│  │    Auto-escalated: confidence < 0.7                           │   │
│  │                                         [Review & Decide →]  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ ⏰ INC-2026-0038 · GR-204 · Motor current                    │   │
│  │    Timeout: operator did not respond for 8h                   │   │
│  │    Auto-escalated: 24h timeout approaching                    │   │
│  │                                         [Review & Decide →]  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  TRENDS (last 30 days)                                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Incidents per week     │ By severity    │ By equipment      │   │
│  │  ▁▃▅█▇▃  (bar chart)   │ 🔴 12 critical │ GR-204: 8        │   │
│  │                         │ 🟠 45 major    │ TB-102: 5        │   │
│  │                         │ 🟡 99 moderate │ FBD-301: 3       │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  RECENT DECISIONS                                                    │
│  ┌────┬──────────┬──────────┬──────────────┬──────────┬──────────┐  │
│  │ ID │ Operator │ Decision │ AI Confidence│ Override │ Time     │  │
│  ├────┼──────────┼──────────┼──────────────┼──────────┼──────────┤  │
│  │0042│ Ivan P.  │ Approved │ 84%          │ No       │ 9 min    │  │
│  │0041│ Anna K.  │ Rejected │ 71%          │ No       │ 2h       │  │
│  │0040│ QA Mgr   │ Approved │ 52%          │ Yes ⚠️   │ 1d       │  │
│  └────┴──────────┴──────────┴──────────────┴──────────┴──────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

**Value for demo:** shows the "management" level - QA Manager sees the full picture, escalations, and can adjust solutions.

---

### 5.6 Template Management (IT Admin)

**Route:** `/templates`  
**Roles:** it-admin only

```
┌──────────────────────────────────────────────────────────────────────┐
│  Document Templates                                                   │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 📄 Work Order Template                     v2.1  [Edit →]   │   │
│  │ Used by: Execution Agent → CMMS                              │   │
│  │ Last modified: 15 Apr 2026 by admin@company.com              │   │
│  │ Fields: type, priority, description, assigned_team, est_hrs  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 📄 Audit Entry Template                    v1.3  [Edit →]   │   │
│  │ Used by: Execution Agent → QMS                               │   │
│  │ Last modified: 10 Apr 2026 by admin@company.com              │   │
│  │ Fields: deviation_type, gmp_clause, root_cause, capa_ref     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ── EDIT MODE ──                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Work Order Template — v2.1                                    │   │
│  │                                                               │   │
│  │ Template Name: [Work Order - Corrective Maintenance    ]     │   │
│  │ Default Priority: [High ▾]                                    │   │
│  │ Assigned Team:    [Maintenance ▾]                             │   │
│  │ Description Template:                                         │   │
│  │ ┌─────────────────────────────────────────────────────────┐  │   │
│  │ │ {{equipment_id}} — {{deviation_type}}                   │  │   │
│  │ │ Detected: {{detected_at}}                               │  │   │
│  │ │ Root cause: {{root_cause}}                              │  │   │
│  │ │ Actions required: {{capa_steps}}                        │  │   │
│  │ └─────────────────────────────────────────────────────────┘  │   │
│  │                                                               │   │
│  │           [Cancel]  [💾 Save as v2.2]                        │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 6. Real-time (SignalR)

### Connection
React → `GET /api/negotiate` → gets URL + accessToken → `@microsoft/signalr` HubConnectionBuilder.

### Events and UI response

| SignalR Event | Payload | UI Reaction |
|---|---|---|
| `incident_created` | `{ incident_id, equipment_id, severity }` | Toast notification + new card in sidebar + new card in Operations |
| `incident_pending_approval` | `{ notification_id, incident_id, equipment_id, title, risk_level }` | Toast + bell unread badge increment + sidebar unread highlight + Operations card → "ACTION REQUIRED" |
| `incident_status_changed` | `{ incident_id, old_status, new_status }` | Update sidebar + update Incident Card header |
| `agent_step_completed` | `{ incident_id, step, result_summary }` | Update sidebar progress ("AI analyzing... step 3/4") |
| `incident_escalated` | `{ notification_id, incident_id, escalated_to, reason }` | Sidebar item → 🟡, bell unread badge increment, toast for qa-manager |
| `chat_response` | `{ incident_id, message, updated_analysis }` | Append to chat panel + refresh AI Analysis section |

### Reconnect
- `withAutomaticReconnect([0, 2000, 5000, 10000, 30000])` — aggressive reconnect
- On reconnect — refetch active incidents (stale data prevention)

### Unread notification state

- Backend API:
   - `GET /api/notifications?status=unread&limit=8` — dropdown feed
   - `GET /api/notifications/summary` — unread count + unread incident IDs
   - `POST /api/incidents/{id}/notifications/read` — acknowledge all visible notifications for the incident
- Read semantics: the incident is considered "reviewed" after opening the detail page, not just after opening the dropdown
- Browser alerts: `Notification.requestPermission()` is called only when the user clicks; after `granted` system notification is shown only when document is hidden/unfocused

---

## 7. Routing Map

```typescript
const routes = [
  // Public (pre-auth)
  { path: "/login",             element: <LoginPage /> },
  
  // Authenticated — wrapped in <AppShell>
  { path: "/",                  element: <OperationsDashboard />,  roles: ["operator", "qa-manager", "it-admin"] },
  { path: "/incidents/:id",     element: <IncidentDetail />,       roles: ["*"] },
  { path: "/history",           element: <IncidentHistory />,      roles: ["*"] },
  { path: "/manager",           element: <ManagerDashboard />,     roles: ["qa-manager", "it-admin"] },
  { path: "/templates",         element: <TemplateManagement />,   roles: ["it-admin"] },
];
```

**Fallback routing per role:**
- `operator` → `/` (Operations Dashboard)
- `qa-manager` → `/` (Operations Dashboard, shows all)  
- `maintenance-tech` → `/history` (closed incidents with WO focus)
- `auditor` → `/history` (full audit trail)
- `it-admin` → `/` (all incidents read-only)

---

## 8. State Management

### TanStack Query (React Query)
- **Incidents list:** `useQuery(['incidents', filters])` — with refetch at SignalR push
- **Incident detail:** `useQuery(['incident', id])` — with refetch at `incident_status_changed`
- **Incident events:** `useQuery(['incident-events', id])` — timeline
- **Stats:** `useQuery(['stats'])` — manager dashboard
- **Templates:** `useQuery(['templates'])` — IT admin

### Mutations
- `useMutation(['submit-decision'])` → `POST /api/incidents/{id}/decision`
- `useMutation(['update-template'])` → `PUT /api/templates/{id}`

### SignalR + React Query integration
SignalR callbacks → `queryClient.invalidateQueries(['incidents'])` for automatic refetch.

### Global State (React Context)
- `AuthContext` — MSAL account, roles, access token
- `SignalRContext` — connection instance, toast notifications queue

---

## 9. API Integration

### Backend endpoints mapping

| Frontend need | Method | Endpoint | Notes |
|---|---|---|---|
| List incidents | GET | `/api/incidents?status=&severity=&equipment=&page=` | Role-filtered server-side |
| Get incident detail | GET | `/api/incidents/{id}` | Includes `ai_analysis`, `workflow_state` |
| Get incident timeline | GET | `/api/incidents/{id}/events` | Array of audit events |
| Submit decision | POST | `/api/incidents/{id}/decision` | `{ action, reason?, question? }` |
| Get equipment | GET | `/api/equipment/{id}` | Equipment master data |
| Get batch | GET | `/api/batches/current/{equipment_id}` | Active batch |
| Get stats | GET | `/api/stats/summary` | Manager dashboard counters |
| List templates | GET | `/api/templates` | IT admin |
| Update template | PUT | `/api/templates/{id}` | IT admin |
| SignalR negotiate | GET | `/api/negotiate` | Returns `{ url, accessToken }` |

### Auth headers
All requests to the API go with the MSAL access token:
```
Authorization: Bearer <token>
```

`api/client.ts` is an axios instance with an interceptor that automatically adds a token through `acquireTokenSilent`.

---

## 10. Component tree

```
src/
├── main.tsx                          # MSAL + QueryClient + Router setup
├── App.tsx                           # Auth gate → LoginPage | AppShell
├── authConfig.ts                     # MSAL config (exists)
│
├── api/
│   ├── client.ts                     # Axios instance + auth interceptor
│   ├── incidents.ts                  # getIncidents, getIncident, getEvents, submitDecision
│   ├── equipment.ts                  # getEquipment, getBatch
│   ├── stats.ts                      # getStats
│   └── templates.ts                  # getTemplates, updateTemplate
│
├── types/
│   ├── incident.ts                   # Incident, AiAnalysis, WorkflowState, Evidence
│   ├── approval.ts                   # ApprovalTask, Decision, ChatMessage
│   ├── equipment.ts                  # Equipment, Batch
│   └── template.ts                   # Template
│
├── hooks/
│   ├── useAuth.ts                    # Current user, roles, token
│   ├── useSignalR.ts                 # SignalR connection + event handlers
│   ├── useIncidents.ts               # React Query hooks for incidents
│   └── useRoleGuard.ts              # Hook for role-based access check
│
├── components/
│   ├── Layout/
│   │   ├── AppShell.tsx              # Header + Sidebar + Main area + Router
│   │   ├── Header.tsx                # Brand, plant selector, user info, notifications
│   │   ├── Sidebar.tsx               # Navigation + Active Incidents list
│   │   └── ActiveIncidentItem.tsx    # Single item in sidebar incident list
│   │
│   ├── Incident/
│   │   ├── IncidentCard.tsx          # 2-column layout (info + approval panel)
│   │   ├── IncidentInfo.tsx          # Equipment, batch, product, stage, time
│   │   ├── ParameterExcursion.tsx    # Visual gauge bar (value vs NOR vs PAR)
│   │   ├── AiAnalysis.tsx            # Risk, confidence, classification, CAPA
│   │   ├── EvidenceCitations.tsx     # SOP references, historical cases
│   │   ├── DocumentPreviews.tsx      # WO draft + Audit entry draft
│   │   ├── BatchDisposition.tsx      # Batch status + recommended disposition
│   │   └── EventTimeline.tsx         # Vertical timeline of all events
│   │
│   ├── Approval/
│   │   ├── ApprovalPanel.tsx         # Sticky right panel: summary + buttons + chat
│   │   ├── DecisionButtons.tsx       # Approve / Reject buttons
│   │   ├── RejectModal.tsx           # Modal with reason textarea
│   │   ├── ConfidenceBanner.tsx      # LOW_CONFIDENCE warning banner
│   │   └── AgentChat.tsx             # Chat messages + input field
│   │
│   ├── IncidentList/
│   │   ├── OperationsCards.tsx       # Cards view for Operations Dashboard
│   │   ├── IncidentTable.tsx         # Table view for History page
│   │   ├── SeverityBadge.tsx         # Colored severity indicator
│   │   ├── StatusBadge.tsx           # Colored status indicator
│   │   └── Filters.tsx              # Search + filter controls
│   │
│   ├── Manager/
│   │   ├── StatsCards.tsx            # KPI counters (total, pending, escalated, resolved)
│   │   ├── EscalationQueue.tsx       # List of escalated incidents
│   │   ├── TrendsCharts.tsx          # Simple bar/line charts
│   │   └── RecentDecisions.tsx       # Table of recent operator decisions
│   │
│   └── Templates/
│       ├── TemplateList.tsx          # List of templates
│       └── TemplateEditor.tsx        # Edit form with save/cancel
│
├── pages/
│   ├── LoginPage.tsx                 # Microsoft SSO login (exists)
│   ├── OperationsDashboard.tsx       # Operations main page
│   ├── IncidentDetailPage.tsx        # Incident Card wrapper (fetches data)
│   ├── IncidentHistoryPage.tsx       # History + audit table
│   ├── ManagerDashboardPage.tsx      # Manager stats + escalation queue
│   ├── TemplateManagementPage.tsx    # Template editor
│   └── NotFoundPage.tsx              # 404
│
└── styles/
    ├── index.css                     # Global styles, CSS variables (colors, spacing)
    ├── login.css                     # Login page styles (exists)
    ├── layout.css                    # AppShell, header, sidebar
    ├── incident.css                  # Incident card, parameter excursion
    ├── approval.css                  # Approval panel, chat
    ├── table.css                     # Table styles, badges
    └── dashboard.css                 # Manager dashboard, stats cards
```

---

## 11. Design solutions and additions

### 11.1 Agent-generated incident title
Currently incidents have only ID and equipment_id. I suggest that the Foundry Orchestrator Agent generates a **short title** (up to 60 characters) for each incident. Examples:
- "Impeller Speed Deviation — Motor Load"
- "Coating Thickness Out of Spec"  
- "Inlet Temperature Spike During Drying"

This is required for the sidebar, tables, and notifications. Without a title, the operator must click on each incident to understand what happened.

**Implementation:** add `title` field to `DocumentAgentOutput` → store in `incidents` Cosmos document.

### 11.2 Chat as part of the audit (not optional)

Agreed - chat with agent **must be part of audit trail**. Each message is stored as an event in the `incidents` document → appears in the Timeline and is available to the auditor.

Events format for chat:
```json
{
  "timestamp": "2026-04-17T08:47:33Z",
  "actor": "ivan.petrenko",
  "actor_type": "human",
  "action": "operator_question",
  "details": "Can this affect batch integrity if speed was below PAR for < 5 min?"
}
```
```json
{
  "timestamp": "2026-04-17T08:48:01Z",
  "actor": "orchestrator-agent",
  "actor_type": "agent",
  "action": "agent_response",
  "details": "Per BPR-MET-500-v3.2 §3.4...",
  "updated_fields": ["capa_steps[0]"]
}
```

### 11.3 Agent progress steps in the sidebar

While the AI ​​is processing the incident, the sidebar shows the progress:
```
INC-2026-0043                     17 Apr, 15:55
   TB-102 · Coating thickness
   ● Step 2/4: Document Agent generating...
```

Steps:
1. Context enrichment
2. Research Agent (querying indexes)
3. Document Agent (generating analysis)
4. Ready for review

Received via SignalR `agent_step_completed` event.

### 11.4 Sidebar typography cleanup

Current design solution: Active Incidents sidebar should look like an operational queue, not like a list of normal links.

Findings:
- Emoji status icons create inconsistent font rendering and different line heights between OS/browsers. Replacing with CSS-dot makes the statuses equal and controllable.
- Mono font for `INC-YYYY-NNNN` in a dense list draws attention to the ID. It is better to use sans-serif bold for queue, and leave mono for tables/audit details, where ID is the primary artifact.
- Equipment and title should be stylistically separated: equipment as a short strong anchor, title as an auxiliary description with ellipsis.
- Status text should be bold and colored, but without underline/link affordance. Clickability gives the entire row hover/active state.
- Date should be muted and `tabular-nums` so that the time column does not "dance" when scrolling.

### 11.5 Notification bell + toast

Header → 🔔 badge with unread counter. Toast notifications for critical events:
- New incident assigned → orange toast
- Escalation → red toast
- Agent finished analysis → blue toast ("INC-0042 ready for your review")

### 11.6 Offline/degraded mode indicator

If SignalR disconnects, show banner: "⚠️ Live updates paused. Data may be stale. [Refresh]". With auto-reconnect.

### 11.7 Keyboard shortcuts (for an operator under pressure)

| Key | Action |
|---|---|
| `A` | Approve (requires confirmation) |
| `R` | Reject (opens reason modal) |
| `Q` | Focus chat input |
| `↑/↓` | Navigate incidents in sidebar |
| `Enter` | Open selected incident |

### 11.8 Adaptability for maintenance-tech

Maintenance tech sees a **simplified version** of the Incident Card:
- Only: Equipment info, Work Order (ready, with details), Timeline
- Does not see: AI Analysis details, Evidence Citations, Approval Panel
- Emphasis on: "What I need to do" (Work Order content)

### 11.9 CSV Export for Auditor

`/history` page → the "Export CSV" button generates a file with all filtered incidents. Includes:
- Incident ID, equipment, severity, status, risk_level, confidence
- Decision (approved/rejected), decision_by, decision_at, rejection_reason
- WO ID, AE ID, human_override flag
- Batch disposition (hold / conditional_release / released), disposition conditions

For GMP inspection readiness — the auditor can show this file to the inspector.

### 11.10 Batch Disposition Tracking

Batch disposition is a critical GMP artifact. After each decision of the batch statement, the status changes, and this is displayed:

1. **On the Incident Card** - the "Batch Disposition" section shows the current status and recommended AI
2. **In the Approval Panel** — the operator sees what will happen to the batch after approval/reject
3. **In Timeline** — each batch disposition change is recorded as an audit event
4. **In History table** — batch disposition column (for GMP inspectors)

**Communication with Execution Agent:**
- Document Agent generates `batch_disposition: "conditional_release"` + `disposition_conditions: ["extended sampling", "moisture recheck"]`
- After approval → Execution Agent updates `batches` container in Cosmos: `status → conditional_release`, `conditions → [...]`
- After reject → Execution Agent sets `batches.status → hold`
- Batch status change → SignalR event `batch_disposition_changed` → UI updates badge

**Why this is important for the demo:** The GMP inspector will ask "what happened to the batch after the deviation?" — and we can show a full trace: deviation → AI analysis → operator decision → batch hold/conditional release → conditions met → released.

### 11.11 Dark/Light mode

Operators often work in different lighting conditions. Dark theme support via CSS variables. Default: light. Toggle in the header.

---

## 12. MVP Scope vs Nice-to-have

### MVP (for demo submission — T-032, T-033)

| Feature | Priority | Satisfied |
|---|---|---|
| Login (MSAL) | ✅ Done | There is already |
| AppShell + Sidebar nav + role display | MUST | T-032 |
| Active Incidents sidebar list (live) | MUST | T-032 |
| Operations Dashboard (cards view) | MUST | T-032 |
| Incident Card (all 7 sections incl. Batch Disposition) | MUST | T-032 |
| Approval Panel (approve/reject) | MUST | T-033 |
| Agent Chat (more_info flow) | MUST | T-033 |
| Reject with reason modal | MUST | T-033 |
| LOW_CONFIDENCE banner | MUST | T-033 |
| SignalR real-time updates | MUST | T-030/T-033 |

### Should-have (T-034)

| Feature | Priority |
|---|---|
| History page with filters | HIGH |
| Audit Trail timeline (expandable) | HIGH |
| Manager Dashboard (stats + escalation) | HIGH |
| Template Management (IT Admin) | HIGH |
| Role-based route guards | HIGH |

### Nice-to-have (if there is time)

| Feature | Priority |
|---|---|
| CSV Export | MEDIUM |
| Keyboard shortcuts | MEDIUM |
| Trend charts (manager) | MEDIUM |
| Dark mode | LOW |
| Toast notifications queue | LOW |
| Mobile responsive | LOW |
| Agent progress steps in sidebar | MEDIUM |
| Notification bell with counter | LOW |

---

## Appendix: CSS Design Tokens

```css
:root {
  /* Brand */
  --color-brand: #1a73e8;
  --color-brand-dark: #1557b0;
  
  /* Severity */
  --color-critical: #d32f2f;
  --color-major: #f57c00;
  --color-moderate: #fbc02d;
  --color-minor: #66bb6a;
  
  /* Status */
  --color-pending: #f57c00;
  --color-analyzing: #1a73e8;
  --color-escalated: #fbc02d;
  --color-approved: #66bb6a;
  --color-rejected: #d32f2f;
  --color-closed: #9e9e9e;
  
  /* Confidence */
  --color-high-confidence: #66bb6a;
  --color-med-confidence: #f57c00;
  --color-low-confidence: #d32f2f;
  
  /* Layout */
  --sidebar-width: 280px;
  --header-height: 56px;
  --border-radius: 8px;
  --shadow-card: 0 1px 3px rgba(0, 0, 0, 0.12);
}
```
