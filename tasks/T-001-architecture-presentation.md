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
