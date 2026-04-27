# T-040 · RAI Layer (Confidence Gate, Content Safety, Prompt Injection, Observability)

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🟡 MEDIUM
**Status:** 🟡 IN PROGRESS
**Gap:** Gap #4 Responsible AI ✅

---

## Goal

Close Gap #4: Confidence gate + Azure Content Safety + Prompt injection guard + Agent output observability.

Separately, for the hackathon evaluation, it should be noted that hallucination control is not limited to prompt/RAG: after generation, there must be an independent verification pass that checks documents and citations before they enter the decision package.

---

## Checklist

### Confidence Gate
- [ ] Document Agent output includes `confidence` float (0.0–1.0)
- [ ] `apply_confidence_gate()` in `run_agents` activity:
  - `confidence < 0.70` → `risk_level = "LOW_CONFIDENCE"`, warning prepended to recommendation
- [ ] Frontend shows red banner if `confidence_flag == "LOW_CONFIDENCE"`
- [ ] LOW_CONFIDENCE incidents auto-escalated to qa-manager (not assigned to operator alone)

### Grounding / Citation Verification
- [ ] There is a separate post-generation verification pass for `evidence_citations`, `sop_refs`, `regulatory_refs`, `regulatory_reference`
- [ ] Each citation is checked separately: document identity, deep link, section claim, excerpt anchor
- [ ] If there is a document match, but the section claim is not confirmed by the authoritative chunk, the citation remains visible as `unresolved`, but the section does not enter the top-level summary fields
- [ ] Generic placeholders of type `sop`, `gmp` or synthetic section values ​​of type `§15` do not enter the decision summary
- [ ] The UI clearly distinguishes verified evidence from unresolved evidence, and the verified evidence threshold does not count unconfirmed citations

### Content Safety
```python
# backend/utils/content_safety.py
from azure.ai.contentsafety import ContentSafetyClient

async def check_content_safety(text: str) -> bool:
    """Returns True if safe, False if flagged."""
    client = ContentSafetyClient(endpoint=..., credential=DefaultAzureCredential())
    result = await client.analyze_text(AnalyzeTextOptions(text=text))
    # Block if any category >= Medium severity
    return all(c.severity < 4 for c in result.categories_analysis)
```
- [ ] Content safety check on agent output before storing to Cosmos DB
- [ ] Content safety check on incoming alert `description` and `reason` fields
- [ ] If flagged: log to App Insights, set incident `content_safety_flag = True`

### Prompt Injection Guard
```python
# backend/utils/validation.py
INJECTION_PATTERNS = [
    r"ignore (previous|above|all) instructions",
    r"system prompt",
    r"jailbreak",
    r"act as if",
]

def sanitize_string_fields(body: dict) -> dict:
    """Scan string fields for prompt injection patterns. Raises 400 if detected."""
    for key, value in body.items():
        if isinstance(value, str):
            for pattern in INJECTION_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    raise HTTPException(400, f"Invalid input in field '{key}'")
    return body
```
- [ ] Prompt injection check on `description`, `reason`, `question` fields in all POST endpoints

### Observability
- [x] Azure App Insights configured on Functions app
- [x] `run_foundry_agents` emits structured trace records with `incident_id`, `round`, `trace_kind`, and `thread_id` / `run_id` when available
- [x] Prompt and response troubleshooting path is documented in `docs/foundry-followup-analysis.md`
- [ ] Custom metric: `agent_run_duration_ms` per agent type
- [ ] Custom metric: `agent_confidence` (track confidence distribution)
- [ ] Dedicated custom dimensions and metrics pipeline beyond structured trace logs
- [ ] Alert: confidence < 0.5 fires App Insights alert
- [ ] Agent/sub-agent run IDs (`run_id`, `thread_id`) logged with `incident_id` for traceability
- [ ] Tool call telemetry (`tool_name`, `duration_ms`, `status`) logged for each incident
- [ ] Incident-centric telemetry endpoint available for admin analysis (`GET /api/incidents/{id}/agent-telemetry`)
- [ ] Admin dashboard can view agent behavior timeline per incident (integration with T-043)

---

## Script for hackathon demo / review

**Scenario:** `GR-204` spray rate excursion during wet granulation for `Metformin HCl 500mg Tablets`.

1. Research Agent retrieves:
    - `SOP-DEV-001 §4.2 Process Parameter Excursions — Granulation`
    - `EU GMP Annex 15` excerpts from Azure AI Search
2. Document Agent drafts recommendation and citations.
3. Verification layer runs **separately from the reasoning agent** and checks:
- does the cited document exist in the knowledge base;
- does the document identity / link match;
- does the section claim really correspond to the authoritative chunk;
- whether the excerpt can be traced to the retrieved evidence.
4. If the model declares `EU GMP Annex 15 §6.3`, but the authoritative chunk actually corresponds only to `§6.1 General Principles`, then the system behavior should be as follows:
- document `EU GMP Annex 15` remains in visible evidence;
- citation status = `unresolved` for section claim;
- top-level summary should not show unconfirmed section as verified fact.
5. Reviewer / judge must see that the system does not hide evidence, but also does not mask hallucinated citation as a reliable source.

---

## Definition of Done

- [ ] Confidence gate tested: confidence=0.5 → LOW_CONFIDENCE shown in UI
- [ ] Hackathon scenario above is played on fixture or live incident payload and shows separate verification pass
- [ ] Unverified section claims do not enter `regulatory_reference` / summary fields as verified fact
- [ ] Verified vs unresolved evidence visibly different in stored payload / UI contract
- [ ] Content Safety check runs on agent output (verified in App Insights logs)
- [ ] Prompt injection attempt in POST /api/alerts `description` field → 400 response
- [ ] App Insights dashboard or API endpoint shows per-incident agent traces with durations and confidence metrics
- [ ] For a selected incident, admin can reconstruct full AI path (agent -> sub-agent -> tools -> output)
