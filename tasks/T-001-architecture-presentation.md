# T-001 · Оновити архітектурну презентацію

← [04 · План дій](../04-action-plan.md) · [02 · Архітектура](../02-architecture.md) · [03 · Аналіз](../03-analysis.md)

| Поле | Значення |
|---|---|
| **ID** | T-001 |
| **Пріоритет** | 🔴 CRITICAL |
| **Статус** | 🔜 TODO |
| **Залежності** | Немає (перша задача) |
| **Блокує** | T-002 (відео потребує оновленого architecture slide) |

---

## Мета

Оновити архітектурну презентацію (PowerPoint/slides) так, щоб:
1. Закрити всі 6 gaps з тріаж-звіту
2. Відображати **реальну збудовану архітектуру** (не тільки концепт)
3. Явно задекларувати **Track A**
4. Бути готовою як слайд для фінального відео [T-002](./T-002-final-video.md)

---

## Gaps, які закриваємо

| Gap | Деталі | Що додаємо до презентації |
|---|---|---|
| **#1 Track** | Track A не задекларований | Явний label "Track A: GitHub + Azure + Azure AI Foundry" на титульній сторінці та архітектурній діаграмі |
| **#2 Security** | Identity, RBAC, Key Vault, network — відсутні | Окремий Security шар на діаграмі: Entra ID, Key Vault, Private Endpoints, RBAC roles |
| **#3 Reliability** | Queuing, retry, DLQ, fallback — відсутні | Service Bus між SCADA→Functions, retry/DLQ позначки, Fallback mode |
| **#4 RAI** | Confidence thresholds, content safety, observability | RAI layer: Content Safety, Confidence Gate, Observability (Azure Monitor) |
| **#5 UX** | Operator UI не визначений | Додати конкретний operator UI (Teams Adaptive Card або Power Apps) |
| **#6 IaC** | Немає deployment layer | GitHub Actions CI/CD + IaC (Bicep) у діаграмі |

> Деталі кожного gap → [03 · Аналіз](../03-analysis.md#5-топ-6-gaps-для-виправлення)

---

## Структура оновленої презентації

### Слайд 1: Title
```
Deviation Management & CAPA in GMP Manufacturing
Operations Assistant — Sentinel Intelligence
Track A: GitHub + Azure + Azure AI Foundry
```

### Слайд 2: Problem Statement
- AS-IS процес (30–60 хв, manual, ризики)
- KPI targets (< 5 хв, auto-drafted, GMP compliant)

### Слайд 3: Solution Overview
- High-level flow: Detect → Context → Agents → Approve → Execute
- Stakeholders

### Слайд 4: Architecture Diagram (головний)
Оновлена діаграма з усіма шарами:
```
┌─────────────────────────────────┐
│  GITHUB + CI/CD (Track A)       │  ← новий
│  GitHub Actions | IaC (Bicep)   │
└─────────────────────────────────┘
┌─────────────────────────────────┐
│  SECURITY LAYER                 │  ← новий
│  Entra ID | Key Vault | VNet    │
└─────────────────────────────────┘
┌─────────────────────────────────┐
│  RELIABILITY LAYER              │  ← новий
│  Service Bus | Retry | DLQ      │
└─────────────────────────────────┘
[існуюча діаграма компонентів]
┌─────────────────────────────────┐
│  RAI + OBSERVABILITY LAYER      │  ← новий
│  Content Safety | Confidence    │
│  Gate | Azure Monitor           │
└─────────────────────────────────┘
┌─────────────────────────────────┐
│  OPERATOR UX                    │  ← новий
│  Teams Adaptive Card / Portal   │
└─────────────────────────────────┘
```

### Слайд 5: Data Sources & Integrations
- SCADA, MES, BPR, SOP, CMMS, QMS

### Слайд 6: KPI Impact
- Before/After table

---

---

## 📋 Нотатки: Структурована презентація по шарах

Ідея — показати додаток не тільки як "ось схема", а провести аудиторію через **6 шарів**, кожен з яких відповідає на своє питання.

---

### Шар 0: Infrastructure / Deployment Topology
*«Що і де крутиться?»*

- Показати що в Azure, що можна тримати локально (наприклад MCP сервери як sidecar або локальний Docker)
- Назвати це **Deployment Topology** або **Infrastructure Overview**
- Ключові компоненти: Azure Functions, Cosmos DB, AI Search, Service Bus, Azure AI Foundry, Static Web App, SignalR
- Позначити межу cloud/on-premise якщо є (SCADA, MES зазвичай локально, агенти — cloud)

---

### Шар 1: Functional Layer
*«Як це працює і навіщо?»*

- Провести через end-to-end flow: Сенсор → Alert → Оркестратор → Агенти → Approval → Execution
- Пояснити **чому** Durable Orchestrator (stateful, retry, long-running), **чому** окремі агенти (Research / Document / Execution), чому Human-in-the-loop
- Показати що система ВИРІШУЄ: час реакції з 30–60 хв → < 5 хв, GMP-compliant документи, аудит кожного кроку
- Показати "провали" без системи (ручна координація, помилки в документах, пропущені SLA)

---

### Шар 2: Security Layer
*«Як ми захищаємо дані і доступи?»*

- **Entra ID** — аутентифікація і авторизація скрізь: frontend, API, агенти, MCP сервери
- **RBAC** — оператор бачить тільки свої incidents, менеджер — зведення, аудитор — логи. Жодних зайвих даних
- **Нема прямого доступу до БД і документів** — тільки через API/MCP шар. Це ключовий design decision:
  - Агент не може "зробити SQL injection" або "злити весь Cosmos"
  - Ми контролюємо кожен запит: що запитує, скільки, в яких межах
  - Можна обмежити, логувати, блокувати підозрілу активність навіть від AI
- **Key Vault** — всі ключі, connection strings, secrets на сервері. Людина не має до них доступу, frontend взагалі нічого не знає про backend credentials
- **Managed Identity** — сервіси Azure спілкуються між собою без паролів у коді
- **Private Endpoints / VNet** — Cosmos DB, Service Bus, AI Search не виставлені в публічний internet; трафік йде по внутрішній мережі Azure
- **Encryption** — дані зашифровані at rest (Cosmos DB, Blob) та in transit (TLS 1.2+); ключі в Key Vault
- **Data classification & retention** — SOP/BPR документи мають окремий клас доступу; audit logs — immutable retention policy для відповідності 21 CFR Part 11

> 📌 Slide pitch: *"Security isn't an afterthought — it's structural. Every layer enforces it."*

---

### Шар 3: Integration Layer
*«Як ми підключаємось до зовнішніх систем?»*

- **MCP сервери** — кожна інтеграція (CMMS, QMS, Sentinel DB, AI Search) це окремий маленький сервер
  - Аргумент: організація може замінити СВІЙ CMMS не чіпаючи логіку агентів
  - Аргумент: новий data source = новий MCP сервер, решта не змінюється
  - Назвати це **"pluggable integration layer"**
- **Azure AI Foundry** — дозволяє перенастроїти агента під конкретну організацію через system prompt або tool configuration, без зміни коду
- Реюзабільність: той самий orchestrator + agents framework може бути задеплоєний для іншої галузі (інші MCP сервери, інші prompts — той самий pipeline)

> 📌 Slide pitch: *"The process is universal. The integrations are configurable."*

---

### Шар 4: Reliability Layer
*«Що станеться якщо щось піде не так?»*

- **Service Bus черги** — SCADA і зовнішні системи скидають алерти в чергу і звільняються. Ніхто не чекає і не блокується. Ми обробляємо інциденти у своєму темпі, навіть якщо прийшла хвиля алертів одночасно
- **Durable Functions** — оркестрація stateful за дизайном. Human-in-the-loop approval може чекати годинами або навіть кілька діб — функція «спить» і прокидається коли людина відповіла. Немає жодних таймаутів HTTP-запиту або ліміту чату
- **Ескалація** — якщо оператор не підтвердив у відведений час, система автоматично ескалює до наступного рівня (менеджер, і далі). Дедлайн не буде мовчки пропущений
- **Push-нотифікації** — SignalR доставляє оновлення статусу у реальному часі. Відповідні люди бачать нову задачу одразу, без polling і без «а я не помітив email»
- **Dead Letter Queue** — якщо обробка провалилась після всіх retry, повідомлення не губиться, а потрапляє в DLQ з повним контекстом для діагностики та ручного перезапуску
- **Retry policy** — кожен крок має явну retry-логіку з backoff; транзієнтні збої (мережа, throttling) обробляються автоматично

> 📌 Slide pitch: *"The system doesn't fail silently. It queues, retries, escalates — and always tells someone."*

---

### Шар 5: Audit & Compliance Layer
*«Хто що робив і коли?»*

- Кожна дія агента, кожен approval, кожна зміна статусу — логується в Cosmos DB з timestamp і user identity
- **Audit pages** — окремі views:
  - **Internal IT / Admin** — налаштування системи, перегляд конфігів, управління ролями
  - **Internal Audit** — повний trail по інциденту: від alert до виконаної CAPA, хто підтвердив, які документи
  - **External Audit / Regulatory** — read-only view для GMP інспекторів: immutable logs, signed approvals
- Зовнішній аудитор не має доступу до операційних даних — тільки до audit trail
- Це дозволяє **пройти 21 CFR Part 11 / GMP інспекцію** без "а покажіть нам базу даних"

---

### Шар 6: Observability & Ops Layer
*«Як ми знаємо що система здорова?»*

- **Azure Monitor + Application Insights** — latency, error rates, agent execution times, кількість ескалацій
- **Health dashboards** для внутрішньої IT команди — видно де черга росте, де агент повільний
- **Alerting** — якщо агент не відповів за N секунд → автоматичний fallback до мануального процесу
- **Distributed tracing** — кожен інцидент має correlation ID, можна відстежити весь шлях від alert до закриття
- **Agent telemetry by incident (Admin view)** — окрема сторінка для IT Admin/QA: хронологія викликів agent -> sub-agent -> tools по конкретному incident (run IDs, duration, retries, помилки, токени, estimated cost). Це критично для tuning prompt/tool конфігурації та пост-мортем аналізу

---

### Шар 7: Responsible AI Layer
*«Як ми контролюємо поведінку AI і не даємо йому вигадувати?»*

> Це окремий scoring dimension в оцінці — **AI Fit (10 балів)**. Повинен бути явний, не закопаний в інші шари.

- **Confidence gate** — агент повертає не просто відповідь, а разом з confidence score. Якщо score нижче порогу → ескалація до людини, а не вгадування. AI не може "видати" рекомендацію без достатньо доказів
- **Evidence gating** — кожна рекомендація в decision package має посилання на конкретний SOP/BPR документ та конкретний параметр. Якщо джерела нема — рекомендація блокується
- **Hallucination controls** — RAG over validated documents (AI Search); агент відповідає тільки на основі верифікованих SOP/CAPA, не "з голови"
- **Prompt injection defense** — вхідний текст від SCADA/MES проходить валідацію та санітизацію; Content Safety API фільтрує шкідливий або маніпулятивний контент
- **Content Safety** — Azure AI Content Safety перевіряє вхід і вихід агентів; блокує аномальні запити
- **Human-in-the-loop як RAI механізм** — не просто зручність, а вимога для GxP: AI пропонує, людина вирішує і бере відповідальність. Кожне рішення підписане конкретною людиною
- **Agent observability** — всі виклики агентів трасуються в App Insights: який prompt, яка модель, яка відповідь, скільки токенів. Пост-фактум аналіз можливий

> 📌 Slide pitch: *"The AI suggests. The human decides. The system proves it."*

---

### Шар 8: UX / Operator Experience
*«Як виглядає це для людини?»*

> **UX Simplicity (10 балів)** — окремий scoring dimension. Потрібно показати конкретний UI, не wireframe.

- **Operator dashboard** — список активних incidents з пріоритетами, статусами, таймерами ескалації. Один клік → деталі
- **Decision package** — на екрані approval оператор бачить: що сталося, які дані з SCADA, яке обладнання, що рекомендує AI і З ЯКИХ документів (з посиланнями), confidence score, попередня CAPA по схожих кейсах
- **Approval ergonomics** — approve/reject/escalate одним кліком; поле для коментаря; підпис фіксується автоматично через Entra ID (хто + коли)
- **Explainability** — оператор може розгорнути "чому AI так вирішив" і побачити конкретний параметр з SOP та відхилення від golden batch
- **Real-time updates** — статус змінюється на екрані без перезавантаження (SignalR push); видно де зараз знаходиться кожен incident у pipeline
- **Role-based views** — оператор, менеджер, QA, аудитор — кожен бачить свій контекст, без зайвого шуму
- **Command Palette (⌘K)** — швидка навігація між розділами без миші, як у VS Code або Linear. Це деталь, яка сигналізує: додаток зроблений для людей, що постійно ним користуються, а не для разового demo. Keyboard-first UX — ознака enterprise-grade продукту
- **Infinite scroll / one-screen UX** — всі таблиці (інциденти, історія, шаблони) без класичної пагінації: оператор бачить повний список і може швидко знайти потрібне без зайвих кліків. Це не "адмінка для галочки", а робочий інструмент — все, що потрібно, доступно на одному екрані, без зайвих переходів і маніпуляцій. Якщо скролінг потрібен — він природний, а не "по 10 рядків". Це стандарт для сучасних бізнес-додатків, де швидкість і зручність важливіші за "красиву сторінку"

> 📌 Slide pitch: *"Every screen answers one question: what do I need to do right now, and why?"*

---

### Шар 9: Business Value & KPI
*«Навіщо це взагалі?»*

> **Value & KPI Impact (10 балів)** — перший Use Case dimension. Краще починати або закінчувати презентацію з цього. Потрібні конкретні цифри, не просто "faster and better".

- **AS-IS pain points:**
  - Deviation виявлення: вручну під час обходу або після зміни — 30–60 хв затримка
  - CAPA документ: 2–4 год зборки з кількох систем (SCADA prints, SOP PDF, Excel CAPA log)
  - GMP audit prep: 2–3 дні підготовки на один інспекційний запит
  - Людський фактор: пропущені ескалації, неправильна версія SOP, непідписаний approval

- **TO-BE KPI targets:**
  - Detection → Decision package ready: **< 5 хв** (зараз 30–60 хв)
  - Manual CAPA drafting: **eliminiated** (AI генерує чернетку, людина затверджує)
  - Audit prep: **real-time** (audit trail завжди ready, один клік)
  - Missed escalations: **0** (автоматична ескалація + push notifications)

- **Regulated context** — це не просто ефективність. В GMP кожна затримка з CAPA = ризик регуляторного порушення, batch rejection, або recall. Система не тільки швидша — вона документально відповідна за замовчуванням

> 📌 Slide pitch: *"From 60 minutes of manual guesswork to 5 minutes of evidence-based decision — with full GMP traceability built in."*

---

### Що ще варто додати в такому ключі

| Потенційний шар | Pitch | Scoring dimension |
|---|---|---|
| **Cost & Token Efficiency** | Pay-per-execution: немає алертів — нема витрат; token budgets обмежують вартість одного інциденту; caching для повторних SOP запитів | Reliability / Performance / Cost (10) |
| **Platform Fit / Track A** | Показати явно: GitHub repo + Actions CI/CD + Bicep IaC + AI Foundry. Вся інфра відтворювана за < 30 хв. Zero manual deployments | Platform Fit (10) |
| **MVP Scope / Build–Scale–Reuse** | Ми взяли один актив (GR-204 granulator), один клас відхилення (vibration deviation), одну лінію (Plant-01 Line-2). Це навмисне звуження MVP. Production scale = розширення MCP серверів, не реархітектура | Build–Scale–Reuse (10) |
| **Innovation Differentiator** | Не chatbot, не anomaly detector. Multi-agent regulated workflow з MCP як pluggable compliance layer — нового класу рішення | Innovation (10) |

---

> 💡 **Загальний pitch для всієї презентації:**
> *"Ми не просто автоматизували процес — ми збудували систему, яка безпечна за дизайном, надійна за замовчуванням, інтегрується без lock-in, аудитується на кожному кроці і масштабується без змін в архітектурі."*

---

## Definition of Done

- [ ] Track A явно вказаний у презентації
- [ ] Архітектурна діаграма оновлена з усіма 6 gap-виправленнями
- [ ] Security шар присутній (Entra ID, Key Vault, VNet, RBAC)
- [ ] Reliability шар присутній (Service Bus, retry, DLQ)
- [ ] RAI шар присутній (Content Safety, Confidence Gate, Monitor)
- [ ] Operator UX показаний (конкретний channel)
- [ ] GitHub + CI/CD присутні
- [ ] Презентація схвалена командою
- [ ] Architecture slide готовий для монтажу у [T-002](./T-002-final-video.md)
- [ ] [02 · Архітектура](../02-architecture.md) оновлено відповідно (Changelog §9)
- [ ] [03 · Аналіз](../03-analysis.md#9-прогрес-виправлення-gaps) — всі gaps відмічені як закриті
- [ ] [01 · Вимоги чеклист](../01-requirements.md#10-чеклист-відповідності-живий) оновлено

---

← [04 · План дій](../04-action-plan.md)
