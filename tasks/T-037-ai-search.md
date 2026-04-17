# T-037 · AI Search Indexes + Mock Documents

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟠 HIGH  
**Статус:** 🔜 TODO  
**Блокує:** T-025 (Research Agent RAG tools), T-036 (needs indexes to exist before populating)  
**Gap:** Gap #4 RAI

---

## Мета

Створити 4 Azure AI Search indexes з правильними схемами та заповнити mock документами (chunked).

---

## 5 Indexes

| Index | Namespace | Documents (mock) |
|---|---|---|
| `idx-sop-documents` | `sop` | SOP-DEV-001, SOP-MAN-GR-001, SOP-CLN-GR-002 |
| `idx-equipment-manuals` | `manuals` | GLATT-GPCG60 manual excerpt |
| `idx-gmp-policies` | `gmp` | GMP Annex 15 §6, ICH Q10 Chapter 3 |
| `idx-bpr-documents` | `bpr` | BPR-MET-500-v3.2, BPR-ATV-020-v2.1, BPR-PCT-500-v2.0 |
| `idx-incident-history` | `history` | 4 closed incidents converted to searchable text |

> **Why a separate BPR index?** BPR documents contain product-specific CPP ranges that override equipment-level PAR. Keeping them in a dedicated index allows the Research Agent to explicitly query "product specification" vs "general procedure" with a single `document_type` filter, reducing hallucination risk when the agent is comparing product NOR vs equipment PAR.

---

## Index Schema (same for all 4)

```python
fields = [
    SimpleField("id", type=SearchFieldDataType.String, key=True),
    SimpleField("document_id", type=SearchFieldDataType.String, filterable=True),
    SearchableField("document_title", type=SearchFieldDataType.String),
    SimpleField("document_type", type=SearchFieldDataType.String, filterable=True),
    SimpleField("chunk_index", type=SearchFieldDataType.Int32),
    SearchableField("text", type=SearchFieldDataType.String),
    SearchField("embedding", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True, vector_search_dimensions=1536,
        vector_search_profile_name="hnsw-profile"),
    SimpleField("equipment_ids", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True),
    SimpleField("source_url", type=SearchFieldDataType.String),
]
```

---

## Mock documents to create

```
data/documents/
  SOP-DEV-001-Deviation-Management.md              ← already created ✅
  SOP-MAN-GR-001-Granulator-Operation.md           ← created ✅
  SOP-CLN-GR-002-Granulator-Cleaning.md            ← created ✅
  manuals/GLATT-GPCG60-Manual-Excerpt.md           ← created ✅
  gmp/GMP-Annex15-Excerpt.md                       ← created ✅
  gmp/ICH-Q10-Excerpt.md                           ← created ✅
  bpr/BPR-MET-500-v3.2-Process-Specification.md   ← created ✅
  bpr/BPR-ATV-020-v2.1-Process-Specification.md   ← created ✅
  bpr/BPR-PCT-500-v2.0-Process-Specification.md   ← created ✅
```

---

## Files

```
scripts/
  create_search_indexes.py    # Create 5 indexes with schema + vector config
  
infra/
  modules/ai-search.bicep     # AI Search service provisioning
```

---

## Definition of Done

- [ ] 5 indexes exist in Azure AI Search portal
- [ ] Each index has vector search enabled (HNSW profile)
- [ ] Minimum 3 chunks per document in each index
- [ ] Semantic search query "impeller speed deviation procedure" → returns SOP-DEV-001 §4.2 result
- [ ] Semantic search query "Metformin validated spray rate range" → returns BPR-MET-500 §3.2 result
- [ ] idx-incident-history returns INC-2026-0003 for query "spray nozzle blockage granulator"
- [ ] `create_search_indexes.py` idempotent (safe to run multiple times)
