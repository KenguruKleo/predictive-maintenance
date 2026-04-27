# T-045 · Evidence Citations Quality + Historical Evidence Links

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🟠 HIGH
**Status:** ✅ DONE
**Blocks:** Trustworthy demo evidence UX / operator confidence in recommendation package
**Depends on:** T-026 (Document Agent), T-031 (Backend API), T-032 (Frontend core), T-037 (AI Search indexes)

---

## Goal

Improve the quality of the `Evidence From Documents` block so that every visible card is canonical, clear, without duplicates, with a working link, sufficient context in the excerpt, and without hallucinatory fallback labels like `Evidence source`.

---

## Progress (April 19-20, 2026)

- [x] Frontend incident detail now reads only `ai_analysis.evidence_citations` for visible evidence cards.
- [x] Backend normalization now emits canonical citations with `resolution_status` / `unresolved_reason` instead of relying on fake fallback titles.
- [x] Dedupe moved to canonical identity (`document_id` / `source_blob` / `url` + `section`) instead of display title.
- [x] Short excerpts are backfilled from matched AI Search chunks to a contextful 180–300 character snippet.
- [x] Historical citations now resolve to `/incidents/:id` deep links instead of pretending to be blob documents.
- [x] Historical indexing now excludes `rejected` and non-approved closed incidents; only approved `closed` / `completed` precedents are indexed.
- [x] Focused regression tests cover canonical dedupe, unresolved evidence, excerpt backfill, historical links, and approved-history indexing.
- [x] Live/manual rebuild of `idx-incident-history` completed from current Cosmos incidents; the live index now contains `INC-2026-0005`, `INC-2026-0006`, and `INC-2026-0013`.
- [x] Automatic history-index sync code was added to `finalize_audit`, covered by focused backend tests, and deployed to the live Function App.
- [x] Direct historical retrieval path now returns live precedent hits for the same query the agent uses (`spray rate deviation criticality GR-204`).
- [x] **Incident citations now generate proper `/incidents/{document_id}` URLs** — fixed `_citation_url()` to handle `type="incident"`, added 4 unit tests for URL generation.
- [x] Document Agent prompts updated to explicitly require primary incident citation with `type: "incident"` and `document_id` in `evidence_citations`.
- [x] Backend deployed with incident citation URL fix.
- [x] AI Search ingestion now stores authoritative chunk-level section metadata (`section_heading`, `section_key`, `section_path`) for SOP/BPR/manual/GMP docs and incident-history chunks.
- [x] Citation normalization now uses soft authoritative matching: document/source match + excerpt anchor + section claim decide the best chunk; excerpt-anchored mismatches are corrected to the authoritative section, while unverifiable section claims stay visible as `unresolved` instead of dropping the whole document.
- [x] Focused regression coverage added for heading-aware ingestion metadata, section metadata retrieval from search hits, authoritative section correction, and unresolved downgrade when only the document can be matched.
- [ ] Full live end-to-end validation pending: re-run search indexing for affected indexes and deploy the updated backend before creating a fresh incident to confirm corrected/unresolved section behavior in the live UI.

---

## Context / problem

The current UX review of live incident `INC-2026-0013` showed several system problems in the presentation layer evidence cards:

1. Frontend now mixes `evidence_citations`, `sop_refs` and `regulatory_refs`, so the same base can be rendered multiple times with different quality.
2. The backend allows partial citations without stable `document_title` / `source_blob` / `url`, after which the UI substitutes generic labels (`Evidence source`, `GMP reference`) instead of the real document name.
3. Dedupe is based on the display title, section and excerpt, and not on the canonical identity of the document, due to which `Deviation Management (SOP-DEV-001)` and `Evidence source` diverge into separate cards.
4. `text_excerpt` is often too short or uneven: sometimes it's 1 line without context, sometimes it's just a fragment with no clear connection to the solution.
5. Historical incidents have a separate structural mismatch:
- `idx-incident-history` is now generated directly from Cosmos incident records, without a real blob artifact;
- evidence normalization maps these results to `blob-history`, so historical citations do not have a reliable document link contract;
- the indexer currently takes `closed`, `resolved`, `rejected`, while evidence reuse requires a business-rule review: consider only previous incidents that actually passed the approved/closed lifecycle, not rejected cases.

> **Important:** do not fix legacy/test incidents in the database manually. It is necessary to correct only the code contract, normalization, indexing rules and UI rendering.

---

## Scope

### 1. `evidence_citations` as the only source of truth for UI

- Frontend should render document evidence only with `ai_analysis.evidence_citations`.
- `sop_refs` and `regulatory_refs` remain backend/model-facing fields, but are not mixed directly into the UI as separate cards.
- The backend must itself canonicalize the data from `sop_refs` / `regulatory_refs` / `evidence_citations` into a single normalized list before saving the incident payload.

### 2. Hard citation contract on the backend

Each **visible** card of type `document evidence` must have:

- `document_title`
- `section`
- `text_excerpt` with normal context
- either `url`, or a pair of `container + source_blob`, or a separate canonical incident link contract for a historical case

If the citation does not pass this contract:

- do not show it as an ordinary document card;
- transfer to a separate unresolved state with clear marking on the UI, and not mask it under `Evidence source`.

### 3. Canonical dedupe

Refactor the dedupe key so that it is based on the canonical document identity:

- `document_id`, if it exists;
- else `source_blob`;
- otherwise canonical historical incident id / URL;
- plus `section`.

Display title should not participate as a primary dedupe key.

### 4. Quality of excerpts

- Do not show raw full chunk as is.
- Do not leave 1 short line without context, if you can backfill a better excerpt.
- Target format: approximately 180–300 characters or 1–2 sentences around the matching fragment.
- If the agent returned a weak `text_excerpt`, the backend should backfill an excerpt from the matched AI Search hit / source chunk.

### 5. Historical incidents as evidence

- Define and record a business rule, which previous incidents can generally be used as evidence.
- Current policy candidate: include only cases that passed operator approval and ended in `closed` / `completed` (or another clearly agreed equivalent), exclude `rejected`.
- Check the discrepancy between:
  - search indexing (`closed` / `resolved` / `rejected`),
  - API/list semantics (`approved` / `closed` / `executed` / `completed`),
- UX expectations for similar cases.
- Historical citations should be opened via the working incident link:
- or deep-link to the incident detail,
- or a special API endpoint for historical preview,
- but not through `blob-history` if there is no physical blob.

### 6. UI presentation

- For canonical document cards, show the understandable name of the document, section, excerpt, type badge and working link.
- For historical evidence, show a separate type of card (`History` / `Similar incident`) with incident id, status, date and reference to the incident.
- For unresolved evidence, show a separate explicit marking (`Unresolved evidence`) instead of a generic fake title.

---

## Expected changes in files

### Backend

```text
backend/activities/run_foundry_agents.py
backend/shared/search_utils.py
backend/triggers/http_incidents.py # if historical link / payload enrichment is needed
backend/triggers/http_documents.py # only if the need for a separate historical preview route is confirmed
scripts/create_search_indexes.py            # status policy for idx-incident-history
```

### Frontend

```text
frontend/src/utils/analysis.ts
frontend/src/components/Incident/EvidenceCitations.tsx
frontend/src/types/incident.ts
```

### Tests

```text
tests/...
frontend/... tests if present
```

---

## Definition of Done

- [x] UI renders document evidence only with normalized `evidence_citations`
- [x] Duplicates with different display titles do not appear for one document/section
- [x] Labels `Evidence source`, `SOP reference`, `GMP reference` no longer appear for canonical document cards
- [x] Every visible document card has a working `Open document` link
- [x] Historical evidence cards have a working `Open incident` or equivalent link
- [x] Historical evidence uses only incident statuses agreed as valid precedent (without rejected cases)
- [x] `text_excerpt` in canonical cards has enough context, not 1 line without meaning
- [x] Non-canonical citations are not disguised as a document, but are shown as unresolved evidence or are not rendered as a card
- [x] Added focused regression tests on normalization, dedupe, unresolved state and historical link semantics
- [ ] Live/manual validation on the incident detail screen shows a clear, unduplicated, linkable evidence block

---

## Validation script

1. Incident with SOP + GMP evidence, where duplicates of `document title` vs `Evidence source` previously appeared
2. Incident with a very short `text_excerpt`, where the backend should backfill a better snippet
3. Incident with similar historical cases, where the card should lead to the historical incident detail, and not to the fake blob link
4. Negative case: rejected historical incident should not fall into visible precedent evidence

---

## Notes

- This is a task on code-path quality, not on cleanup test data.
- If it turns out that historical cases are not logically `documents`, you can rename the UI block or split it to `Evidence From Documents` + `Similar Historical Incidents`, but only after agreeing on the UX direction.
