# T-055 · AI Pipeline Status Contract Hardening (post-hackathon)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

> **Пріоритет:** 🟡 MEDIUM — важливо для коректного live UX, але не блокує demo завдяки тимчасовому frontend workaround  
> **Походження:** Demo debugging, 23 квітня 2026  
> **Статус:** 🔜 TODO

---

## Контекст

Під час demo-debugging виявлено розсинхрон між backend статусами інциденту, SignalR подіями та frontend AI Pipeline widget.

**Що є зараз:**
- `http_ingest_alert.py` створює incident зі статусом `open` і шле тільки SignalR подію `incident_created`;
- Durable orchestrator стартує `run_foundry_agents`, але не переводить incident у `ingested` або `analyzing`;
- після завершення Foundry run backend одразу ставить `pending_approval` або `escalated`;
- frontend widget на Operations Dashboard рахує лише `ingested`, `analyzing`, `awaiting_agents`.

Наслідок: під час **першого реального AI run** агент працює, але AI Pipeline widget може залишатися порожнім. Для hackathon demo це тимчасово обійдено фронтенд-мапінгом `open -> first pipeline bucket`, але правильний fix має бути на backend/status-contract рівні.

---

## Мета

Зробити backend єдиним джерелом правди для AI pipeline станів і live-оновлень, щоб frontend показував реальний lifecycle інциденту без workaround-ів.

Цільовий статусний контракт:

1. `open` — incident щойно створений, ще не взятий Durable/Service Bus у роботу;
2. `ingested` — Service Bus message прийнято, Durable instance стартував;
3. `analyzing` — `run_foundry_agents` реально виконується;
4. `awaiting_agents` — оператор запросив `more_info`, incident поставлено в чергу на повторний AI run;
5. `pending_approval` / `escalated` — AI завершив підготовку decision package;
6. `in_progress` / `completed` / `rejected` — execution / terminal flow.

---

## Що змінити

### 1. Нормалізувати статуси в backend

#### `backend/triggers/service_bus_trigger.py`

- Після успішного `start_new(...)` оновлювати incident `status = "ingested"`;
- записувати `workflow_state.current_step = "ingested"` або аналогічний ранній крок;
- додати timestamp оновлення;
- відправляти SignalR подію `incident_status_changed` з `new_status: "ingested"`.

#### `backend/orchestrators/incident_orchestrator.py`

- Перед `run_foundry_agents` викликати activity/helper, що ставить `status = "analyzing"`;
- при кожному повторному `more_info` run знову переходити в `analyzing` перед стартом activity;
- не залишати incident в `open`, якщо Durable вже реально обробляє payload.

#### `backend/triggers/http_decision.py`

- `more_info` має переводити incident в `awaiting_agents` як явний pre-run стан;
- після старту rerun orchestrator/activity incident має переходити з `awaiting_agents` у `analyzing`.

### 2. Реально надсилати live події, які вже очікує frontend

#### `backend/shared/signalr_client.py`

Додати маленькі helper-и для status/event пушів, щоб не дублювати payload-формат по всьому коду:

```python
notify_incident_status_changed(
    incident_id="INC-2026-0049",
    new_status="analyzing",
    previous_status="ingested",
)
```

#### Використання helper-а

- `service_bus_trigger.py` → `incident_status_changed(ingested)`
- status transition helper/activity перед AI run → `incident_status_changed(analyzing)`
- `http_decision.py` on `more_info` → `incident_status_changed(awaiting_agents)`
- `notify_operator.py` → або `incident_status_changed(pending_approval|escalated)`, або залишити існуючу domain-specific подію + додати загальну status event теж

### 3. Вирівняти фронтенд і бекенд контракт

#### `frontend/src/pages/OperationsDashboard.tsx`

- Після backend fix прибрати demo workaround `open -> first pipeline bucket`;
- AI Pipeline widget знову має рахувати лише реальні pipeline statuses із backend;
- за бажанням перейменувати перший bucket назад з `Received` на `Ingested`, якщо контракт стабільний.

#### `frontend/src/hooks/useSignalR.ts`

- Перевірити, що `incident_status_changed` і `agent_step_completed` або реально використовуються, або видалити зайві listener-и;
- якщо `agent_step_completed` лишається, backend має справді надсилати його хоча б після завершення major steps (наприклад, `run_foundry_agents`, `run_execution_agent`).

### 4. Прибрати legacy drift

#### `backend/triggers/timer_watchdog.py`

- Переглянути legacy-статуси `queued` і `analyzing_agents`;
- звести watchdog до актуального набору статусів;
- переконатися, що recovery логіка не залежить від старих назв.

---

## Definition of Done

- [ ] Перший AI run більше не залишається в `open` після старту Durable orchestrator
- [ ] `service_bus_trigger.py` ставить `ingested` і шле `incident_status_changed`
- [ ] Перед кожним `run_foundry_agents` incident переходить у `analyzing`
- [ ] `more_info` flow використовує `awaiting_agents -> analyzing -> pending_approval`
- [ ] Frontend AI Pipeline widget більше не потребує `open` workaround
- [ ] `incident_status_changed` реально приходить у frontend під час pipeline transitions
- [ ] Watchdog більше не покладається на застарілі `queued` / `analyzing_agents`
- [ ] Smoke test: під час активного Foundry run AI Pipeline widget показує хоча б 1 incident in-flight

---

## Smoke сценарій після реалізації

1. Надіслати новий alert через `POST /api/alerts`.
2. Переконатися, що incident переходить `open -> ingested -> analyzing`.
3. Під час роботи Foundry widget на Operations Dashboard показує інцидент в pipeline.
4. Після завершення AI run incident переходить у `pending_approval` і зникає з AI in-flight bucket.
5. Натиснути `More info` і перевірити `awaiting_agents -> analyzing -> pending_approval`.