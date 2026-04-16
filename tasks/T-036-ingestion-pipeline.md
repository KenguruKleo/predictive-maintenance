# T-036 · Document Ingestion Pipeline (Blob → Chunk → Embed → AI Search)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟠 HIGH  
**Статус:** 🔜 TODO  
**Блокує:** T-037 (AI Search indexes populated), T-025 (Research Agent RAG calls)  
**Залежить від:** T-020 (Cosmos DB not strictly, but same infra setup time)  
**Gap:** Gap #4 RAI (RAG quality)

---

## Мета

Pipeline для завантаження SOP/manual документів у Azure Blob Storage → автоматичне chunking та embedding → Azure AI Search indexes.

---

## Flow

```
Upload .md/.pdf/.docx to Blob Storage (container: documents)
    │
    ▼
Azure Function: blob_trigger_ingest (triggered on new blob)
    │
    ├── Parse document (markdown/PDF/DOCX → plain text)
    ├── Split into chunks (500 tokens, 50 overlap)
    ├── Generate embeddings (Azure OpenAI text-embedding-3-small)
    └── Upsert to correct AI Search index based on blob path prefix
         ├── documents/sop/       → idx-sop-documents
         ├── documents/manuals/   → idx-equipment-manuals
         ├── documents/gmp/       → idx-gmp-policies
         └── documents/history/   → idx-incident-history
```

---

## Blob structure

```
documents/
  sop/
    SOP-DEV-001-Deviation-Management.md     ← already in data/documents/
    SOP-MAN-GR-001-Granulator-Operation.md
    SOP-CLN-GR-002-Granulator-Cleaning.md
  manuals/
    GLATT-GPCG60-Operation-Manual.md
  gmp/
    GMP-Annex15-Qualification-Validation.md
    ICH-Q10-Pharmaceutical-Quality-System.md
  history/
    (generated from closed incidents for semantic search)
```

---

## Files

```
backend/
  triggers/
    blob_trigger_ingest.py    # @app.blob_trigger
  ingestion/
    chunker.py                # split_text(text, chunk_size=500, overlap=50)
    embedder.py               # get_embedding(text) via Azure OpenAI
    search_upserter.py        # upsert_chunk(index_name, chunk_doc)

scripts/
  upload_documents.py         # Upload data/documents/ to Blob Storage
  generate_history_chunks.py  # Convert closed incidents → history docs → upload
```

---

## AI Search document schema

```json
{
  "id": "SOP-DEV-001-chunk-003",
  "document_id": "SOP-DEV-001",
  "document_title": "GMP Deviation Management Procedure",
  "document_type": "sop",
  "chunk_index": 3,
  "text": "...",
  "embedding": [ ... 1536 floats ... ],
  "equipment_ids": ["GR-204", "MIX-102"],
  "keywords": ["impeller", "deviation", "major"],
  "source_url": "https://blob.../documents/sop/SOP-DEV-001.md"
}
```

---

## Definition of Done

- [ ] `scripts/upload_documents.py` uploads all mock docs to Blob Storage
- [ ] Blob trigger fires and chunks/embeds new documents automatically
- [ ] 4 AI Search indexes contain chunks from mock documents (verify with portal)
- [ ] Research Agent semantic search returns relevant results for GR-204 impeller deviation query
- [ ] `generate_history_chunks.py` creates incident history documents from closed incidents
