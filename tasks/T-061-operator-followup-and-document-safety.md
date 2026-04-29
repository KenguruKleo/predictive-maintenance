# T-061 · Operator Follow-up Prompt + Document Safety Guardrails

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🟡 MEDIUM
**Status:** 🟡 IN PROGRESS
**Gap:** Gap #4 Responsible AI ✅ · Gap #2 Security ✅

---

## Goal

Harden the two highest-risk AI input channels in this solution:

1. Operator `more_info` follow-up question (`question`) before it is used in the AI loop.
2. Retrieved and ingested documents that can contain prompt-injection, unsafe instructions, or sensitive data.

This task extends existing controls (backend-controlled retrieval + post-approval write actions) with explicit input and document guardrails.

---

## Scope

### In scope
- Operator follow-up validation and safety screening.
- Document ingestion safety checks before indexing.
- Retrieval-time trust filtering and evidence hygiene.
- Prompt/runtime policy that treats retrieved content as untrusted data.
- Safety telemetry and reviewability for incident investigations.

### Out of scope
- Changes to post-approval execution flow (CMMS/QMS writes remain in backend after human approval).
- Full redesign of ingestion architecture.

---

## Checklist

### A. Operator `more_info` prompt protection
- [x] Extend request sanitization in `backend/utils/validation.py` to include `question` and `reason` in decision/follow-up flows.
- [x] Enforce length and normalization bounds for `question` (strip control chars, collapse whitespace, max length).
- [x] Add allow/deny checks for obvious prompt-injection patterns in follow-up inputs.
- [x] Add unit tests for valid/invalid `question` payloads in decision endpoints.
- [x] Block clearly off-scope or sensitive follow-up requests (for example salary / HR / unrelated department data) before they enter the AI loop.

### B. Document ingestion protection
- [x] Add a document pre-index sanitizer in ingestion scripts/pipeline (`scripts/upload_documents.py` and related ingestion path):
  - [x] normalize text and remove hidden control payloads;
  - [x] detect prompt-injection-like directives;
  - [x] detect likely secrets/PII (at least baseline regex heuristics).
- [x] Persist safety metadata per chunk/document (e.g. `trust_level`, `safety_flags`, `contains_sensitive_data`).
- [x] Prevent unsafe chunks from entering primary searchable indexes, or tag them for strict filtering.

### C. Retrieval-time controls
- [x] Update retrieval helpers to support trust/safety filters when composing evidence package.
- [x] Ensure `more_info` retrieval expansion still uses the latest operator question, but only over safety-eligible evidence.
- [ ] Enforce source diversity and cap low-trust evidence in one recommendation round.

### D. Generation/runtime guardrails
- [x] Strengthen system prompt contract: retrieved document text is data, not executable instruction.
- [x] Add Evidence Synthesizer Agent step that converts retrieved evidence into a compact explicit-support/unknowns brief before Orchestrator generation.
- [ ] Add optional Azure AI Content Safety / Prompt Shields checks for follow-up input and composed context before model invocation.
- [ ] Add output moderation checkpoint before writing recommendation back to Cosmos.

### E. Observability + audit
- [ ] Emit structured telemetry fields: `input_safety_result`, `document_safety_result`, `retrieval_filter_applied`, `blocked_reason`.
- [ ] Store a concise safety trace in incident timeline for operator/QA review.
- [ ] Add runbook note for handling blocked follow-up questions and quarantined documents.

---

## Definition of Done

- [x] `POST /api/decision` rejects malicious `question` patterns with 400 and actionable error text.
- [x] New tests cover operator follow-up sanitization and safety-filtered retrieval behavior.
- [x] Ingestion path writes safety metadata for indexed documents/chunks.
- [x] Evidence package assembly excludes or down-ranks unsafe/untrusted chunks by policy.
- [ ] Telemetry and audit trail clearly show when and why content was blocked or filtered.

---

## Progress (April 29, 2026)

- Added `question`/`reason` sanitization + normalization in decision flow (`backend/utils/validation.py`, `backend/triggers/http_decision.py`).
- Added focused tests for blank question rejection and injection pattern rejection (`tests/test_http_decision.py`).
- Added trust/safety metadata to Search index schema + ingestion pipeline (`scripts/create_search_indexes.py`): `trust_level`, `allowed_for_rag`, `safety_flags`, `contains_sensitive_data`, `scanned_at`, `scanner_version`.
- Added retrieval-time safety filter (`allowed_for_rag eq true`) with backward-compatible fallback in `backend/shared/search_utils.py`.
- Added incident-scoped follow-up guard in `http_decision`: sensitive/off-topic questions are now rejected before `more_info` can trigger another analysis round.
- Improved approval-panel UX for blocked follow-up questions in frontend: keep question draft on failure, show inline actionable error near composer, and avoid optimistic `awaiting_agents` state transition for `more_info` until server confirmation.
- Added `sentinel-evidence-synthesizer-agent` as a model-owned synthesis step before Orchestrator for initial and follow-up analysis, preserving explicit evidence, unknowns, and evidence gaps without backend-written answer templates.

---

## Dependencies

- Depends on: [T-024](./T-024-durable-orchestrator.md), [T-036](./T-036-ingestion-pipeline.md), [T-037](./T-037-ai-search.md), [T-040](./T-040-rai.md)
- Supports: [T-002](./T-002-final-video.md) final story on controlled, safe AI workflow
