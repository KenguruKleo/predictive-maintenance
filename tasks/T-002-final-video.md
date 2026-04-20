# T-002 · Фінальне відео (5 хвилин)

← [04 · План дій](../04-action-plan.md) · [01 · Вимоги §9](../01-requirements.md#9-deliverables-по-фазах)

| Поле | Значення |
|---|---|
| **ID** | T-002 |
| **Пріоритет** | 🔴 CRITICAL |
| **Статус** | 🔜 TODO |
| **Залежності** | [T-001](./T-001-architecture-presentation.md) (architecture slide), [T-010](./T-010-cartoon-animation.md) (cartoon анімація), live demo (робочий додаток) |
| **Дедлайн** | 1-й тиждень травня 2026 |

---

## Чому це критично

> ⚡ **5 хвилин = рішення про переможця.**  
> Це єдиний touchpoint для Capgemini executives + Microsoft judges на Finals. Структура, якість і story цього відео — те що залишиться в пам'яті після перегляду.

---

## Структура відео (5 хв = 300 сек)

```
[00:00–00:30]  HOOK — Проблема одним реченням + драматична цифра
               "In GMP manufacturing, one deviation event = 30–60 minutes
               of manual work, audit risk, and potential line shutdown"

[00:30–01:30]  CARTOON AS-IS — процес без додатку (← T-010)
               Cartoon-style: оператор вручну шукає SOP, телефонує QA,
               заповнює форми — повільно, помилково, стресово

[01:30–02:30]  CARTOON TO-BE — процес з додатком (← T-010)
               Той самий сценарій: granulator дає відхилення →
               за < 5 хв оператор бачить decision package → approves →
               work order створено автоматично

[02:30–04:00]  LIVE DEMO — робочий додаток (← working implementation)
               Реальний flow: SCADA signal → agents → decision package
               → notification bell/unread highlight → human approval → audit trail
               Один конкретний сценарій: Granulator GR-204, vibration spike

[04:00–04:30]  ARCHITECTURE SLIDE — один слайд (← T-001)
               Оновлена архітектурна діаграма
               Track A: GitHub + Azure + Foundry

[04:30–05:00]  IMPACT + CLOSE
               KPI: 30–60 хв → < 5 хв · Standardized · GMP compliant
               "Production-ready solution for pharma"
```

---

## Технічні вимоги

| Параметр | Значення |
|---|---|
| Тривалість | ≤ 5:10 хвилин (hard limit) |
| Мова | **English** |
| Субтитри | Обов'язкові (judges можуть дивитись без звуку) |
| Формат | MP4 |
| Якість відео | ≥ 1080p |
| Розмір файлу | ≤ 300 MB |

---

## Інструменти для запису

| Роль | Інструмент | Нотатки |
|---|---|---|
| Screen record + narration | OBS / Loom / QuickTime | Для live demo секції |
| Монтаж | DaVinci Resolve (безкоштовно) / Camtasia | |
| Субтитри | Auto-captions у DaVinci / Whisper | |
| Cartoon вставки | → [T-010](./T-010-cartoon-animation.md) | Окрема задача |
| Architecture slide | → [T-001](./T-001-architecture-presentation.md) | Окрема задача |

---

## Сценарій відео (script — заповнюємо)

> Тут пишемо повний narration script перед записом

```
[00:00–00:30] HOOK
Narrator: "In GMP pharmaceutical manufacturing, when equipment deviates from
validated limits, operators face a 30-to-60-minute manual process:
searching SOPs, contacting QA, filling CAPA forms by hand.
Every minute counts. Every error risks a batch rejection or audit finding.
We built Sentinel Intelligence to change that."

[00:30–01:30] CARTOON AS-IS
[no narration needed — animation tells the story]

[01:30–02:30] CARTOON TO-BE
[no narration needed — animation tells the story]

[02:30–04:00] LIVE DEMO
Narrator: "Let me show you how it works.
A vibration spike on Granulator GR-204 triggers our system...
[demo narration — TBD after implementation]
Notice the notification bell in the header: the operator gets a real-time alert,
the unread counter increments, and the new incident is highlighted in the left rail.
Opening the incident takes the operator directly into the approval package and
clears the unread marker once the package is viewed.
If we want one extra visual proof point during recording, we can briefly switch the browser tab or window and show the optional browser popup notification after permission has been granted."

## Manual popup demo note

- Optional demo beat: after granting browser notification permission from the bell dropdown, move focus away from the app (switch tab/window) and trigger a fresh incident so the system popup becomes visible on screen.
- This popup check is manual only; no Playwright / automated E2E coverage is planned before demo.

[04:00–04:30] ARCHITECTURE
Narrator: "Built on Track A — GitHub, Azure, and Azure AI Foundry.
Multi-agent orchestration, RAG over validated SOPs,
mandatory human approval for GxP compliance,
full audit trail automatically generated."

[04:30–05:00] IMPACT
Narrator: "Result: deviation handling reduced from 45 minutes to under 5.
Standardized, GMP-compliant, traceable.
This is Sentinel Intelligence."
```

---

## Definition of Done

- [ ] Повний сценарій (script) написаний та схвалений командою
- [ ] [T-010](./T-010-cartoon-animation.md) cartoon готовий і переданий
- [ ] [T-001](./T-001-architecture-presentation.md) architecture slide готовий
- [ ] Live demo записаний без помилок (один чистий take)
- [ ] Відео змонтовано в єдиний файл
- [ ] Субтитри додані та перевірені
- [ ] Тривалість ≤ 5:10
- [ ] Переглянуто командою та схвалено
- [ ] Завантажено на платформу хакатону до дедлайну

---

← [04 · План дій](../04-action-plan.md) · [T-001 Архітектура](./T-001-architecture-presentation.md) · [T-010 Анімація](./T-010-cartoon-animation.md)
