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

## 4 Indexes

| Index | Namespace | Documents (mock) |
|---|---|---|
| `idx-sop-documents` | `sop` | SOP-DEV-001, SOP-MAN-GR-001, SOP-CLN-GR-002 |
| `idx-equipment-manuals` | `manuals` | GLATT-GPCG60 manual excerpt |
| `idx-gmp-policies` | `gmp` | GMP Annex 15 §6, ICH Q10 Chapter 3 |
| `idx-incident-history` | `history` | 4 closed incidents converted to searchable text |

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
  SOP-DEV-001-Deviation-Management.md        ← already created ✅
  SOP-MAN-GR-001-Granulator-Operation.md     ← create
  SOP-CLN-GR-002-Granulator-Cleaning.md      ← create (brief)
  manuals/GLATT-GPCG60-Manual-Excerpt.md     ← create (key sections)
  gmp/GMP-Annex15-Excerpt.md                 ← create (§6 process validation)
  gmp/ICH-Q10-Excerpt.md                     ← create (§3 quality system)
```

---

## Files

```
scripts/
  create_search_indexes.py    # Create 4 indexes with schema + vector config
  
infra/
  modules/ai-search.bicep     # AI Search service provisioning
```

---

## Definition of Done

- [ ] 4 indexes exist in Azure AI Search portal
- [ ] Each index has vector search enabled (HNSW profile)
- [ ] Minimum 3 chunks per document in each index
- [ ] Semantic search query "impeller speed deviation procedure" → returns SOP-DEV-001 §4.2 result
- [ ] idx-incident-history returns INC-2026-0003 for query "spray nozzle blockage granulator"
- [ ] `create_search_indexes.py` idempotent (safe to run multiple times)
