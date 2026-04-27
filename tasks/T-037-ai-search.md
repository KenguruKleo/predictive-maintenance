# T-037 · AI Search Indexes + Mock Documents

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🟠 HIGH
**Status:** ✅ DONE
**Blocks:** T-025 (Research Agent RAG tools), T-036 (needs indexes to exist before populating)
**Gap:** Gap #4 RAI

> **Completed 17 April 2026:** `srch-sentinel-intel-dev-erzrpo` (westeurope, basic SKU) + `oai-sentinel-intel-dev-erzrpo` (swedencentral, S0) deployed. 9 Doc. loaded up to 4 blob containers. 5 indexes created, **117 chunks** indexed with HNSW vector embeddings (1536d, `text-embedding-3-small`). Spot-checks passed.

---

## Goal

Create 4 Azure AI Search indexes with the correct schemas and fill them with mock documents (chunked).

---

## 5 Indexes

| Index | Namespace | Documents (mock) | Chunks |
|---|---|---|---|
| `idx-sop-documents` | `sop` | SOP-DEV-001, SOP-MAN-GR-001, SOP-CLN-GR-002 | 12 |
| `idx-equipment-manuals` | `manuals` | GLATT-GPCG60 manual excerpt | 6 |
| `idx-gmp-policies` | `gmp` | GMP Annex 15 §6, ICH Q10 Chapter 3 | 12 |
| `idx-bpr-documents` | `bpr` | BPR-MET-500-v3.2, BPR-ATV-020-v2.1, BPR-PCT-500-v2.0 | 62 |
| `idx-incident-history` | `history` | 25 closed incidents from Cosmos DB | 25 |

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
  upload_documents.py         # Upload data/documents/{sop,manuals,gmp,bpr}/ → blob containers
  create_search_indexes.py    # Create 5 indexes + chunk + embed + upsert (idempotent)
  
infra/
  modules/ai-search.bicep     # AI Search service provisioning (westeurope, basic SKU)
  modules/openai.bicep        # Azure OpenAI S0 + text-embedding-3-small + gpt-4o deployments
```

---

## Definition of Done

- [x] 5 indexes exist in Azure AI Search portal
- [x] Each index has vector search enabled (HNSW profile)
- [x] Minimum 3 chunks per document in each index
- [x] Semantic search query "impeller speed deviation procedure" → returns BPR-MET-500 result (score 5.13)
- [x] Semantic search query "Metformin validated spray rate range" → returns BPR-MET-500 §3.2 result
- [x] idx-incident-history returns closed incidents for equipment deviation queries
- [x] `create_search_indexes.py` idempotent (safe to run multiple times via `create_or_update_index`)
