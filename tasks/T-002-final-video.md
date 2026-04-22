# T-002 · Фінальне відео (5 хвилин)

← [04 · План дій](../04-action-plan.md) · [01 · Вимоги §9](../01-requirements.md#9-deliverables-по-фазах)

| Поле | Значення |
| --- | --- |
| **ID** | T-002 |
| **Пріоритет** | 🔴 CRITICAL |
| **Статус** | 🔜 TODO |
| **Залежності** | [T-001](./T-001-architecture-presentation.md) (architecture slides), live demo (робочий додаток) |
| **Дедлайн** | 1-й тиждень травня 2026 |

---

## Чому це критично

> ⚡ **5 хвилин = рішення про top 10.**
> Judges повинні побачити **working demo**, а не тільки conceptual pitch. Тому відео будуємо навколо реального продукту, а не навколо анімації.

---

## Структура відео (5 хв = 300 сек)

```text
[00:00–00:15]  HOOK
               Problem + value claim

[00:15–02:20]  LIVE DEMO — Operator workflow
               Dashboard → bell → unread queue → incident detail
               → summary → recommendation → evidence verification
               → batch disposition → CAPA/work order/audit drafts
               → follow-up Q&A → approval actions → status history

[02:20–02:50]  SAFE FAILURE STATE
               waiting/manual-review state instead of fabricated answer

[02:50–03:25]  QA MANAGER VIEW
               Escalation queue + recent decisions + override/response metrics

[03:25–03:55]  AUDITOR / IT ADMIN VIEW
               History filters + CSV export + telemetry + token usage

[03:55–04:20]  ARCHITECTURE SLIDE
               Track A, Durable orchestration, Foundry agents, MCP,
               Service Bus, Cosmos DB, AI Search, SignalR, Entra ID / RBAC

[04:20–05:00]  IMPACT + CLOSE
               KPI + regulated workflow value + closing brand frame
```

---

## Що саме повинно довести demo

- **Working product** — judges бачать не mock concept, а реальні role-based screens і incident states
- **Document & citation verification** — у decision package evidence явно розділене на **Verified** і **Unresolved**. Це закриває вимогу про separate document/citation verification
- **Human-in-the-loop** — operator може approve / reject / ask for more info; без людського рішення workflow не завершує CAPA execution
- **Closed-loop actionability** — decision package показує batch disposition, CAPA actions, work order draft і audit entry draft ще до execution step
- **RBAC** — різні ролі бачать різні surfaces: Operator, QA Manager, Auditor, IT Admin
- **Safe failure behavior** — якщо agent conclusion не готовий або не grounded, UI не вигадує відповідь і не маскує невизначеність
- **Real-time UX** — notification bell, unread state, escalation queue, consistent status colors across views
- **Long-running autonomy** — workflow може чекати 24h і більше без втрати стану, з escalation до QA
- **Traceability & observability** — status history, telemetry page, audit export, incident timeline
- **Operational oversight** — manager surfaces already show recent decisions, AI confidence, response time, and human override signals

---

## Повний inventory того, що можна показати на demo

### Operator

- Operations Dashboard з active incidents і status-based prioritization
- Incident Analytics table з period × status counts
- Notification bell з unread badge
- Sidebar з unread incident queue, timestamps, equipment, unread dot
- Footer live/offline indicator + active incident count
- Incident summary: equipment, batch, stage, parameter, measured value, limits, duration, severity
- Parameter excursion block
- AI recommendation: risk, confidence, classification, batch disposition, recommended action, root cause
- Evidence citations: document type, verified/unresolved status, relevance score, unresolved reason, deep link
- Batch Release Recommendation + disposition conditions
- CAPA actions list
- Work order draft
- Audit entry draft
- Approve / Reject / Need More Info controls
- Agent conversation transcript / follow-up Q&A
- Low confidence banner when applicable
- Event timeline / status history
- Decision summary after resolution

### QA Manager

- Manager Dashboard stats cards: total, pending, escalated, resolved
- Escalation Queue
- Recent Decisions table with AI confidence, human override, response time
- Continue review on escalated incidents with full context preserved

### Auditor

- History & Audit table
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

1. **Operator happy path**
    - Primary candidate: `INC-2026-0001` (GR-204, pending approval, medium risk, conditional release)
    - Backup candidate: `INC-2026-0006` (MIX-102, pending approval, conditional release)
    - Show: dashboard → bell → incident detail → recommendation → verified/unresolved evidence → batch disposition → CAPA/work order/audit drafts
    - Proves: end-to-end flow, AI Fit, explainability, closed-loop actionability

2. **Follow-up question / Need More Info**
    - Show: recorded transcript or prepared follow-up response inside the same incident
    - Proves: human-in-the-loop is iterative, not only approve/reject

3. **Safe failure / withheld output**
    - Strong candidate: `INC-2026-0010` (BLOCKED, confidence `0.31`, no recommendation, auto-escalated by policy)
    - Show: incident with no final recommendation yet, explicit waiting/manual-review state
    - Proves: system does not fabricate unsafe output

4. **QA escalation**
    - Primary candidate: `INC-2026-0007` (24h timeout escalation to QA Manager)
    - Show: escalated incident in Manager Dashboard / Escalation Queue
    - Proves: long-running workflow, timeout escalation, continuity of state

5. **Manager oversight**
    - Show: Recent Decisions table with AI confidence, human override, response time
    - Proves: measurable governance and operational oversight

6. **Auditor export**
    - Show: History & Audit filters + CSV export click
    - Proves: inspection readiness and auditability

7. **Admin telemetry**
    - Show: telemetry summary + token totals + trace/failure counters
    - Proves: observability, prompt traceability, token governance

### Backup scenarios

1. Low-confidence recommendation banner (**promote to main cut** — covers 3-state confidence gate)
    - Candidate: `INC-2026-0008` (`LOW_CONFIDENCE`, confidence ~0.55, banner visible, mandatory comment field)
2. Conditional release with explicit disposition conditions
3. Rejection path with operator reason
4. Real-time unread routing in sidebar and bell
5. Template management for IT Admin

### Setup checks before recording

- Verify one incident has clear **Verified** and **Unresolved** evidence rows
- Prefer to validate this on the same happy-path incident before recording, otherwise swap to the best evidence-rich pending incident
- Verify one incident is in waiting/manual-review or `awaiting_agents` style state
- If no dedicated waiting-state incident exists in the seed, use `INC-2026-0010` as the safe-failure / withheld-output proof point
- Verify one incident is in `escalated` state
- `INC-2026-0007` should be the first escalation candidate to test
- Verify telemetry for chosen admin incident contains trace items and token counts
- Verify Recent Decisions table is populated
- Verify a follow-up transcript exists, or record that scenario separately as its own take

---

## Технічні вимоги

| Параметр | Значення |
| --- | --- |
| Тривалість | ≤ 5:10 хвилин (hard limit) |
| Мова | **English** |
| Субтитри | Обов'язкові (judges можуть дивитись без звуку) |
| Формат | MP4 |
| Якість відео | ≥ 1080p |
| Розмір файлу | ≤ 300 MB |

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

- Не записувати як один take. Краще 4-5 чистих сегментів і змонтувати їх в один безшовний flow
- Не витрачати час на live sign-in. Використати `e2e` auth mode і перемикати ролі між takes
- Основний happy path — один конкретний incident: **Granulator GR-204**
- Окремо підготувати incident у **waiting/manual-review** state для safe failure beat
- Якщо є prepared transcript, у happy path показати `Need More Info` loop як already recorded conversation, а не live typing
- Для manager beat краще мати дані з `Recent Decisions`, де видно `AI Confidence`, `Override`, `Response Time`
- Для admin beat цілитись у incident з telemetry summary, де є `Prompt Tokens`, `Completion Tokens`, `Total Tokens`
- Optional only: browser popup notification. Не робити його критичним для фінального cut
- Optional backup beats only if after dry-run ще є запас: `History & Audit` filters, `Quick Jump` palette, `Document Templates` page для IT Admin

---

## Сценарій відео (по секундах, узгоджений з новим темпом)

| Час | Що на екрані | Що говоримо |
| --- | --- | --- |
| **00:00–00:07** | Title slide: `Sentinel Intelligence` + subtitle `GMP Deviation & CAPA Operations Assistant` | "In GMP manufacturing, one deviation can trigger thirty to sixty minutes of manual investigation." |
| **00:07–00:15** | Hook slide: `45 min -> < 2 min` + `Governed AI assistance` | "Sentinel Intelligence brings that below two minutes — end to end — with AI, human approval, and traceability at every step." |
| **00:15–00:25** | Operations Dashboard with incident counts, analytics table, footer live status. | "This is the live operations dashboard, showing active incidents, status trends, and real-time system connectivity at a glance." |
| **00:25–00:35** | Open bell dropdown, show unread sidebar item, click incident. | "A new incident appears in the bell and unread queue, then opens directly into the decision workflow for the operator." |
| **00:35–00:55** | Incident detail summary + parameter excursion. Pause on equipment, batch, measured value, limits. | "Notice that the operator does not see raw telemetry alone. They get the equipment, the affected batch, the measured value, the validated range, the duration, and the severity in one view. That is the context needed for a regulated decision." |
| **00:55–01:15** | AI recommendation block. Pause on risk, confidence, classification, batch disposition. | "The recommendation is more than a summary. It includes risk, confidence, classification, and the proposed batch disposition, so the operator can see both what the system suggests and how certain it is about that suggestion." |
| **01:15–01:35** | Evidence section. Hold on verified and unresolved evidence rows. | "This is one of the most important screens. Verified citations are grounded in retrieved source material, while unresolved items stay visibly unresolved, so the user can distinguish evidence from assumptions before approving anything in a regulated workflow." |
| **01:35–01:50** | Batch Release Recommendation + conditions. | "Here the judge should notice that the system does not stop at diagnosis. It recommends the batch path and clearly states the conditions that must be met before release." |
| **01:50–02:05** | `After Approval` section with CAPA actions, work order draft, audit entry draft. | "This is not just analysis. The system prepares CAPA actions, a work order draft, and an audit entry draft before execution begins, so downstream work is already structured for review." |
| **02:05–02:20** | Need More Info transcript or available actions. | "If the operator needs more context, they can ask a follow-up question, and that conversation remains attached to the incident for traceability instead of disappearing outside the workflow." |
| **02:20–02:35** | Incident with `LOW_CONFIDENCE` banner (e.g. `INC-2026-0008`, confidence ~0.55). Show banner + mandatory comment field. | "When confidence falls below the threshold, the system shows a warning banner and requires the operator to leave a comment before deciding. The operator still decides — there is no automatic escalation. This is a governed co-pilot, not an override machine." |
| **02:35–02:50** | Pivot to `BLOCKED` state incident (`INC-2026-0010`, confidence 0.31, empty decision package). | "When the AI pipeline cannot produce a grounded result at all, the state is different: the recommendation is withheld entirely and the operator sees an empty form for manual entry. The incident is not lost — it stays in the workflow with a full audit trail. The system degrades gracefully instead of fabricating an answer." |
| **02:50–03:08** | QA Manager view: Manager Dashboard + Escalation Queue. | "If the incident is not handled in time, the workflow escalates to QA with the full context preserved. The important detail here is that the case is reassigned, not restarted, so review continues without losing history." |
| **03:08–03:25** | Recent Decisions table with AI confidence, override, response time. | "This manager view is where governance becomes measurable. Response time shows operational speed, AI confidence shows model certainty, and human override shows where people corrected or challenged the recommendation." |
| **03:25–03:40** | Auditor view: History & Audit filters + click `Export CSV`. | "For auditors, the incident log is filterable and exportable, so the current audit set can be downloaded in one click. That makes the workflow easy to review offline." |
| **03:40–03:55** | IT Admin view: Incident Telemetry summary with trace counters and token totals. | "Administrators can inspect trace counts, failures, rounds, duration, and token usage for each incident. This is the operational layer for troubleshooting prompts, agent runs, and cost-related governance." |
| **03:55–04:08** | Architecture slide reveal step 1: Track A + two-level orchestration. | "This is Track A: GitHub, Azure, and Azure AI Foundry. The architecture has two separate orchestration levels: Durable Functions handle the stateful workflow — incident creation, HITL pause, retry, and escalation. Azure AI Foundry handles AI reasoning — research, synthesis, and tool calls. Each level has a distinct responsibility." |
| **04:08–04:20** | Architecture slide reveal step 2 and 3: Service Bus, Cosmos DB, SignalR, MCP, security + CI/CD layer. | "AI Search grounds answers in validated documents. Service Bus absorbs alert bursts. Cosmos stores durable state. SignalR pushes real-time updates. MCP keeps integrations pluggable. Security runs on PIM just-in-time access, Conditional Access with MFA, and Defender for Cloud. The Foundry eval gate in CI/CD blocks any deployment where AI quality regresses." |
| **04:20–04:40** | KPI slide: before/after numbers. | "The result is a production-ready pattern for pharma operations: faster deviation handling, standardized decision support, and full traceability for regulated environments. In practice, it reduces investigation time while keeping approvals, escalation, and evidence review inside one governed flow." |
| **04:40–04:52** | Closing product screenshot or KPI slide. | "Instead of chasing documents and approvals manually, operators get a governed decision package in minutes, with evidence, actions, and next steps already structured." |
| **04:52–05:00** | Final branded closing frame. | "This is Sentinel Intelligence, built for governed pharma operations at scale." |

### Delivery notes

- Тримати паузу 1-2 секунди на `Verified` / `Unresolved` badges, щоб judges встигли це прочитати
- Не показувати live login, role switching або технічні transition steps. Ролі змінювати між takes і зводити в монтажі
- У segment `02:20–02:50` показати **два різних стани**: `LOW_CONFIDENCE` (оператор вирішує сам, з банером) і `BLOCKED` (пустий decision package, ручне заповнення). Це три-state confidence gate — ключовий RAI differentiator
- `operator_agrees_with_agent` прапор записується при Approve і Reject разом з причиною rejection, яка йде назад до SCADA/MES як feedback. Якщо є час у монтажі — показати rejection path як окремий beat
- Якщо показуємо `After Approval` section, не читати всі поля з draft objects. Достатньо коротко назвати: `CAPA actions`, `work order draft`, `audit entry draft`
- На architecture slide робити поетапне reveal у 3 кроки: `Track A + orchestration`, потім `AI Search / Service Bus / Cosmos / SignalR / MCP`, потім `Entra ID / RBAC / HITL`
- Якщо approval click ламає pacing, можна не тиснути кнопку у happy path, а тільки показати available actions і audit timeline окремим cut
- Якщо follow-up transcript не готовий, не робити live typing в основному cut. Краще показати prepared transcript або викинути цей beat на користь telemetry/export

---

## Optional popup beat

- Якщо стабільно працює під час запису: дати browser notification permission, переключити вікно і показати системний popup
- Якщо не стабільно: прибрати з фінального cut. In-app bell + unread highlight already sufficient

---

## Definition of Done

- [ ] Повний сценарій (script) написаний та схвалений командою
- [ ] [T-001](./T-001-architecture-presentation.md) architecture slides готові
- [ ] Покадровий таймінг dry-run перевірений: narration вкладається в 5:00 без поспіху
- [ ] Підготовлено мінімум 4 demo states: operator happy path, waiting/manual-review state, QA escalation state, auditor/admin traceability state
- [ ] Evidence verification state (**verified** vs **unresolved**) чітко видно у recorded demo
- [ ] Live demo записаний clean segments для монтажу
- [ ] Відео змонтовано в єдиний файл
- [ ] Субтитри додані та перевірені
- [ ] Тривалість ≤ 5:10
- [ ] Переглянуто командою та схвалено
- [ ] Завантажено на платформу хакатону до дедлайну

---

← [04 · План дій](../04-action-plan.md) · [T-001 Архітектура](./T-001-architecture-presentation.md)
