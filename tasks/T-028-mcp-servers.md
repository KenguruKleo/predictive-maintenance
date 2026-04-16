# T-028 · MCP Servers (mcp-cosmos-db, mcp-qms-mock, mcp-cmms-mock)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🔴 CRITICAL  
**Статус:** 🔜 TODO  
**Блокує:** T-025, T-026, T-027  
**Залежить від:** T-020 (Cosmos DB), T-021 (mock data)

---

## Мета

Реалізувати 3 MCP servers (stdio transport) для надання Foundry Agents доступу до структурованих даних і mock external systems.

---

## Структура

```
mcp-servers/
  mcp_cosmos_db/
    __init__.py
    server.py          # MCP stdio server
    tools.py           # Tool implementations (reads from Cosmos DB)
    
  mcp_qms_mock/
    __init__.py
    server.py          # MCP stdio server
    tools.py           # create_audit_entry tool
    
  mcp_cmms_mock/
    __init__.py
    server.py          # MCP stdio server
    tools.py           # create_work_order tool

  requirements.txt     # mcp, azure-cosmos, python-dotenv
```

---

## mcp-cosmos-db — Tools

| Tool | Args | Returns |
|---|---|---|
| `get_equipment` | `equipment_id: str` | Full equipment document |
| `get_batch` | `batch_id: str` | Full batch document |
| `get_incident` | `incident_id: str` | Incident document |
| `search_incidents` | `equipment_id: str, limit: int = 5` | List of recent incidents for equipment |
| `get_template` | `template_type: str` | Template document |

## mcp-qms-mock — Tools

| Tool | Args | Returns |
|---|---|---|
| `create_audit_entry` | `incident_id, equipment_id, deviation_type, description, root_cause, capa_actions, batch_disposition, prepared_by` | `{ audit_entry_id, qms_url, created_at }` |

## mcp-cmms-mock — Tools

| Tool | Args | Returns |
|---|---|---|
| `create_work_order` | `equipment_id, title, description, priority, assigned_to, due_date, work_type` | `{ work_order_id, cmms_url, created_at }` |

---

## Implementation pattern (mcp-cosmos-db/server.py)

```python
from mcp.server.stdio import stdio_server
from mcp import Server
import asyncio

app = Server("mcp-cosmos-db")

@app.tool()
async def get_equipment(equipment_id: str) -> dict:
    """Get equipment master data from Cosmos DB by equipment_id."""
    container = get_container("equipment")
    item = container.read_item(item=equipment_id, partition_key=equipment_id)
    return item

@app.tool()
async def search_incidents(equipment_id: str, limit: int = 5) -> list:
    """Find recent incidents for a given equipment_id."""
    container = get_container("incidents")
    query = "SELECT TOP @limit * FROM c WHERE c.equipment_id = @eq_id ORDER BY c.created_at DESC"
    items = list(container.query_items(
        query=query,
        parameters=[{"name": "@eq_id", "value": equipment_id}, {"name": "@limit", "value": limit}],
        partition_key=equipment_id
    ))
    return items

async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Agent registration (how agents use MCP servers)

```python
# In Foundry Agent creation script:
from azure.ai.projects.models import McpTool

research_agent = project_client.agents.create_agent(
    model="gpt-4o",
    name="research-agent",
    instructions="...",
    tools=[
        McpTool(server_label="cosmos-db", server_params={"command": "python", "args": ["mcp-servers/mcp_cosmos_db/server.py"]}),
        # + AI Search tools
    ]
)
```

---

## Definition of Done

- [ ] `mcp-cosmos-db`: всі 5 tools повертають коректні дані при тесті з seed'ованою Cosmos DB
- [ ] `mcp-qms-mock`: `create_audit_entry` повертає WO ID і записує в Cosmos DB `incident_events`
- [ ] `mcp-cmms-mock`: `create_work_order` повертає WO ID і записує в Cosmos DB `incident_events`
- [ ] Foundry Agent може викликати MCP tools через stdio transport (test script)
- [ ] `requirements.txt` актуальний
