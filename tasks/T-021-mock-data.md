# T-021 · Mock Data Seed Script

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🔴 CRITICAL
**Status:** ✅ DONE
**Blocks:** Demo flow, T-025, T-027
**Depends on:** T-020 (Cosmos DB provisioned)

> **Completed April 17, 2026:** 55 items uploaded to Cosmos DB.
> equipment (3) · batches (20) · incidents (30) · templates (2).  
> Auth: `COSMOS_KEY` env var (for running locally). DefaultAzureCredential for Azure Functions (requires Cosmos RBAC assignment).
> Idempotent: `upsert_item()` - can be restarted.

---

## Goal

Fill Cosmos DB with mock data for the demo. JSON files are already in `data/mock/`. You need a Python script to download them.

---

## Scope mock data

| Collection | Data | File |
|---|---|---|
| `equipment` | 3 units: GR-204, MIX-102, DRY-303 | `data/mock/equipment.json` |
| `batches` | **20 batches** (2026: 11; 2025: 9) — 3 equipment × 6 products | `data/mock/batches.json` |
| `incidents` | **30 incidents** (INC-2026-0001–0010; INC-2025-0001–0020) — all types | `data/mock/incidents.json` |
| `templates` | 2 templates (work order, audit entry) | `data/mock/templates.json` |

**Demo scenarios covered in incidents.json:**
- `INC-2026-0001`: **pending_approval** — the main demo script (GR-204 impeller)
- `INC-2026-0006`: **pending_approval** — the second operator (MIX-102 speed)
- `INC-2026-0008`: **LOW_CONFIDENCE** (confidence=0.58) — operator warning
- `INC-2026-0007`: **escalated** (24h timeout → QA Manager)
- `INC-2026-0010`: **BLOCKED** (confidence=0.31, no evidence → auto-escalate)
- `INC-2025-0001–0020`: **historical cases** for RAG (Research Agent semantic search)

---

## File

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

- [x] JSON files: equipment.json (3), batches.json (**20**), incidents.json (**30**), templates.json (2)
- [ ] `python scripts/seed_cosmos.py` starts without errors
- [ ] Cosmos DB contains 3 equipment, **20 batches**, **30 incidents**, 2 templates
- [ ] `python scripts/seed_cosmos.py --reset` cleans and reseeds
