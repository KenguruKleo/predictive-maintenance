# T-040 · RAI Layer (Confidence Gate, Content Safety, Prompt Injection, Observability)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟡 MEDIUM  
**Статус:** 🟡 IN PROGRESS  
**Gap:** Gap #4 Responsible AI ✅

---

## Мета

Закрити Gap #4: Confidence gate + Azure Content Safety + Prompt injection guard + Agent output observability.

Окремо зафіксувати для хакатонної оцінки, що hallucination control не зводиться лише до prompt/RAG: після генерації має існувати незалежний verification pass, який перевіряє документи та citations перед тим, як вони потрапляють у decision package.

---

## Checklist

### Confidence Gate
- [ ] Document Agent output includes `confidence` float (0.0–1.0)
- [ ] `apply_confidence_gate()` in `run_agents` activity:
  - `confidence < 0.70` → `risk_level = "LOW_CONFIDENCE"`, warning prepended to recommendation
- [ ] Frontend показує red banner якщо `confidence_flag == "LOW_CONFIDENCE"`
- [ ] LOW_CONFIDENCE incidents auto-escalated до qa-manager (not assigned to operator alone)

### Grounding / Citation Verification
- [ ] Існує окремий post-generation verification pass для `evidence_citations`, `sop_refs`, `regulatory_refs`, `regulatory_reference`
- [ ] Для кожної citation перевіряється окремо: document identity, deep link, section claim, excerpt anchor
- [ ] Якщо document match є, але section claim не підтверджується authoritative chunk, citation лишається visible як `unresolved`, але section не потрапляє в top-level summary fields
- [ ] Generic placeholders типу `sop`, `gmp` або synthetic section values типу `§15` не потрапляють у decision summary
- [ ] UI чітко відрізняє verified evidence від unresolved evidence, а verified evidence threshold не рахує непідтверджені citations

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

## Сценарій для hackathon demo / review

**Scenario:** `GR-204` spray rate excursion during wet granulation for `Metformin HCl 500mg Tablets`.

1. Research Agent retrieves:
    - `SOP-DEV-001 §4.2 Process Parameter Excursions — Granulation`
    - `EU GMP Annex 15` excerpts from Azure AI Search
2. Document Agent drafts recommendation and citations.
3. Verification layer runs **окремо від reasoning агента** and checks:
    - чи існує cited document у knowledge base;
    - чи збігається document identity / link;
    - чи section claim реально відповідає authoritative chunk;
    - чи excerpt можна простежити до retrieved evidence.
4. Якщо модель заявляє `EU GMP Annex 15 §6.3`, але authoritative chunk реально відповідає лише `§6.1 General Principles`, то system behavior має бути таким:
    - документ `EU GMP Annex 15` залишається у visible evidence;
    - citation status = `unresolved` для section claim;
    - top-level summary не повинен показувати непідтверджену секцію як verified fact.
5. Reviewer / judge повинен побачити, що система не приховує evidence, але й не маскує hallucinated citation як достовірне джерело.

---

## Definition of Done

- [ ] Confidence gate tested: confidence=0.5 → LOW_CONFIDENCE shown in UI
- [ ] Hackathon scenario вище відтворюється на fixture або live incident payload і показує separate verification pass
- [ ] Unverified section claims не потрапляють у `regulatory_reference` / summary fields як verified fact
- [ ] Verified vs unresolved evidence visibly different in stored payload / UI contract
- [ ] Content Safety check runs on agent output (verified in App Insights logs)
- [ ] Prompt injection attempt in POST /api/alerts `description` field → 400 response
- [ ] App Insights dashboard or API endpoint shows per-incident agent traces with durations and confidence metrics
- [ ] For a selected incident, admin can reconstruct full AI path (agent -> sub-agent -> tools -> output)
