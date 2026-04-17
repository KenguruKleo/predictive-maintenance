# Sentinel Intelligence — GMP CAPA Operations Assistant
### Microsoft Agentic Industry Hackathon 2026 · Capgemini + Microsoft · Track A

> **Use Case:** LS / Supply Chain — Deviation Management & CAPA in GMP Manufacturing  
> **Stack:** GitHub + Azure + Azure AI Foundry  
> **Фаза:** 🔄 Implementation (Квітень 2026) · Фінал: 2-й тиждень травня

---

## Документи проєкту

### Знання та вимоги
| | Файл | Що там |
|---|---|---|
| 📋 | [01-requirements.md](./01-requirements.md) | Вимоги хакатону, критерії оцінки, живий чеклист ✅/❌ |
| 🏗 | [02-architecture.md](./02-architecture.md) | Архітектура: AS-SUBMITTED → IN-PROGRESS, changelog |
| 🔍 | [03-analysis.md](./03-analysis.md) | Тріаж 71/100, 6 gaps, що виправляємо |

### Планування та задачі
| | Файл | Що там |
|---|---|---|
| 📌 | [04-action-plan.md](./04-action-plan.md) | Backlog, пріоритети, sprint план |
| 📁 | [tasks/README.md](./tasks/README.md) | Індекс всіх задач |

### Вихідні документи хакатону
| | Файл | Що там |
|---|---|---|
| 📄 | [docs/](./docs/) | Оригінальні файли: презентація хакатону, транскрипт мітингу, наше подання, тріаж-звіт |

---

## Швидка навігація

| Питання | Де шукати |
|---|---|
| Які вимоги і що ще не виконано? | [01 · чеклист](./01-requirements.md#10-чеклист-відповідності-живий) |
| Яка наша архітектура зараз? | [02 · компонентна схема](./02-architecture.md#2-компонентна-схема) |
| Що потрібно виправити в архітектурі? | [03 · топ-6 gaps](./03-analysis.md#5-топ-6-gaps-для-виправлення) |
| Які задачі в роботі? | [04 · backlog](./04-action-plan.md#2-backlog-задач) |
| Деталі конкретної задачі? | [tasks/](./tasks/README.md) |
| Оригінальна оцінка (71/100)? | [03 · тріаж-звіт](./03-analysis.md#1-тріаж-звіт-30-березня-2026) |

---

## 🧪 Testing & Development

### Prerequisites

```bash
pip install azure-cosmos requests python-dotenv
```

Credentials are loaded from `backend/local.settings.json` automatically when running scripts locally.

---

### Симуляція алертів (`simulate_alerts.py`)

The script sends test payloads to the ingestion API and prints pass/fail for each scenario.

```bash
# Single scenario with fresh IDs (no idempotency collision)
FUNCTION_URL="https://func-sentinel-intel-dev-erzrpo.azurewebsites.net/api/alerts" \
FUNCTION_KEY="<your-function-key>" \
python scripts/simulate_alerts.py --fresh --scenario 1

# Run all 6 scenarios
FUNCTION_URL="..." FUNCTION_KEY="..." python scripts/simulate_alerts.py --fresh --all

# Target local Azure Functions host
python scripts/simulate_alerts.py --local --fresh --all
```

**Scenarios:**
| # | Description | Expected |
|---|---|---|
| 1 | GR-204 major deviation | 202 + INC-2026-NNNN |
| 2 | GR-204 critical deviation | 202 |
| 3 | MIX-102 minor deviation | 202 |
| 4 | DRY-303 critical deviation | 202 |
| 5 | Duplicate alert (idempotency) | 200 already_exists |
| 6 | Invalid payload | 400 validation error |

> **Note:** Without `--fresh`, re-running scenario 1–4 returns `200 already_exists` (idempotent by `source_alert_id`). Use `--fresh` to generate a new ID suffix each run.

---

### Очищення тестових даних (`clean_test_data.py`)

Deletes incidents and their related records (`incident_events`, `notifications`) from Cosmos DB.  
**Never touches** seed containers: `equipment`, `batches`, `sop_library`.

```bash
# Dry-run: show what would be deleted, no actual changes
python scripts/clean_test_data.py --dry-run --all

# Delete all incidents (asks for confirmation)
python scripts/clean_test_data.py --all

# Delete specific incidents by ID
python scripts/clean_test_data.py --ids INC-2026-0011 INC-2026-0012

# Delete incidents created in the last 30 minutes
python scripts/clean_test_data.py --last-minutes 30

# Interactive mode: shows list, prompts before deleting
python scripts/clean_test_data.py
```

**Typical test cycle:**

```bash
# 1. Clean up previous test data
python scripts/clean_test_data.py --all

# 2. Run fresh simulation
FUNCTION_URL="..." FUNCTION_KEY="..." python scripts/simulate_alerts.py --fresh --all

# 3. Verify in Azure Portal → Cosmos DB → Data Explorer → incidents
```
