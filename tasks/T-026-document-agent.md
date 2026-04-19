# T-026 · Document Agent (Azure AI Foundry Connected Agents — sub-agent)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🔴 CRITICAL  
**Статус:** ✅ DONE (18-19 квітня 2026; updated 19 квітня 2026 for round-0 operator_dialogue hardening)  
**Блокує:** T-024 (run_foundry_agents activity), T-033 (approval UX shows this output)  
**Залежить від:** T-024 (Orchestrator Agent), T-025 (Research Agent output via Orchestrator), T-020 (templates collection)

> **ADR-002:** Document Agent є **sub-agent** в Foundry Connected Agents pattern.  
> Orchestrator Agent підключає його як `AgentTool` і передає Research Agent output безпосередньо в контексті thread — **не через Durable state**.  
> Дивись [02-architecture §8.10b](../02-architecture.md#810b-adr-002-foundry-connected-agents-vs-ручна-оркестрація).

---

## Мета

Document Agent є sub-agent Foundry Orchestrator Agent (Connected Agents pattern).  
Orchestrator Agent передає йому Research Agent output та alert context через thread всередині размови — Document Agent формує decision package: classification, risk level, CAPA recommendation, work order draft, audit entry draft.  
Включає confidence gate (RAI Gap #4).

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
# activities/run_foundry_agents.py — after Foundry Orchestrator Agent returns result:
def apply_confidence_gate(result: dict) -> dict:
    confidence = result["confidence"]
    evidences = result.get("evidence_citations", [])

    if confidence >= 0.70:
        pass  # normal flow
    elif confidence < 0.70 and len(evidences) > 0:
        # LOW_CONFIDENCE: show warning, require operator comment
        result["confidence_flag"] = "LOW_CONFIDENCE"
        result["risk_level"] = "LOW_CONFIDENCE"
        result["recommendation"] = (
            f"⚠️ AI впевненість низька ({confidence:.0%}). Коментар QA обов'язковий. \n"
            + result["recommendation"]
        )
    else:
        # BLOCKED: no evidence — do not show recommendation, auto-escalate
        result["confidence_flag"] = "BLOCKED"
        result["risk_level"] = "BLOCKED"
        result["recommendation"] = None
        result["escalation_required"] = True
        result["escalation_reason"] = "Insufficient evidence for AI recommendation"
    return result
```

**Operator UI показує:**
- `confidence_flag == None` → normal recommendation display
- `confidence_flag == "LOW_CONFIDENCE"` → червоний банер + коментар обов'язковий перед approve
- `confidence_flag == "BLOCKED"` → recommendation не видно; авто-ескалація до QA Manager

## Реєстрація як AgentTool (у orchestrator_agent.py)

Document Agent **не має окремої функції запуску**. Orchestrator Agent реєструє його як `AgentTool`:

```python
# agents/orchestrator_agent.py — фрагмент create_agents.py
from azure.ai.projects.models import AgentTool

document_agent_id = os.environ["DOCUMENT_AGENT_ID"]
document_tool = AgentTool(agent_id=document_agent_id)

orchestrator = client.agents.create_agent(
    model="gpt-4o",
    name="sentinel-orchestrator",
    instructions="...",  # orchestrator_system.md
    tools=[research_tool, document_tool],
    tool_resources={},
)
```

Orchestrator Agent передає Research Agent output у Document Agent через thread context (нативний Foundry механізм).  
Без окремого Durable state serialization.

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
- [ ] Document Agent зареєстрований як `AgentTool` в Orchestrator Agent (T-024)
- [ ] Orchestrator Agent передає Research Agent output в Document Agent через thread context
- [ ] Document Agent повертає повний structured JSON (всі поля зі схеми вище)
- [ ] Confidence gate застосовується в `run_foundry_agents.py`: confidence < 0.7 → `risk_level = "LOW_CONFIDENCE"`
- [ ] Evidence citations присутні (мінімум 2 на кожну рекомендацію)
- [ ] Work order draft і audit entry draft коректно заповнені на основі templates
- [ ] Тест на INC-2026-0001 (GR-204 impeller speed): ai_result відповідає очікуваному в mock incident

## Post-completion hardening (19 квітня 2026)

- `run_foundry_agents.py` now rewrites impossible initial transcript phrasing on round `0` (for example, "the recommendation remains the same") instead of exposing that raw wording to the operator UI.
- Added a focused regression test in `tests/test_operator_followup_dialogue.py` for stale comparison language on the first recommendation.
- Live validation confirmed the fix on `INC-2026-0013`: the first operator-facing message now starts with the actual finding and recommendation instead of implying there was a previous recommendation.
