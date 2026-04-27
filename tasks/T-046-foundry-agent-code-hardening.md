# T-046 · Foundry Agent Code Hardening (post-demo)

← [04 · Action Plan](../04-action-plan.md)

> **Priority:** 🟢 LOW — does not block demo, run after finals
> **Source:** Code review `run_foundry_agents.py` (April 20, 2026)
> **Status:** 🔜 TODO

---

## Context

During the in-depth review of `backend/activities/run_foundry_agents.py`, a number of issues were identified that do not affect the demo, but are important for production-ready code and GxP compliance.

**Already fixed (April 20, 2026):**
- ✅ `_build_agents_client()` — removed `os.environ.setdefault("AZURE_AI_AGENTS_TESTS_IS_TEST_RUN", "True")` (test flag in production code)
- ✅ `_infer_known_document()` - added explicit comment HACKATHON ONLY + `KNOWN_DOCUMENT_FALLBACK_DISABLED` env var to disable
- ✅ Hardcoded fallback Agent ID — documented as a HACKATHON, it can be seen that it needs to be removed before production

---

## Remaining issues to resolve

### 1. `_infer_known_document()` — delete or replace (MEDIUM)

**File:** `backend/activities/run_foundry_agents.py`

The function hardcodes blob paths for specific documents (SOP-DEV-001, SOP-MAN-GR-001, GMP-Annex15, BPR-MET-500). If the document is renamed to Azure Blob Storage, the references will silently become invalid, but the UI will show a "resolved" citation.

**Correct approach:** AI Search index is the only source of truth. The document is matched via `_find_matching_hit`. If `source_blob` does not come from the index, this is a problem with the quality of the index (the field must be indexed), and not a reason to hardcode the mapping in Python.

**Action:** Check that AI Search `idx-sop-documents`, `idx-gmp-policies`, `idx-bpr-documents` return `source` field for all mock documents → remove `_infer_known_document()` → enable through `KNOWN_DOCUMENT_FALLBACK_DISABLED=true`.

---

### 2. `_has_direct_stop_requirement()` — keyword matching for GxP dialog (MEDIUM)

**File:** `backend/activities/run_foundry_agents.py`

```python
stop_markers = (
    "stop the line", "must stop", "halt production",
    "production must be stopped", "hold the batch",
    "batch must be held", "reject the batch",
)
```

This function determines what to say to the operator ("the document requires a stop"). If the SOP uses `"cease operations"`, `"suspend batch"`, `"discontinue processing"` - they will not work. For GxP, dialogue is a risk.

**Correct approach:** Let the Document Agent answer this question explicitly in `operator_dialogue`. Add a section to `document_system.md`: if the operator asks "does the document require stopping" - the Document Agent should give a direct answer "Yes/No, because [excerpt]", without relying on post-processing.

**Action:** Improve `document_system.md` + `orchestrator_system.md` → gradually replace `_has_direct_stop_requirement()` → check via Foundry evaluation.

---

### 3. `time.sleep(stagger)` in Durable Activity (LOW)

**File:** `backend/activities/run_foundry_agents.py`

```python
# line ~153 — up to 60 seconds of sleep, 25% of the 240-second budget
time.sleep(stagger)
```

Thundering herd prevention through `time.sleep` in Activity has disadvantages:
- 60 seconds = 25% of the Activity budget is spent waiting for the start
- With orchestrator replay stagger is calculated again (may differ)
- Durable Activity is not intended for long sleeps

**Correct approach:** Rate limit throttling should be resolved in the orchestrator via `context.create_timer()` (Durable-aware) or via Service Bus sessions/lease. Or rely on retry-with-backoff in `_call_orchestrator_agent()` (it already exists and is well implemented).

**Action:** Check whether thundering herd is really a problem after retry-backoff implementation → if not, remove sleep → if so, transfer to orchestrator.

---

### 4. Confidence gate — only log, no blocking (LOW)

**File:** `backend/activities/run_foundry_agents.py`

```python
if confidence < CONFIDENCE_THRESHOLD:
    result["confidence_flag"] = "LOW_CONFIDENCE"
# but nothing gets blocked
```

`confidence_flag` is set, but the orchestrator doesn't do anything with it automatically. The operator can approve the incident with `confidence=0.1`.

**Action:** Check that the approval UX (T-033) shows a confidence badge → decide: whether to block approve when `confidence_flag == LOW_CONFIDENCE`, or whether a warning is enough.

---

### 5. RAG parameters are not configured (LOW)

**File:** `backend/activities/run_foundry_agents.py`

```python
search_all_indexes(query=search_query, equipment_id=equipment_id, top_k=3)
# ...
hit['text'][:600]  # prompt truncation hardcoded
```

`top_k=3` and truncation of 600 characters affect parsing quality and should be env vars.

**Action:** Add `RAG_TOP_K` (default 3) and `RAG_EXCERPT_CHARS` (default 600) env vars.

---

### 6. Dialog rewriting layer — simplify or remove (LOW)

`_normalize_operator_dialogue()` → `_should_rewrite_followup_dialogue()` — complex post-processing of LLM output with `SequenceMatcher` threshold `0.88`. The logic is correct, but:
- Masks system prompt quality issues
- Makes debugging more difficult (what LLM said vs. what is shown)
- Can rewrite the correct output

**Action:** After finals — conduct Foundry evaluation `operator_dialogue` of quality → if LLM with improved prompt consistently gives quality output, remove or significantly simplify `_normalize_operator_dialogue()`.

---

## What not to touch

| Solution | Why leave |
|---|---|
| Hard JSON schema in prompt | Correct for GxP |
| `raw_response` is always stored | Audit trail |
| RAG pre-fetch before prompt | Grounding to LLM |
| `NEVER fabricate` in orchestrator system prompt | Reduces hallucinations
| `_citation_points_to_incident()` filter | Current incident ≠ evidence |
| Rate limit retry with backoff + jitter | Production-ready |
| `_build_agent_failure_result()` | Controlled degraded mode |
| `_parse_response()` graceful fallback | Don't fall for incorrect JSON |

---

## Definition of Done

- [ ] `_infer_known_document()` removed or replaced with index-based lookup
- [ ] `KNOWN_DOCUMENT_FALLBACK_DISABLED=true` in production settings
- [ ] `_has_direct_stop_requirement()` replaced by LLM-based response in `document_system.md`
- [ ] The starting sleep (`time.sleep(stagger)`) has been removed or moved to the orchestrator
- [ ] `RAG_TOP_K` and `RAG_EXCERPT_CHARS` env vars added
- [ ] Regression tests passed
