# T-025 · Research Agent (Azure AI Foundry + MCP + RAG)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🔴 CRITICAL  
**Статус:** 🔜 TODO  
**Блокує:** T-024 (step 3 — run_agents activity)  
**Залежить від:** T-028 (MCP servers), T-037 (AI Search indexes)

---

## Мета

Реалізувати Research Agent на Azure AI Foundry Agent Service. Агент збирає повний контекст для incident: equipment history, similar past cases, relevant SOPs/manuals, GMP policies.

---

## Файли

```
agents/
  create_agents.py         # Script: create/update all 3 agents in Foundry
  research_agent.py        # Agent definition + instructions + run logic
  document_agent.py        # (T-026)
  execution_agent.py       # (T-027)
  prompts/
    research_system.md     # System prompt для Research Agent
```

---

## Tools які має Research Agent

| Tool | Source | Purpose |
|---|---|---|
| `get_equipment` | MCP mcp-cosmos-db | Equipment master data + validated params |
| `get_batch` | MCP mcp-cosmos-db | Current batch context |
| `search_incidents` | MCP mcp-cosmos-db | Historical incidents for this equipment |
| `search_sop_documents` | Azure AI Search | RAG: relevant SOPs by semantic similarity |
| `search_equipment_manuals` | Azure AI Search | RAG: equipment manual sections |
| `search_incident_history` | Azure AI Search | RAG: similar historical cases (semantic) |
| `search_gmp_policies` | Azure AI Search | RAG: GMP regulations cited |

---

## System Prompt (prompts/research_system.md)

```
You are the Research Agent in the Sentinel Intelligence GMP Deviation Management System.

Your role: gather comprehensive context for a GMP deviation incident before analysis begins.

Given an incident alert with equipment_id and deviation details, you MUST:

1. Retrieve equipment master data (validated parameters, PM history, criticality)
2. Retrieve current batch context (product, stage, BPR reference)
3. Search for similar historical incidents on this equipment (last 12 months)
4. Find the most relevant SOPs (top 3 by relevance to deviation type)
5. Find relevant GMP policies and regulations
6. Find equipment manual sections related to the failing component

Return a structured JSON object:
{
  "equipment": { ... equipment document ... },
  "batch": { ... batch document ... },
  "historical_incidents": [ ... top 5 similar past incidents ... ],
  "relevant_sops": [ { "id": "...", "title": "...", "relevant_section": "...", "text_excerpt": "..." } ],
  "gmp_references": [ { "regulation": "...", "section": "...", "text": "..." } ],
  "equipment_manual_notes": "...",
  "context_summary": "One paragraph summary of the full context for the Document Agent"
}

Always cite your sources. Never fabricate data. If a tool returns no results, say so explicitly.
```

---

## run_research_agent() function

```python
# research_agent.py
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

async def run_research_agent(incident_id: str, alert_payload: dict) -> dict:
    client = AIProjectClient.from_connection_string(
        os.environ["AZURE_AI_FOUNDRY_PROJECT_CONNECTION_STRING"],
        credential=DefaultAzureCredential()
    )
    
    agent = client.agents.get_agent(os.environ["RESEARCH_AGENT_ID"])
    thread = client.agents.create_thread()
    
    message = client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content=f"""
        Incident ID: {incident_id}
        Equipment ID: {alert_payload['equipment_id']}
        Batch ID: {alert_payload.get('batch_id')}
        Deviation type: {alert_payload['deviation_type']}
        Parameter: {alert_payload['parameter']}
        Measured value: {alert_payload['measured_value']} {alert_payload['unit']}
        Limit: {alert_payload['lower_limit']}–{alert_payload['upper_limit']} {alert_payload['unit']}
        Duration: {alert_payload['duration_seconds']} seconds
        
        Please gather all relevant context for this deviation.
        """
    )
    
    run = client.agents.create_and_process_run(
        thread_id=thread.id,
        agent_id=agent.id
    )
    
    # Extract last assistant message (structured JSON)
    messages = client.agents.list_messages(thread_id=thread.id)
    result_text = messages.data[0].content[0].text.value
    return json.loads(result_text)
```

---

## Definition of Done

- [ ] Azure AI Foundry Hub + Project provisioned via `infra/modules/ai-foundry.bicep` (додати до `infra/main.bicep`)
- [ ] `agents/create_agents.py` створює Research Agent в Foundry з усіма tools
- [ ] `run_research_agent()` повертає структурований JSON з усіма 7 секціями
- [ ] MCP tools викликаються і повертають дані (перевірено на INC-2026-0001)
- [ ] RAG search повертає релевантні SOP chunks (>0 результатів для GR-204 deviation)
- [ ] System prompt збережений у `agents/prompts/research_system.md`
- [ ] Confidence/source citations присутні у відповіді
