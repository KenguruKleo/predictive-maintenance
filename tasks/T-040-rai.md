# T-040 · RAI Layer (Confidence Gate, Content Safety, Prompt Injection, Observability)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟡 MEDIUM  
**Статус:** 🔜 TODO  
**Gap:** Gap #4 Responsible AI ✅

---

## Мета

Закрити Gap #4: Confidence gate + Azure Content Safety + Prompt injection guard + Agent output observability.

---

## Checklist

### Confidence Gate
- [ ] Document Agent output includes `confidence` float (0.0–1.0)
- [ ] `apply_confidence_gate()` in `run_agents` activity:
  - `confidence < 0.70` → `risk_level = "LOW_CONFIDENCE"`, warning prepended to recommendation
- [ ] Frontend показує red banner якщо `confidence_flag == "LOW_CONFIDENCE"`
- [ ] LOW_CONFIDENCE incidents auto-escalated до qa-manager (not assigned to operator alone)

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
- [ ] Azure App Insights configured on Functions app
- [ ] Custom metric: `agent_run_duration_ms` per agent type
- [ ] Custom metric: `agent_confidence` (track confidence distribution)
- [ ] Custom dimension: `incident_id` on all traces
- [ ] Alert: confidence < 0.5 fires App Insights alert

---

## Definition of Done

- [ ] Confidence gate tested: confidence=0.5 → LOW_CONFIDENCE shown in UI
- [ ] Content Safety check runs on agent output (verified in App Insights logs)
- [ ] Prompt injection attempt in POST /api/alerts `description` field → 400 response
- [ ] App Insights dashboard shows agent traces with durations and confidence metrics
