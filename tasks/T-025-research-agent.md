# T-025 · Research Agent (Azure AI Foundry Connected Agents — sub-agent)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🔴 CRITICAL  
**Статус:** ✅ DONE (18-19 квітня 2026)  
**Блокує:** T-024 (run_foundry_agents activity)  
**Залежить від:** T-024 (Orchestrator Agent), T-028 (MCP servers), T-037 (AI Search indexes)

> **ADR-002:** Research Agent є **sub-agent** в Foundry Connected Agents pattern.  
> Він не викликається безпосередньо з Durable Functions — Foundry Orchestrator Agent підключає його як `AgentTool`.  
> Дивись [02-architecture §8.10b](../02-architecture.md#810b-adr-002-foundry-connected-agents-vs-ручна-оркестрація).

---

## Мета

Реалізувати Research Agent на Azure AI Foundry Agent Service як **sub-agent** Orchestrator Agent (Connected Agents pattern).  
Агент збирає повний контекст для incident: equipment history, similar past cases, relevant SOPs/manuals, GMP policies.  
Orchestrator Agent викликає Research Agent через `AgentTool`, отримує structured JSON output і передає його до Document Agent.

---

## Файли

```
agents/
  create_agents.py         # Script: create/update all agents in Foundry (Research + Document + Orchestrator + Execution)
  research_agent.py        # Sub-agent definition: tools + system prompt (без standalone run logic)
  document_agent.py        # (T-026)
  orchestrator_agent.py    # (T-024) Orchestrator Agent з підключеними sub-agents як AgentTool
  execution_agent.py       # (T-027)
  prompts/
    research_system.md     # System prompt для Research Agent
```

**Важливо:** `research_agent.py` містить лише визначення агента (tools, instructions, model).  
Станова виклику (`run_research_agent()`) відсутня — Foundry Orchestrator Agent керує запуском нативно через `AgentTool`.

---

## Tools які має Research Agent

| Tool | Тип у Foundry | Source | Purpose |
|---|---|---|---|
| `get_equipment` | MCP ServerTool | MCP `mcp-sentinel-db` | Equipment master data + equipment-level validated params (PAR) |
| `get_batch` | MCP ServerTool | MCP `mcp-sentinel-db` | Current batch context |
| `search_incidents` | MCP ServerTool | MCP `mcp-sentinel-db` | Historical incidents for this equipment |
| `search_sop_documents` | `AzureAISearchTool` | AI Search `idx-sop-documents` | RAG: relevant SOPs by semantic similarity |
| `search_equipment_manuals` | `AzureAISearchTool` | AI Search `idx-equipment-manuals` | RAG: equipment manual sections |
| `search_gmp_policies` | `AzureAISearchTool` | AI Search `idx-gmp-policies` | RAG: GMP regulations cited |
| **`search_bpr_documents`** | **`AzureAISearchTool`** | **AI Search `idx-bpr-documents`** | **RAG: product-specific CPP NOR/PAR — narrower than equipment PAR** |
| `search_incident_history` | `AzureAISearchTool` | AI Search `idx-incident-history` | RAG: similar historical cases (semantic) |

> **Foundry native tools:** AI Search tool calls використовують `AzureAISearchTool` з SDK `azure-ai-projects`.  
> MCP servers підключаються через `McpTool` / `ToolSet` з endpoint MCP server (T-028).

---

## System Prompt (prompts/research_system.md)

```
You are the Research Agent in the Sentinel Intelligence GMP Deviation Management System.

Your role: gather comprehensive context for a GMP deviation incident before analysis begins.

Given an incident alert with equipment_id and deviation details, you MUST:

1. Retrieve equipment master data (validated parameters = equipment-level PAR, PM history, criticality)
2. Retrieve current batch context (product, stage, BPR reference)
3. **Retrieve BPR product process specification** (search idx-bpr-documents for product NOR/PAR — these ranges are NARROWER than equipment PAR and take precedence for this product)
4. Search for similar historical incidents on this equipment (last 12 months)
5. Find the most relevant SOPs (top 3 by relevance to deviation type)
6. Find relevant GMP policies and regulations
7. Find equipment manual sections related to the failing component

Return a structured JSON object:
```json
{
  "equipment": { ... equipment document ... },
  "batch": { ... batch document ... },
  "bpr_constraints": {
    "document_id": "BPR-MET-500-v3.2",
    "product_nor": { "impeller_speed_rpm": [600, 700], "spray_rate_g_min": [75, 105] },
    "product_par": { "impeller_speed_rpm": [580, 750] },
    "note": "Product NOR/PAR narrower than equipment validated range. Use these limits for deviation assessment, not equipment PAR."
  },
  "historical_incidents": [ ... top 5 similar past incidents ... ],
  "relevant_sops": [ { "id": "...", "title": "...", "relevant_section": "...", "text_excerpt": "..." } ],
  "gmp_references": [ { "regulation": "...", "section": "...", "text": "..." } ],
  "equipment_manual_notes": "...",
  "context_summary": "One paragraph summary of the full context for the Document Agent"
}

Always cite your sources. Never fabricate data. If a tool returns no results, say so explicitly.
```

---

## Реєстрація як AgentTool (у orchestrator_agent.py)

Research Agent **не має окремої функції запуску**. Orchestrator Agent реєструє його як `AgentTool`:

```python
# agents/orchestrator_agent.py — фрагмент create_agents.py
from azure.ai.projects.models import AgentTool

# 1. Research Agent вже створений — отримуємо ID з env або Cosmos
research_agent_id = os.environ["RESEARCH_AGENT_ID"]

# 2. Підключаємо до Orchestrator Agent як AgentTool
research_tool = AgentTool(agent_id=research_agent_id)

orchestrator = client.agents.create_agent(
    model="gpt-4o",
    name="sentinel-orchestrator",
    instructions="...",  # orchestrator_system.md
    tools=[research_tool, document_tool],  # + document_tool (T-026)
    tool_resources={},
)
```

Коли Orchestrator Agent вирішує зателефонувати до Research Agent — він робить це нативно через Foundry Connected Agents механізм. Durable не бачить цього виклику.

---

## Definition of Done

- [ ] Azure AI Foundry Hub + Project provisioned via `infra/modules/ai-foundry.bicep` (додати до `infra/main.bicep`)
- [ ] `agents/create_agents.py` створює Research Agent в Foundry з усіма tools (MCP + AzureAISearchTool)
- [ ] Research Agent зареєстрований як `AgentTool` в Orchestrator Agent (T-024)
- [ ] Orchestrator Agent може викликати Research Agent через Connected Agents механізм
- [ ] MCP tools (`get_equipment`, `get_batch`, `search_incidents`) викликаються і повертають дані (INC-2026-0001)
- [ ] RAG search (`AzureAISearchTool`) повертає релевантні SOP chunks (>0 результатів для GR-204)
- [ ] Research Agent output (structured JSON, 7 секцій) передається Orchestrator Attorney → Document Agent без Durable state
- [ ] System prompt збережений у `agents/prompts/research_system.md`
- [ ] Source citations присутні у відповіді
