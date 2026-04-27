# T-025 · Research Agent (Azure AI Foundry Connected Agents — sub-agent)

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🔴 CRITICAL
**Status:** ✅ DONE (April 18-19, 2026)
**Blocks:** T-024 (run_foundry_agents activity)
**Depends on:** T-024 (Orchestrator Agent), T-028 (MCP servers), T-037 (AI Search indexes)

> **ADR-002:** Research Agent is a **sub-agent** in the Foundry Connected Agents pattern.
> It is not called directly from Durable Functions - the Foundry Orchestrator Agent hooks it as `AgentTool`.
> See [02-architecture §8.10b](../02-architecture.md#810b-adr-002-foundry-connected-agents-vs-manual-orchestration).

---

## Goal

Implement Research Agent on Azure AI Foundry Agent Service as **sub-agent** Orchestrator Agent (Connected Agents pattern).
The agent gathers the full context for the incident: equipment history, similar past cases, relevant SOPs/manuals, GMP policies.
The Orchestrator Agent calls the Research Agent through `AgentTool`, receives the structured JSON output and passes it to the Document Agent.

---

## Files

```
agents/
  create_agents.py         # Script: create/update all agents in Foundry (Research + Document + Orchestrator + Execution)
research_agent.py # Sub-agent definition: tools + system prompt (without standalone run logic)
  document_agent.py        # (T-026)
orchestrator_agent.py # (T-024) Orchestrator Agent with connected sub-agents as AgentTool
  execution_agent.py       # (T-027)
  prompts/
research_system.md # System prompt for Research Agent
```

**Important:** `research_agent.py` contains only agent definitions (tools, instructions, model).
Call state (`run_research_agent()`) missing - The Foundry Orchestrator Agent manages the launch natively via `AgentTool`.

---

## Tools that Research Agent has

| Tool | Type in Foundry | Source | Purpose |
|---|---|---|---|
| `get_equipment` | MCP ServerTool | MCP `mcp-sentinel-db` | Equipment master data + equipment-level validated params (PAR) |
| `get_batch` | MCP ServerTool | MCP `mcp-sentinel-db` | Current batch context |
| `search_incidents` | MCP ServerTool | MCP `mcp-sentinel-db` | Historical incidents for this equipment |
| `search_sop_documents` | `AzureAISearchTool` | AI Search `idx-sop-documents` | RAG: relevant SOPs by semantic similarity |
| `search_equipment_manuals` | `AzureAISearchTool` | AI Search `idx-equipment-manuals` | RAG: equipment manual sections |
| `search_gmp_policies` | `AzureAISearchTool` | AI Search `idx-gmp-policies` | RAG: GMP regulations cited |
| **`search_bpr_documents`** | **`AzureAISearchTool`** | **AI Search `idx-bpr-documents`** | **RAG: product-specific CPP NOR/PAR — narrower than equipment PAR** |
| `search_incident_history` | `AzureAISearchTool` | AI Search `idx-incident-history` | RAG: similar historical cases (semantic) |

> **Foundry native tools:** AI Search tool calls use `AzureAISearchTool` from SDK `azure-ai-projects`.
> MCP servers are connected via `McpTool` / `ToolSet` with endpoint MCP server (T-028).

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

## Register as AgentTool (in orchestrator_agent.py)

Research Agent **does not have a separate launch function**. The Orchestrator Agent registers it as `AgentTool`:

```python
# agents/orchestrator_agent.py is a fragment of create_agents.py
from azure.ai.projects.models import AgentTool

# 1. Research Agent is already created - we get the ID from env or Cosmos
research_agent_id = os.environ["RESEARCH_AGENT_ID"]

# 2. Connect to Orchestrator Agent as AgentTool
research_tool = AgentTool(agent_id=research_agent_id)

orchestrator = client.agents.create_agent(
    model="gpt-4o",
    name="sentinel-orchestrator",
    instructions="...",  # orchestrator_system.md
    tools=[research_tool, document_tool],  # + document_tool (T-026)
    tool_resources={},
)
```

When the Orchestrator Agent decides to call the Research Agent, it does so natively through the Foundry Connected Agents mechanism. Durable does not see this challenge.

---

## Definition of Done

- [ ] Azure AI Foundry Hub + Project provisioned via `infra/modules/ai-foundry.bicep` (add to `infra/main.bicep`)
- [ ] `agents/create_agents.py` creates Research Agent in Foundry with all tools (MCP + AzureAISearchTool)
- [ ] Research Agent registered as `AgentTool` in Orchestrator Agent (T-024)
- [ ] Orchestrator Agent can call Research Agent through Connected Agents mechanism
- [ ] MCP tools (`get_equipment`, `get_batch`, `search_incidents`) are called and return data (INC-2026-0001)
- [ ] RAG search (`AzureAISearchTool`) returns relevant SOP chunks (>0 results for GR-204)
- [ ] Research Agent output (structured JSON, 7 sections) is transferred to Orchestrator Attorney → Document Agent without Durable state
- [ ] System prompt saved in `agents/prompts/research_system.md`
- [ ] Source citations are present in the answer
