# T-021 · Mock Data Seed Script

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🔴 CRITICAL  
**Статус:** � IN PROGRESS  
**Блокує:** Demo flow, T-025, T-027  
**Залежить від:** T-020 (Cosmos DB provisioned)

> **Що зроблено:** JSON файли готові у `data/mock/` — equipment (3), batches (2), incidents (3), templates (2).  
> **Що залишилось:** `scripts/seed_cosmos.py` — залежить від `backend/cosmos_client.py` (T-020).

---

## Мета

Заповнити Cosmos DB mock даними для demo. JSON файли вже є в `data/mock/`. Потрібен Python script для їх завантаження.

---

## Scope mock даних

| Collection | Данні | Файл |
|---|---|---|
| `equipment` | 3 units: GR-204, MIX-102, DRY-303 | `data/mock/equipment.json` |
| `batches` | **20 batches** (2026: 11; 2025: 9) — 3 equipment × 6 products | `data/mock/batches.json` |
| `incidents` | **30 incidents** (INC-2026-0001–0010; INC-2025-0001–0020) — всі типи | `data/mock/incidents.json` |
| `templates` | 2 templates (work order, audit entry) | `data/mock/templates.json` |

**Demo scenarios покриті в incidents.json:**
- `INC-2026-0001`: **pending_approval** — основный demo сценарій (GR-204 impeller)
- `INC-2026-0006`: **pending_approval** — другий оператор (MIX-102 speed)
- `INC-2026-0008`: **LOW_CONFIDENCE** (confidence=0.58) — попередження оператору
- `INC-2026-0007`: **escalated** (24h timeout → QA Manager)
- `INC-2026-0010`: **BLOCKED** (confidence=0.31, no evidence → auto-escalate)
- `INC-2025-0001–0020`: **historical cases** для RAG (Research Agent semantic search)

---

## Файл

```
scripts/
  seed_cosmos.py
```

## Logic

```python
# seed_cosmos.py
# 1. Load .env
# 2. CosmosClient via DefaultAzureCredential (or key for local)
# 3. For each collection: upsert all items from JSON file
# 4. For each closed incident: generate incident_events from resolution data
# 5. Print summary: "Seeded X items into Y collections"

# Usage:
#   python scripts/seed_cosmos.py
#   python scripts/seed_cosmos.py --reset   # delete all first
```

## Definition of Done

- [x] JSON файли: equipment.json (3), batches.json (**20**), incidents.json (**30**), templates.json (2)
- [ ] `python scripts/seed_cosmos.py` запускається без помилок
- [ ] Cosmos DB містить 3 equipment, **20 batches**, **30 incidents**, 2 templates
- [ ] `python scripts/seed_cosmos.py --reset` очищує і перезасіває
