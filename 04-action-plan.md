# 04 · План дій

← [README](./README.md) · [01 Вимоги](./01-requirements.md) · [02 Архітектура](./02-architecture.md) · [03 Аналіз](./03-analysis.md)

> **Призначення:** Живий backlog задач implementation фази. Оновлюємо в міру роботи. Кожна задача прив'язана до конкретного gap або вимоги.

---

## Зміст
1. [Поточний фокус](#1-поточний-фокус)
2. [Backlog задач](#2-backlog-задач)
3. [Sprint / Iteration план](#3-sprint--iteration-план)
4. [Definition of Done](#4-definition-of-done)
5. [Блокери та ризики](#5-блокери-та-ризики)

---

## 1. Поточний фокус

> **Квітень 2026 — Implementation Phase**  
> Дедлайн фінального submission: 1-й тиждень травня 2026

**Зараз в роботі:** _не розпочато_

**Наступний крок:** _визначити з командою_

---

## 2. Backlog задач

> Задачі будуть додаватись тут. Кожна задача містить пріоритет, gap-посилання та definition of done.  
> **Порядок у списку ≠ порядок виконання.** Пріоритет і послідовність — у [§3 Sprint план](#3-sprint--iteration-план).

### Критичні (Must-have для finals)

| ID | Задача | Gap / Вимога | Пріоритет | Статус |
|---|---|---|---|---|
| T-001 | **[Оновити архітектурну презентацію](./tasks/T-001-architecture-presentation.md)** — закрити всі gaps, показати реальну збудовану архітектуру (Track A, Security, Reliability, RAI, UX, IaC) | [Gap #1–6](./03-analysis.md#5-топ-6-gaps-для-виправлення) | 🔴 CRITICAL | 🔜 TODO |
| T-002 | **[5-хвилинне фінальне відео](./tasks/T-002-final-video.md)** — повна demo презентація додатка; структура, script, DoD | [Вимоги §9](./01-requirements.md#9-deliverables-по-фазах) | 🔴 CRITICAL | 🔜 TODO |
| T-003 | _TBD — implementation tasks_ | | | |

### Важливі (Should-have)

| ID | Задача | Gap / Вимога | Пріоритет | Статус |
|---|---|---|---|---|
| T-010 | **[Cartoon / анімація «До і Після»](./tasks/T-010-cartoon-animation.md)** — process walkthrough AS-IS vs TO-BE; блокує T-002 | [Вимоги §9](./01-requirements.md#9-deliverables-по-фазах) | 🟠 HIGH | 🔜 TODO |
| T-011 | _TBD_ | | | |

### Nice-to-have

| ID | Задача | Gap / Вимога | Пріоритет | Статус |
|---|---|---|---|---|
| T-020 | _TBD_ | | | |

---

## 3. Sprint / Iteration план

> Заповнюємо після визначення backlog.

### Week 1 (квітень)
_TBD_

### Week 2 (квітень)
_TBD_

### Week 3 (квітень)
_TBD_

### Week 4 (квітень) — Finalization
_TBD_

---

## 4. Definition of Done

Задача вважається завершеною якщо:

**Для архітектурних змін:**
- [ ] Зміна відображена в [02 · Архітектура](./02-architecture.md)
- [ ] Відповідний gap відмічений як "виправлений" в [03 · Аналіз](./03-analysis.md#9-прогрес-виправлення-gaps)
- [ ] Відповідний пункт відмічений у [01 · Вимоги чеклист](./01-requirements.md#10-чеклист-відповідності-живий)
- [ ] Changelog оновлений в [02 · Архітектура §9](./02-architecture.md#9-changelog-архітектури)

**Для коду:**
- [ ] Code у GitHub repo
- [ ] CI pipeline проходить
- [ ] Deployed до dev environment
- [ ] Базовий smoke test проходить

**Для demo scenario:**
- [ ] Один кінцевий сценарій з реальними mock даними
- [ ] Decision package показує recommendation + evidence + SOP reference
- [ ] Human approval flow демонструється
- [ ] Audit trail генерується

---

## 5. Блокери та ризики

| Блокер/Ризик | Опис | Mitigation |
|---|---|---|
| _TBD_ | | |

---

## 6. Задачі — деталі

Кожна задача розписана в окремому файлі в папці [`tasks/`](./tasks/README.md):

| ID | Файл | Примітка |
|---|---|---|
| T-001 | [tasks/T-001-architecture-presentation.md](./tasks/T-001-architecture-presentation.md) | Закрити всі 6 gaps в презентації; architecture slide потрібен для T-002 |
| T-002 | [tasks/T-002-final-video.md](./tasks/T-002-final-video.md) | ⚡ Це вирішить чи переможемо. Детальна структура відео, script, DoD |
| T-010 | [tasks/T-010-cartoon-animation.md](./tasks/T-010-cartoon-animation.md) | Cartoon AS-IS vs TO-BE; блокує T-002 |

---

### Корисні посилання для планування:
- Gaps, які потрібно закрити → [03 · Аналіз](./03-analysis.md#5-топ-6-gaps-для-виправлення)
- Вимоги, що не виконані → [01 · Вимоги чеклист](./01-requirements.md#10-чеклист-відповідності-живий)
- Архітектурні зміни in-progress → [02 · Архітектура §8](./02-architecture.md#8-поточна-версія-in-progress)

---

← [03 Аналіз](./03-analysis.md) · [README →](./README.md)
