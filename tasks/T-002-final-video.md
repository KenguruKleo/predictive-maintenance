# T-002 · Фінальне відео (до 10 хвилин)

← [04 · План дій](../04-action-plan.md) · [01 · Вимоги §9](../01-requirements.md#9-deliverables-по-фазах)

| Поле | Значення |
| --- | --- |
| **ID** | T-002 |
| **Пріоритет** | 🔴 CRITICAL |
| **Статус** | 🟡 IN PROGRESS |
| **Залежності** | [T-001](./T-001-architecture-presentation.md) (architecture slides), live demo (робочий додаток) |
| **Дедлайн** | 1-й тиждень травня 2026 |

---

## Чому це критично

> ⚡ **До 10 хвилин = рішення про top 10.**
> Judges повинні побачити **working demo**, а не тільки conceptual pitch. Тому відео будуємо навколо реального продукту, а не навколо анімації. Додатковий час використовуємо щоб показати глибину — editable AI drafts, AI vs Human agreement, feedback loop.

---

## Структура відео (до 10 хв = ~600 сек)

```text
[00:00–00:15]  HOOK
               Problem + value claim

[00:15–02:55]  LIVE DEMO — Operator workflow
               Dashboard (KPI cards, equipment health grid, Workflow Pipeline)
               → incident list AI Rec. column → bell → incident detail
               → summary → recommendation badge → evidence verification
               → batch disposition → CAPA actions
               → editable WO draft + audit entry draft (T-052)
               → approval actions → execution state (WO task + audit record created)
               → incident history + Workflow Pipeline tracking

[02:55–03:50]  CONFIDENCE GATE — три стани
               LOW_CONFIDENCE banner + mandatory comment
               BLOCKED state: пустий decision package, ручне заповнення

[03:50–05:15]  QA MANAGER VIEW + AUDIT + ADMIN
               Escalation queue → continue review
               Recent Decisions: AI Rec. badge, agreement KPI, infinite scroll (T-043, T-054)
               History filters + CSV export (з AI rec column) + telemetry + token usage

[05:15–06:30]  ARCHITECTURE SLIDE
               Track A, Durable orchestration, Foundry agents, MCP,
               Service Bus, Cosmos DB, AI Search, SignalR, Entra ID / RBAC
               Alert feedback loop до SCADA/MES при Reject (T-053)
               **Watchdog recovery:** Timer Trigger (5 хв) виявляє stuck/orphaned
               orchestrators → auto-requeue до Service Bus без втрати бізнес-контексту

[06:30–07:15]  IMPACT + CLOSE
               KPI + три-state confidence gate differentiator + GxP audit trail + closing
```

---

## Що саме повинно довести demo

- **Working product** — judges бачать не mock concept, а реальні role-based screens і incident states
- **Document & citation verification** — у decision package evidence явно розділене на **Verified** і **Unresolved**. Це закриває вимогу про separate document/citation verification
- **Human-in-the-loop** — operator може approve / reject / ask for more info; без людського рішення workflow не завершує CAPA execution
- **Editable AI drafts** (T-052) — оператор редагує WO і audit entry draft перед Approve; при BLOCKED стані форми пусті і **обов'язкові** — це GxP differentiator: людина підтверджує не просто "approve", а конкретний зміст документа
- **AI vs Human agreement** (T-054) — `AgentRecommendationBadge` і `AiVsHumanBadge` скрізь: у списку інцидентів, у Recent Decisions, в CSV export. Governance стає вимірюваним
- **Closed-loop actionability** — decision package показує batch disposition, CAPA actions, work order draft і audit entry draft ще до execution step
- **Post-approval execution visibility** — після Approve CAPA plan переходить у execution: система створює work order task і audit record, а цей перехід видно і в самому incident, і у **Workflow Pipeline** на головному екрані
- **RBAC** — різні ролі бачать різні surfaces: Operator, QA Manager, Auditor, IT Admin
- **Three-state confidence gate** — NORMAL / LOW_CONFIDENCE (banner + mandatory comment) / BLOCKED (empty forms + manual fill)
- **Real-time UX** — notification bell, unread state, escalation queue, consistent status colors across views
- **Long-running autonomy** — workflow може чекати 24h і більше без втрати стану, з escalation до QA
- **Traceability & observability** — status history, telemetry page, audit export, incident timeline, AI recommendations у CSV
- **Operational oversight** — manager surfaces show AI recommendation, AI confidence, response time, human override, agreement rate KPI
- **Infinite scroll** (T-043) — Recent Decisions підвантажує більше записів при скролі — показує що система масштабується на великі обсяги даних

---

## Повний inventory того, що можна показати на demo

### Operator

- Operations Dashboard з active incidents і status-based prioritization
- Incident Analytics table з period × status counts
- **Incident list — AI Rec. column** з `AgentRecommendationBadge` (APPROVE / REJECT label з кольором) (T-054)
- Notification bell з unread badge
- Sidebar з unread incident queue, timestamps, equipment, unread dot
- Footer live/offline indicator + active incident count
- Incident summary: equipment, batch, stage, parameter, measured value, limits, duration, severity
- Parameter excursion block
- **`AgentRecommendationBadge`** у decision package (APPROVE / REJECT icon + label) (T-054)
- AI recommendation: risk, confidence, classification, batch disposition, recommended action, root cause
- Evidence citations: document type, verified/unresolved status, relevance score, unresolved reason, deep link
- Batch Release Recommendation + disposition conditions
- CAPA actions list
- **Editable Work Order draft form** — оператор редагує поля (equipment, type, priority, title, description) (T-052)
- **Editable Audit entry draft form** — оператор редагує поля (deviation type, batch reference, action taken, comments) (T-052)
- **BLOCKED state: пусті форми, обов'язкові для заповнення, Approve disabled до заповнення** (T-052)
- Approve / Reject / Need More Info controls
- Agent conversation transcript / follow-up Q&A
- Low confidence banner when applicable
- Event timeline / status history
- Post-approval execution state with created work order task and audit record
- Decision summary after resolution

### QA Manager

- Manager Dashboard stats cards: total, pending, escalated, resolved
- **AI–Operator Agreement KPI** (% where operator agreed with AI recommendation) (T-054)
- Escalation Queue
- **Recent Decisions table**: AI Rec. (`AgentRecommendationBadge`), `AiVsHumanBadge` (agreement icon), AI confidence, human override, response time (T-054)
- **Infinite scroll** у Recent Decisions — scrolling loads next page automatically (T-043)
- Continue review on escalated incidents with full context preserved

### Auditor

- History & Audit table — **включає AI Rec. і agreement columns** (T-054)
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

### Optional backup only

- Browser popup notification
- Command palette demo
- Template editor deep dive
- E2E preview role switch

---

## Рекомендовані demo scenarios

### Main cut scenarios

1. **Operator happy path — full editable draft flow** (T-052)
    - Primary candidate: `INC-2026-0001` (GR-204, pending approval, medium risk, conditional release)
    - Show: dashboard → Workflow Pipeline → AI Rec. badge in incident list → bell → incident detail → `AgentRecommendationBadge` (APPROVE) → evidence (verified/unresolved) → batch disposition → CAPA actions → **edit WO draft fields** → **edit Audit entry fields** → Approve enabled → click Approve → incident enters `Execution` → work order task + audit record created → return to dashboard and show Workflow Pipeline `Execution`
    - Proves: AI recommendation is visible upfront, operator edits structured documents not just clicks OK, GxP traceability, and post-approval execution is observable end to end

2. **Follow-up question / Need More Info**
    - Show: recorded transcript або prepared follow-up response inside the same incident
    - Proves: human-in-the-loop is iterative, not only approve/reject

3. **BLOCKED state — mandatory form fill** (T-052)
    - Strong candidate: `INC-2026-0010` (BLOCKED, confidence `0.31`, no recommendation)
    - Show: incident з порожніми WO і audit entry forms, поля marked required, Approve button disabled; operator fills in mandatory fields → Approve becomes enabled
    - Proves: system enforces human accountability for decisions — người підписує конкретний документ, а не просто "клікає"

4. **Low confidence — mandatory comment**
    - Candidate: `INC-2026-0008` (`LOW_CONFIDENCE`, confidence ~0.55)
    - Show: warning banner + mandatory comment field before any decision
    - Proves: three-state confidence gate (NORMAL / LOW_CONFIDENCE / BLOCKED)

5. **QA escalation**
    - Primary candidate: `INC-2026-0007` (24h timeout escalation to QA Manager)
    - Show: escalated incident in Manager Dashboard / Escalation Queue
    - Proves: long-running workflow, timeout escalation, continuity of state

6. **Manager oversight — AI vs Human + infinite scroll** (T-043, T-054)
    - Show: Recent Decisions table з `AgentRecommendationBadge`, `AiVsHumanBadge` (✅ agreed / ⚠️ overridden), AI confidence, response time → scroll down to trigger next page load
    - Proves: measurable governance, infinite scroll scalability

7. **Auditor export + AI columns** (T-054)
    - Show: History & Audit з AI Rec. і agreement columns → Export CSV click
    - Proves: inspection readiness and auditability including AI recommendation tracking

8. **Admin telemetry**
    - Show: telemetry summary + token totals + trace/failure counters
    - Proves: observability, prompt traceability, token governance

### Setup checks before recording

- Verify one incident has clear **Verified** and **Unresolved** evidence rows
- Verify `INC-2026-0001` has `ai_analysis.work_order_draft` і `ai_analysis.audit_entry_draft` populated — inits the editable forms
- Verify after approving `INC-2026-0001` the incident shows execution events for work order + audit creation and appears in the Workflow Pipeline `Execution` stage
- Verify `INC-2026-0010` is in BLOCKED state з confidence ≤ 0.35 — forms empty, Approve disabled
- Verify one incident is in `escalated` state (`INC-2026-0007`)
- Verify Recent Decisions table has **more than 20 entries** щоб продемонструвати infinite scroll
- Verify telemetry for chosen admin incident contains trace items and token counts
- Verify a follow-up transcript exists, or record that scenario separately as its own take

---

## Технічні вимоги

| Параметр | Значення |
| --- | --- |
| Тривалість | ≤ 10:10 хвилин (hard limit) |
| Мова | **English** |
| Субтитри | Обов'язкові (judges можуть дивитись без звуку) |
| Формат | MP4 |
| Якість відео | ≥ 1080p |
| Розмір файлу | ≤ 500 MB |

---

## Інструменти для запису

| Роль | Інструмент | Нотатки |
| --- | --- | --- |
| Screen record + narration | OBS / Loom / QuickTime | Для demo сегментів |
| Монтаж | DaVinci Resolve (безкоштовно) / Camtasia | Зібрати кілька clean takes в один walkthrough |
| Субтитри | Auto-captions у DaVinci / Whisper | Перевірити вручну терміни GMP / CAPA / Foundry |
| Architecture slides | → [T-001](./T-001-architecture-presentation.md) | 1-2 щільні слайди, не більше |

---

## Recording notes

- Не записувати як один take. Краще 6-8 чистих сегментів і змонтувати їх в один безшовний flow
- Не витрачати час на live sign-in. Використати `e2e` auth mode і перемикати ролі між takes
- Основний happy path — один конкретний incident: **Granulator GR-204** (`INC-2026-0001`)
- Підготувати окремо: `INC-2026-0008` для LOW_CONFIDENCE beat, `INC-2026-0010` для BLOCKED beat, `INC-2026-0007` для QA escalation beat
- **Editable forms take**: seed `INC-2026-0001` повинен мати `work_order_draft` і `audit_entry_draft` в `ai_analysis` → перевірити перед записом
- **Infinite scroll take**: Recent Decisions повинна мати 20+ записів → перевірити seed або генерувати через `scripts/seed_cosmos.py`
- Якщо є prepared transcript, у happy path показати `Need More Info` loop як already recorded conversation, а не live typing
- Для manager beat показати `AiVsHumanBadge` — де ✅ (operator agreed) і ⚠️ (operator overrode AI). Краще мати мікс обох в Recent Decisions
- Для admin beat цілитись у incident з telemetry summary, де є `Prompt Tokens`, `Completion Tokens`, `Total Tokens`
- Optional only: browser popup notification. Не робити його критичним для фінального cut

---

## Optional popup beat

- Якщо стабільно працює під час запису: дати browser notification permission, переключити вікно і показати системний popup
- Якщо не стабільно: прибрати з фінального cut. In-app bell + unread highlight already sufficient

---

## Сценарій відео (по секундах, узгоджений з новим темпом)

| Час | Що на екрані | Що говоримо |
| --- | --- | --- |
| **00:00–00:07** | Title slide: `Sentinel Intelligence` + subtitle `GMP Deviation & CAPA Operations Assistant` | "In GMP manufacturing, one deviation can trigger thirty to sixty minutes of manual investigation." |
| **00:07–00:15** | Hook slide: `45 min -> < 2 min` + `Governed AI assistance` | "Sentinel Intelligence brings that below two minutes — end to end — with AI, human approval, and traceability at every step." |
| **00:15–00:50** | Operations Dashboard — прокрутити сторінку згори донизу: 4 KPI-картки (Total / Pending / Escalated / Resolved), двоколонковий блок (черга очікуючих рішень зліва + **Workflow Pipeline** справа з лічильниками Ingested → Analyzing → Execution), Equipment Health Grid з кольоровими плитками по кожному обладнанню (червоний = critical, синій = обробляється AI, зелений = OK), таблиця Incident Analytics, таблиця Recent Decisions внизу, footer з live-статусом. | "This is the live operations dashboard — the first screen every operator sees at shift start. The KPI cards show total active incidents, what is pending human review, what has escalated to QA, and what is resolved. In the center, the pending review queue sits beside the Workflow Pipeline, so the operator can see both what needs a decision and where each case sits in the end-to-end flow. The equipment health grid maps each asset by its worst status. Tracking active incidents is critical, which is why the left Active Incidents rail stays visible across screens. New incidents and status changes are highlighted there, so the operator is always aware when something changes. Incident Analytics and Recent Decisions complete the view." |
| **00:50–01:00** | Incident list — показати AI Rec. column з `AgentRecommendationBadge` (зелений APPROVE / червоний REJECT) і один resolved row, де видно human override recommendation. | "Notice that the AI recommendation is visible directly in the incident list — before the operator even opens the case. Each row shows the AI call, and resolved rows also show when the operator overrode it. Triage and governance start immediately." |
| **01:00–01:15** | Open bell dropdown, show unread sidebar item, click incident. | "A new incident appears in the bell and unread queue, then opens directly into the decision workflow for the operator." |
| **01:15–01:35** | Incident detail summary + parameter excursion. Pause on equipment, batch, measured value, limits. | "Notice that the operator does not see raw telemetry alone. They get the equipment, the affected batch, the measured value, the validated range, the duration, and the severity in one view. That is the context needed for a regulated decision." |
| **01:35–01:53** | `AgentRecommendationBadge` у decision package (APPROVE з іконкою). AI recommendation block — risk, confidence, classification, batch disposition. | "The recommendation is visible immediately with a clear APPROVE or REJECT label. Below that, the operator sees risk, confidence, classification, and the proposed batch disposition, so they can see both what the system suggests and how certain it is." |
| **01:53–02:15** | Evidence section. Hold on verified and unresolved evidence rows. | "This is one of the most important screens. Verified citations are grounded in retrieved source material, while unresolved items stay visibly unresolved, so the user can distinguish evidence from assumptions before approving anything in a regulated workflow." |
| **02:15–02:30** | Batch Release Recommendation + conditions. CAPA actions list. | "The system does not stop at diagnosis. It recommends the batch path with explicit conditions that must be met before release, and prepares the full CAPA action list." |
| **02:30–02:55** | **Editable WO draft form** — scroll to Work Order section, show editable fields (equipment, type, priority, title, description). Operator modifies one field (e.g., priority or description). | "This is where the changes the GxP story. The operator is not just clicking Approve on an AI output — they are editing and confirming the actual work order document. Every field is pre-populated by the AI from the incident context, but the operator owns the final content." |
| **02:55–03:15** | **Editable Audit entry draft form** — scroll to Audit section, show deviation type, batch reference, action taken, comments fields. | "Same pattern for the audit entry: AI fills the draft, operator reviews and confirms each field. Only when both forms are complete does the Approve button become active. This is a governed co-authorship model, not a rubber stamp." |
| **03:15–03:35** | Click Approve. Status changes to `Execution` → show incident status history / audit timeline with created work order task and audit record → jump back to dashboard Workflow Pipeline. | "Approval commits both drafts and immediately moves the CAPA plan into execution. At that point the system creates the work order task and audit record. We can track that transition inside the incident itself and from the Workflow Pipeline on the home screen." |
| **03:35–03:50** | Incident with `LOW_CONFIDENCE` banner (INC-2026-0008, confidence ~0.55). Show banner + mandatory comment field. | "When confidence falls below the threshold, the system shows a warning banner and requires the operator to leave a comment before deciding. The operator still decides — there is no automatic escalation. This is a governed co-pilot, not an override machine." |
| **03:50–04:15** | Pivot to `BLOCKED` state incident (INC-2026-0010, confidence 0.31). Show empty WO and audit forms with red required indicators. Approve button visibly disabled. Operator fills mandatory field → Approve becomes enabled. | "When the AI pipeline cannot produce a grounded result at all, the state is different: the recommendation is withheld entirely and both document forms are empty, with every mandatory field marked required. The operator cannot approve until those fields are filled. This is not a bypass — it is an enforcement point." |
| **04:15–04:35** | QA Manager view: Manager Dashboard → stats cards → **AI–Operator Agreement KPI widget**. | "If the incident is not handled in time, the workflow escalates to QA with the full context preserved. At the top of the manager dashboard you can see the AI–operator agreement rate — in this session, operators agreed with the AI recommendation eighty-three percent of the time. That is a measurable governance signal." |
| **04:35–05:00** | Escalation Queue → Recent Decisions table. Show `AgentRecommendationBadge` column, `AiVsHumanBadge` (✅ agreed / ⚠️ overridden), AI confidence, response time. | "The Recent Decisions table shows every resolved case with the AI recommendation, whether the operator agreed or overridden it, AI confidence, and response time. Governance is now measurable at a glance." |
| **05:00–05:15** | Scroll down у Recent Decisions — показати loading spinner, нові рядки завантажуються (infinite scroll). | "The table uses infinite scroll to load additional records on demand — this same view scales to hundreds of decisions without pagination clicks." |
| **05:15–05:30** | Auditor view: History & Audit table з AI Rec. і agreement columns. Click `Export CSV`. | "For auditors, the incident log includes the AI recommendation and agreement status in every row and is exportable in one click. That makes the full audit set — including AI outputs — available for offline review." |
| **05:30–05:45** | IT Admin view: Incident Telemetry summary з trace counters і token totals. | "Administrators can inspect trace counts, failures, rounds, duration, and token usage for each incident. This is the operational layer for troubleshooting prompts, agent runs, and cost-related governance." |
| **05:45–06:00** | Architecture slide reveal step 1: Track A + two-level orchestration. | "This is Track A: GitHub, Azure, and Azure AI Foundry. The architecture has two separate orchestration levels: Durable Functions handle the stateful workflow — incident creation, HITL pause, retry, and escalation. Azure AI Foundry handles AI reasoning — research, synthesis, and tool calls. Each level has a distinct responsibility." |
| **06:00–06:20** | Architecture slide reveal step 2: Service Bus, Cosmos DB, AI Search, SignalR, MCP, Entra ID, CI/CD. | "AI Search grounds answers in validated documents. Service Bus absorbs alert bursts. Cosmos stores durable state. SignalR pushes real-time updates. MCP keeps integrations pluggable. Security runs on PIM just-in-time access, Conditional Access with MFA, and Defender for Cloud. The Foundry eval gate in CI/CD blocks any deployment where AI quality regresses." |
| **06:20–06:30** | Architecture slide highlight: alert feedback loop arrow from Reject back to SCADA/MES. | "When an operator rejects a recommendation, the operator-agrees-with-agent flag and the rejection reason are recorded and flow back toward the source system. Every decision enriches the operational record — this is a closed-loop, not a one-way advisory." |
| **06:30–06:50** | KPI slide: before/after numbers + three-state confidence gate summary. | "The result is a production-ready pattern for pharma operations: faster deviation handling, standardized decision support, and full traceability for regulated environments. The three-state confidence gate — normal, low confidence, and blocked — means the system never fabricates a confident answer when it cannot be grounded." |
| **06:50–07:05** | Closing product screenshot або KPI slide. | "Instead of chasing documents and approvals manually, operators get a governed decision package in minutes, with evidence, actions, and next steps already structured — and with editable drafts that make every approval a confirmed human act, not just a click." |
| **07:05–07:15** | Final branded closing frame. | "This is Sentinel Intelligence, built for governed pharma operations at scale." |

### Delivery notes

- Тримати паузу 1-2 секунди на `Verified` / `Unresolved` badges, `AgentRecommendationBadge`, і `AiVsHumanBadge` — щоб judges встигли прочитати
- Не показувати live login, role switching або технічні transition steps. Ролі змінювати між takes і зводити в монтажі
- **Editable forms beat (02:30–03:15)** — найважливіший новий beat. Треба щоб seed incident `INC-2026-0001` мав `ai_analysis.work_order_draft` і `ai_analysis.audit_entry_draft` populated. Показати саме редагування, а не просто скрол
- **Execution beat (03:15–03:35)** — після Approve затриматись на incident timeline / status history, щоб було видно створення work order task і audit record, потім коротко повернутись на dashboard і показати incident у Workflow Pipeline `Execution`
- **BLOCKED beat (03:50–04:15)** — `INC-2026-0010` повинен бути в стані де Approve disabled. Показати момент коли оператор заповнює одне поле і Approve стає enabled — це drama moment
- **Infinite scroll beat (05:00–05:15)** — переконатись що є 20+ записів у Recent Decisions. Scroll повільно, щоб spinner був видимий
- `operator_agrees_with_agent` прапор записується при Approve і Reject. `AiVsHumanBadge` показує цей результат. Якщо є час — показати reject path де badge стає ⚠️
- На architecture slide робити поетапне reveal у 3 кроки: orchestration → services → feedback loop
- Якщо approval click ламає pacing, можна показати available actions і audit timeline окремим cut замість live click

---

## Definition of Done

- [ ] Повний сценарій (script) написаний та схвалений командою
- [ ] [T-001](./T-001-architecture-presentation.md) architecture slides готові
- Покадровий таймінг dry-run перевірений: narration вкладається в 7:15 без поспіху (запас ~3 хв на монтажні паузи та transitions)
- [ ] Підготовлено мінімум 5 demo states: operator happy path + editable drafts, LOW_CONFIDENCE, BLOCKED mandatory fill, QA escalation, auditor/admin traceability
- [ ] Evidence verification state (**verified** vs **unresolved**) чітко видно у recorded demo
- [ ] **Editable WO та Audit entry forms** показані з реальним редагуванням поля (T-052)
- [ ] Після Approve показано перехід у `Execution`: створення work order task + audit record, видимо і в incident, і у Workflow Pipeline
- [ ] **BLOCKED state** показує Approve disabled → оператор заповнює → Approve enabled (T-052)
- [ ] **`AgentRecommendationBadge`** видно в incident list і в decision package (T-054)
- [ ] **`AiVsHumanBadge`** видно в Recent Decisions (T-054)
- [ ] **AI–Operator Agreement KPI** видно в Manager Dashboard (T-054)
- [ ] **Infinite scroll** у Recent Decisions показано (scroll → spinner → нові рядки) (T-043)
- [ ] Live demo записаний clean segments для монтажу
- [ ] Відео змонтовано в єдиний файл
- [ ] Субтитри додані та перевірені
- [ ] Тривалість ≤ 10:10
- [ ] Переглянуто командою та схвалено
- [ ] Завантажено на платформу хакатону до дедлайну

---

← [04 · План дій](../04-action-plan.md) · [T-001 Архітектура](./T-001-architecture-presentation.md)
