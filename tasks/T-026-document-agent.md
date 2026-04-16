# T-026 · Document Agent (Azure AI Foundry + Templates + Confidence Gate)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🔴 CRITICAL  
**Статус:** 🔜 TODO  
**Блокує:** T-024 (step 3), T-033 (approval UX shows this output)  
**Залежить від:** T-025 (Research Agent output), T-020 (templates collection)

---

## Мета

Document Agent приймає Research Agent output і formulates the decision package: classification, risk level, CAPA recommendation, work order draft, audit entry draft. Включає confidence gate (RAI Gap #4).

---

## Output schema (structured JSON)

```json
{
  "incident_id": "INC-2026-XXXX",
  "classification": "process_parameter_excursion | equipment_malfunction | ...",
  "risk_level": "low | medium | high | critical | LOW_CONFIDENCE",
  "confidence": 0.84,
  "confidence_flag": null,
  "root_cause_hypothesis": "...",
  "recommendation": "...",
  "capa_suggestion": "1. ...\n2. ...\n3. ...",
  "regulatory_reference": "SOP-DEV-001 §4.2; GMP Annex 15 §6.3",
  "batch_disposition": "conditional_release_pending_testing | rejected | release",
  "evidence_citations": [
    { "source": "SOP-DEV-001", "section": "§4.2", "text_excerpt": "..." },
    { "source": "INC-2026-0003", "relevance": "Similar spray rate deviation — resolved with moisture check" }
  ],
  "work_order_draft": {
    "title": "...",
    "description": "...",
    "priority": "high",
    "estimated_hours": 4
  },
  "audit_entry_draft": {
    "deviation_type": "...",
    "description": "...",
    "root_cause": "...",
    "capa_actions": "..."
  }
}
```

## Confidence Gate (RAI Gap #4)

```python
# In Durable Activity run_agents.py, after Document Agent returns result:
def apply_confidence_gate(result: dict) -> dict:
    if result["confidence"] < 0.70:
        result["confidence_flag"] = "LOW_CONFIDENCE"
        result["risk_level"] = "LOW_CONFIDENCE"
        result["recommendation"] = (
            f"⚠️ AI confidence is low ({result['confidence']:.0%}). "
            f"Manual review by QA required. "
            + result["recommendation"]
        )
    return result
```

**Operator UI показує:** якщо `confidence_flag == "LOW_CONFIDENCE"` → червоний банер "AI Low Confidence — QA Review Required"

---

## System Prompt highlights

```
You are the Document Agent in the Sentinel Intelligence GMP Deviation Management System.

You receive:
1. The original incident alert details
2. Research Agent output (equipment context, batch context, historical cases, SOPs, GMP refs)

Your job:
1. Classify the deviation (use the SOP-DEV-001 classification criteria)
2. Assess risk level (minor/major/critical based on duration and magnitude)
3. Write a concise root cause hypothesis (evidence-based, cite your sources)
4. Generate a numbered CAPA recommendation (immediate action + short-term + long-term)
5. Suggest batch disposition
6. Pre-fill work order draft (using the work order template format)
7. Pre-fill audit entry draft (using the audit entry template format)
8. Assign confidence (0.0–1.0) based on evidence quality

CRITICAL RULES:
- Every claim MUST have an evidence citation (SOP section, historical case, or equipment manual)
- Never fabricate compliance references
- If evidence is insufficient, assign confidence < 0.70 and note what is missing
- Output MUST be valid JSON matching the specified schema
```

---

## Definition of Done

- [ ] Document Agent створений у Foundry з правильними instructions
- [ ] `run_document_agent()` повертає повний structured JSON (всі поля)
- [ ] Confidence gate застосовується: якщо confidence < 0.7 → `risk_level = "LOW_CONFIDENCE"`
- [ ] Evidence citations присутні (мінімум 2 на кожну рекомендацію)
- [ ] Work order draft і audit entry draft коректно заповнені на основі templates
- [ ] Тест на INC-2026-0001 (GR-204 impeller speed): ai_result відповідає очікуваному в mock incident
