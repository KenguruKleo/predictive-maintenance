# Frontend Design Document — Sentinel Intelligence

← [README](../README.md) · [02 Архітектура](../02-architecture.md) · [T-032](../tasks/T-032-frontend-core.md) · [T-033](../tasks/T-033-frontend-approval.md) · [T-034](../tasks/T-034-frontend-other-roles.md)

> **Дата:** 17 квітня 2026  
> **Стек:** React 19 + Vite 8 + TypeScript 6 + TanStack Query + MSAL React  
> **Deploy:** Azure Static Web Apps  
> **Auth:** Azure Entra ID (MSAL v5, redirect flow)

---

## Зміст

1. [Загальна філософія](#1-загальна-філософія)
2. [Інформаційна архітектура](#2-інформаційна-архітектура)
3. [Ролі та доступ](#3-ролі-та-доступ)
4. [Layout та навігація](#4-layout-та-навігація)
5. [Сторінки та екрани](#5-сторінки-та-екрани)
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
10. [Компонентне дерево](#10-компонентне-дерево)
11. [Дизайн-рішення та доповнення](#11-дизайн-рішення-та-доповнення)
12. [MVP Scope vs Nice-to-have](#12-mvp-scope-vs-nice-to-have)

---

## 1. Загальна філософія

- **Operational-first:** UI оптимізований для оператора під тиском часу. Мінімум кліків до рішення.
- **Audit-ready:** кожна дія записується і візуалізується. Аудитор бачить повний trace без зайвих переходів.
- **Role-aware:** один додаток, але кожна роль бачить тільки те, що потрібно. Sidebar навігація адаптується під роль.
- **Real-time:** SignalR push-нотифікації. Нові інциденти з'являються без рефрешу. Статуси оновлюються live.
- **GMP-compliant UX:** чіткий візуальний поділ між AI-рекомендацією та людським рішенням. Confidence gate видимий.

---

## 2. Інформаційна архітектура

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

### Ключові сутності

| Сутність | Опис | Cosmos Container |
|---|---|---|
| **Incident** | Інцидент: alert → enrichment → AI analysis → decision → execution | `incidents` |
| **Approval Task** | Таск для оператора: decision package + approve/reject/more_info | `approval-tasks` |
| **Work Order** | Наряд на виправлення (створюється після approval) | `approval-tasks` (execution_result) |
| **Audit Entry** | Запис аудиту (GMP compliance) | `approval-tasks` (execution_result) |
| **Equipment** | Обладнання (GR-204, TB-102, FBD-301) | `equipment` |
| **Batch** | Виробнича партія | `batches` |
| **Template** | Шаблон документа (work order, audit entry) | `approval-tasks` (template_id ref) |

---

## 3. Ролі та доступ

> 5 ролей визначені в Azure Entra ID (T-035). Роль приходить у JWT access token → `roles` claim.

| Роль | Sidebar | Operational | Incident Card | Approval | History | Manager | Templates |
|---|---|---|---|---|---|---|---|
| **operator** | ✅ Active incidents | ✅ (свої) | ✅ Read + Decision | ✅ Approve/Reject/Chat | ✅ (свої) | ❌ | ❌ |
| **qa-manager** | ✅ All incidents | ✅ (всі) | ✅ Read + Decision | ✅ (escalated + override) | ✅ (всі) | ✅ | ❌ |
| **maintenance-tech** | ✅ Closed incidents | ❌ | ✅ Read-only (WO focus) | ❌ | ✅ (read-only) | ❌ | ❌ |
| **auditor** | ❌ | ❌ | ✅ Read-only (audit focus) | ❌ | ✅ (всі, export) | ❌ | ❌ |
| **it-admin** | ✅ All incidents | ✅ (всі, read-only) | ✅ Read-only | ❌ | ✅ (всі) | ✅ (stats) | ✅ Edit |

### Правила видимості

- **Operator** бачить тільки інциденти, де `assigned_to === currentUser` або ще не призначені
- **QA Manager** бачить всі інциденти + ескальовані (де таймаут минув або `confidence < 0.7`)
- **Maintenance Tech** бачить тільки approved/closed інциденти (фокус на Work Orders)
- **Auditor** бачить тільки History/Audit view — повний trail усіх інцидентів
- **IT Admin** бачить все read-only + може редагувати Templates

---

## 4. Layout та навігація

### AppShell — загальний layout

```
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

### Sidebar — дві частини

**Верхня: навігація** (адаптивна під роль)

| Пункт | Route | Ролі |
|---|---|---|
| 📋 Operations | `/` | operator, qa-manager, it-admin |
| 📂 History & Audit | `/history` | all |
| 📊 Manager Dashboard | `/manager` | qa-manager, it-admin |
| 📄 Templates | `/templates` | it-admin |

**Нижня: Active Incidents** — live-список активних інцидентів

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

Кожен елемент показує:
- **Номер інциденту** (INC-YYYY-NNNN)
- **Коротка назва** — генерується AI (Foundry Orchestrator Agent повинен генерувати `title` field)
- **Обладнання** (equipment_id)
- **Дата/час** — праворуч у header рядку, `tabular-nums`, muted
- **Статус-індикатор** — CSS-dot, не emoji, щоб не змішувати системні emoji fonts з UI typography:

| Статус | Dot color | Текст |
|---|---|---|
| `open` | blue | Open |
| `ingested` | blue | Ingesting... |
| `analyzing` | blue | AI analyzing... |
| `pending_approval` | orange | Awaiting decision |
| `escalated` | yellow | Escalated to QA Manager |
| `approved` | green | Approved, executing... |
| `rejected` | red | Rejected |
| `closed` | gray | Closed |

**Типографіка sidebar item:**
- incident number: sans-serif, 12px, 700; не використовувати mono як основний шрифт у списку, бо він читається як debug ID
- equipment: 13px, 650/700, `text-heading`
- title: 12px, muted, ellipsis
- status: 12px, 700, colored by status
- уникати emoji у статусах; вони рендеряться іншим font stack і візуально “ламають” рядок

Клік на інцидент → відкриває Incident Card у main area.

---

## 5. Сторінки та екрани

### 5.1 Operational Dashboard (Operator)

**Route:** `/`  
**Ролі:** operator, qa-manager, it-admin  
**Суть:** головний екран оператора. Показує тільки **активні** інциденти (не closed) що потребують уваги.

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

**Поведінка:**
- Сортування: `pending_approval` → `escalated` → `analyzing` → `ingested` → інші
- Карточки з'являються real-time через SignalR
- Для оператора: показує тільки `assigned_to === me`
- Для qa-manager: показує всі + окрема секція "Escalated to You"
- "View & Decide →" → відкриває `/incidents/{id}` з Approval Panel

---

### 5.2 Incident Card (Detail)

**Route:** `/incidents/{id}`  
**Ролі:** all (з різним рівнем доступу)

Основна сторінка інциденту. Layout — **2 колонки** (або tabs на мобільному):

```
┌──────────────────────────────────────────────────────────────────────┐
│  ← Back    INC-2026-0042 · Impeller Speed Deviation                  │
│  Status: 🟠 PENDING APPROVAL          Equipment: GR-204              │
├──────────────────────────┬───────────────────────────────────────────┤
│  LEFT COLUMN (60%)       │  RIGHT COLUMN (40%)                       │
│                          │                                           │
│  ┌────────────────────┐  │  ┌─────────────────────────────────────┐ │
│  │ INCIDENT INFO      │  │  │ APPROVAL PANEL                     │ │
│  │ Equipment: GR-204  │  │  │ (або Agent Chat якщо                │ │
│  │ Batch: BPR-0042    │  │  │  вже прийнято рішення)             │ │
│  │ Product: Metformin  │  │  │                                    │ │
│  │ Stage: Wet Gran.   │  │  │ → Блок 5.3 нижче                  │ │
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

### Секції Incident Card

#### 1. Incident Info
Базова інформація: equipment, batch, product, виробничий етап, час, оператор.

#### 2. Parameter Excursion
Візуальна шкала: measured value vs NOR (Normal Operating Range) vs PAR (Proven Acceptable Range). Чіткий показ чи параметр вийшов за NOR але ще в PAR, чи вже за PAR.

#### 3. AI Analysis
Risk level (HIGH/MEDIUM/LOW + LOW_CONFIDENCE), confidence bar, deviation classification, root cause hypothesis, CAPA steps recommendation.

#### 4. Evidence Citations
SOP references, historical similar cases, GMP clauses — з clickable посиланнями.

#### 5. Documents (Work Order + Audit Entry drafts)
Попередньо заповнені чернетки документів що створить Execution Agent після approval. Оператор може переглянути що буде створено.

#### 6. Batch Disposition
Після approval batch змінює статус. Секція показує поточний і рекомендований disposition:

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

| Status | Колір | Опис |
|---|---|---|
| `in_production` | 🟢 green | Batch у виробництві, все ОК |
| `hold` | 🔴 red | Batch зупинено (критична девіація або reject) |
| `conditional_release` | 🟡 yellow | Випуск з умовами (додаткове тестування) |
| `released` | 🟢 green | Підтверджено після виконання умов |
| `rejected` | ⚫ black | Batch забракований |

**Логіка зміни статусу:**
- Operator approves + AI рекомендує conditional release → batch → `conditional_release`
- Operator approves + AI рекомендує full release → batch → `released`
- Operator rejects → batch → `hold` (потребує QA Manager review)
- LOW_CONFIDENCE + escalation → batch → `hold` (авто-hold до рішення QA)

**Implementation:** Document Agent генерує `batch_disposition` field у `DocumentAgentOutput`. Execution Agent оновлює статус batch в Cosmos `batches` container після approval.

#### 7. Timeline / Audit Trail
Хронологічний лог усіх подій інциденту. GMP audit-ready формат. Кожен запис: timestamp, actor (system/agent/human), action, result.

#### Різниця залежно від ролі

| Роль | Що бачить | Approval Panel |
|---|---|---|
| operator | All sections + Approval Panel | ✅ Active (якщо assigned) |
| qa-manager | All sections + Approval Panel | ✅ Active (escalated / override) |
| maintenance-tech | Incident Info + Documents + Timeline | ❌ Read-only, WO focus |
| auditor | All sections (read-only) + Timeline | ❌ Read-only |
| it-admin | All sections (read-only) | ❌ Read-only |

---

### 5.3 Approval Panel + Chat

**Location:** Права колонка на Incident Card (sticky, scrolls independently).  
**Видимість:** тільки operator та qa-manager, тільки коли `status === pending_approval` і інцидент assigned.

#### Approval Panel (коли AI закінчив аналіз)

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

#### Chat з агентом (Agent Conversation)

Chat панель **вбудована нижче кнопок** (або замість них після прийняття рішення). Це **не опціонально** — це частина аудиту. Кожне питання оператора і відповідь агента записуються в timeline incident.

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

**Логіка чату:**
1. Оператор вводить питання → `POST /api/incidents/{id}/decision` з `action: "more_info"` і `question: "..."` 
2. Backend: Durable orchestrator отримує event → re-run `run_foundry_agents` з додатковим контекстом (оператор запитує X)
3. Agent може оновити documents (WO draft, audit entry draft, CAPA steps) → оновлення приходить через SignalR
4. Оновлений AI Analysis відображається зліва, а в чаті з'являється відповідь агента
5. Кнопки Approve/Reject залишаються доступними — оператор може прийняти рішення у будь-який момент

**Reject flow:**
- Clicking "Reject" → модальне вікно з обов'язковим полем "Reason for rejection" (textarea, min 10 chars)
- Reason зберігається в audit trail

**After decision:** chat-панель стає read-only, показує повну історію переписки як частину аудиту.

---

### 5.4 Incident History + Audit

**Route:** `/history`  
**Ролі:** all (з різним обсягом даних)

Це головний **ретроспективний view** — для аудиторів, менеджерів, і операторів що хочуть подивитись минулі інциденти.

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

**Особливості:**
- **Full-text search** по номеру, назві, equipment, batch
- **Фільтри:** status (multi-select), severity, equipment, date range
- **Сортування:** по даті (default desc), severity, status
- **Export CSV:** для auditor — всі відфільтровані записи
- Click на рядок → `/incidents/{id}` (Incident Card)

**Audit Trail view (expandable row або tab):**

При кліку на інцидент в History, окрім переходу на Incident Card, auditor може розгорнути inline timeline:

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
**Ролі:** qa-manager, it-admin

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

**Цінність для demo:** показує "управлінський" рівень — QA Manager бачить повну картину, ескалації, і може скоригувати рішення.

---

### 5.6 Template Management (IT Admin)

**Route:** `/templates`  
**Ролі:** it-admin only

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

### Підключення
React → `GET /api/negotiate` → отримує URL + accessToken → `@microsoft/signalr` HubConnectionBuilder.

### Events та реакція UI

| SignalR Event | Payload | UI Reaction |
|---|---|---|
| `incident_created` | `{ incident_id, equipment_id, severity }` | Toast notification + new card in sidebar + new card in Operations |
| `incident_pending_approval` | `{ incident_id, equipment_id, risk_level }` | Sidebar item → 🟠, Operations card → "ACTION REQUIRED" |
| `incident_status_changed` | `{ incident_id, old_status, new_status }` | Update sidebar + update Incident Card header |
| `agent_step_completed` | `{ incident_id, step, result_summary }` | Update sidebar progress ("AI analyzing... step 3/4") |
| `incident_escalated` | `{ incident_id, escalated_to, reason }` | Sidebar item → 🟡, toast for qa-manager |
| `chat_response` | `{ incident_id, message, updated_analysis }` | Append to chat panel + refresh AI Analysis section |

### Reconnect
- `withAutomaticReconnect([0, 2000, 5000, 10000, 30000])` — aggressive reconnect
- На reconnect — refetch active incidents (stale data prevention)

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
- **Incidents list:** `useQuery(['incidents', filters])` — з refetch при SignalR push
- **Incident detail:** `useQuery(['incident', id])` — з refetch при `incident_status_changed`
- **Incident events:** `useQuery(['incident-events', id])` — timeline
- **Stats:** `useQuery(['stats'])` — manager dashboard
- **Templates:** `useQuery(['templates'])` — IT admin

### Mutations
- `useMutation(['submit-decision'])` → `POST /api/incidents/{id}/decision`
- `useMutation(['update-template'])` → `PUT /api/templates/{id}`

### SignalR + React Query integration
SignalR callbacks → `queryClient.invalidateQueries(['incidents'])` для автоматичного refetch.

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
Всі запити до API йдуть з MSAL access token:
```
Authorization: Bearer <token>
```

`api/client.ts` — axios instance з interceptor що автоматично додає token через `acquireTokenSilent`.

---

## 10. Компонентне дерево

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

## 11. Дизайн-рішення та доповнення

### 11.1 Agent-generated incident title
Зараз інциденти мають тільки ID і equipment_id. Пропоную щоб Foundry Orchestrator Agent генерував **короткий title** (до 60 символів) для кожного інциденту. Приклади:
- "Impeller Speed Deviation — Motor Load"
- "Coating Thickness Out of Spec"  
- "Inlet Temperature Spike During Drying"

Це потрібно для sidebar, таблиць, і notifications. Без title оператор повинен клікнути кожен інцидент щоб зрозуміти що сталось.

**Implementation:** додати `title` field до `DocumentAgentOutput` → зберігати в `incidents` документі Cosmos.

### 11.2 Chat як частина аудиту (не опціонально)

Згоден — чат з агентом **повинен бути частиною audit trail**. Кожне повідомлення зберігається як event в `incidents` document → з'являється в Timeline і доступне auditor.

Формат events для чату:
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

### 11.3 Agent progress steps у sidebar

Поки AI обробляє інцидент, у sidebar показувати прогрес:
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

Отримуємо через SignalR `agent_step_completed` event.

### 11.4 Sidebar typography cleanup

Поточне дизайн-рішення: Active Incidents sidebar має виглядати як operational queue, не як список звичайних links.

Findings:
- Emoji status icons створюють неузгоджений font rendering і різну висоту рядків між OS/browser. Заміна на CSS-dot робить статуси рівними і контрольованими.
- Mono-шрифт для `INC-YYYY-NNNN` у щільному списку перетягує увагу на ID. Для queue краще sans-serif bold, а mono лишати для таблиць/audit details, де ID є primary artifact.
- Equipment і title треба стилістично розділяти: equipment як короткий сильний якір, title як допоміжний опис з ellipsis.
- Status text має бути bold і colored, але без underline/link affordance. Клікабельність дає весь row hover/active state.
- Date має бути muted і `tabular-nums`, щоб колонка часу не “танцювала” при скролі.

### 11.5 Notification bell + toast

Header → 🔔 badge з лічильником непрочитаних. Toast notifications для критичних подій:
- New incident assigned → orange toast
- Escalation → red toast
- Agent finished analysis → blue toast ("INC-0042 ready for your review")

### 11.6 Offline/degraded mode indicator

Якщо SignalR disconnect — показувати banner: "⚠️ Live updates paused. Data may be stale. [Refresh]". З auto-reconnect.

### 11.7 Keyboard shortcuts (для оператора під тиском)

| Key | Action |
|---|---|
| `A` | Approve (requires confirmation) |
| `R` | Reject (opens reason modal) |
| `Q` | Focus chat input |
| `↑/↓` | Navigate incidents in sidebar |
| `Enter` | Open selected incident |

### 11.8 Адаптивність для maintenance-tech

Maintenance tech бачить **спрощену версію** Incident Card:
- Тільки: Equipment info, Work Order (готовий, з деталями), Timeline
- Не бачить: AI Analysis details, Evidence Citations, Approval Panel
- Акцент на: "Що мені потрібно зробити" (Work Order content)

### 11.9 CSV Export для Auditor

`/history` page → кнопка "Export CSV" генерує файл з усіма відфільтрованими інцидентами. Включає:
- Incident ID, equipment, severity, status, risk_level, confidence
- Decision (approved/rejected), decision_by, decision_at, rejection_reason
- WO ID, AE ID, human_override flag
- Batch disposition (hold / conditional_release / released), disposition conditions

Для GMP inspection readiness — auditor може показати цей файл інспектору.

### 11.10 Batch Disposition Tracking

Batch disposition — критично важливий GMP артефакт. Після кожного рішення оператора batch змінює статус, і це відображається:

1. **На Incident Card** — секція "Batch Disposition" показує поточний статус і рекомендований AI
2. **В Approval Panel** — оператор бачить що станеться з batch після approval/reject
3. **В Timeline** — кожна зміна batch disposition записується як audit event
4. **В History table** — колонка batch disposition (для GMP інспекторів)

**Зв'язок з Execution Agent:**
- Document Agent генерує `batch_disposition: "conditional_release"` + `disposition_conditions: ["extended sampling", "moisture recheck"]`
- Після approval → Execution Agent оновлює `batches` container в Cosmos: `status → conditional_release`, `conditions → [...]`
- Після reject → Execution Agent ставить `batches.status → hold`
- Зміна batch status → SignalR event `batch_disposition_changed` → UI оновлює badge

**Чому це важливо для demo:** GMP інспектор запитає "що сталось з batch після девіації?" — і ми можемо показати повний trace: deviation → AI analysis → operator decision → batch hold/conditional release → conditions met → released.

### 11.11 Dark/Light mode

Оператори часто працюють в різних умовах освітлення. Підтримка темної теми через CSS variables. Default: light. Toggle в header.

---

## 12. MVP Scope vs Nice-to-have

### MVP (для demo submission — T-032, T-033)

| Feature | Priority | Задоволено |
|---|---|---|
| Login (MSAL) | ✅ Done | Вже є |
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

### Nice-to-have (якщо є час)

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
