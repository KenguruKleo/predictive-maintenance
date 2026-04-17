# T-028 · MCP Servers (mcp-sentinel-db, mcp-qms, mcp-cmms)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🔴 CRITICAL  
**Статус:** ✅ DONE  
**Блокує:** T-025, T-026, T-027  
**Залежить від:** T-020 (Cosmos DB), T-021 (mock data)

---

## Мета

Реалізувати 3 MCP servers (stdio transport) для надання Foundry Agents доступу до структурованих даних і mock external systems.

---

## Структура

```
backend/
  mcp_sentinel_db/     # ← всередині Functions deployment package
    __init__.py
    server.py          # FastMCP app + 5 read tools (Cosmos DB)
    
  mcp_qms/             # ← всередині Functions deployment package
    __init__.py
    server.py          # FastMCP app + create_audit_entry tool
    
  mcp_cmms/            # ← всередині Functions deployment package
    __init__.py
    server.py          # FastMCP app + create_work_order tool
```

> MCP пакети знаходяться в `backend/` — вони потрапляють в Azure Functions deployment  
> та імпортуються напряму з `run_foundry_agents.py` без subprocess.  
> `mcp==1.6.0` вже є в `backend/requirements.txt`.

---

## mcp-sentinel-db — Tools

| Tool | Args | Returns |
|---|---|---|
| `get_equipment` | `equipment_id: str` | Full equipment document |
| `get_batch` | `batch_id: str` | Full batch document |
| `get_incident` | `incident_id: str` | Incident document |
| `search_incidents` | `equipment_id: str, limit: int = 5` | List of recent incidents for equipment |
| `get_template` | `template_type: str` | Template document |

## mcp-qms — Tools

| Tool | Args | Returns |
|---|---|---|
| `create_audit_entry` | `incident_id, equipment_id, deviation_type, description, root_cause, capa_actions, batch_disposition, prepared_by` | `{ audit_entry_id, qms_url, created_at }` |

## mcp-cmms — Tools

| Tool | Args | Returns |
|---|---|---|
| `create_work_order` | `equipment_id, title, description, priority, assigned_to, due_date, work_type` | `{ work_order_id, cmms_url, created_at }` |

---

## Implementation pattern (mcp-sentinel-db/server.py)

```python
from mcp.server.stdio import stdio_server
from mcp import Server
import asyncio

app = Server("mcp-sentinel-db")

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

## Використання в Activities (run_foundry_agents.py)

MCP пакети імпортуються напряму — без subprocess або HTTP:

```python
# backend/activities/run_foundry_agents.py
from mcp_sentinel_db.server import get_equipment, get_batch, search_incidents, get_template
from mcp_qms.server import create_audit_entry
from mcp_cmms.server import create_work_order
```

Функції реєструються як `FunctionTool` при створенні Foundry агента (T-024).  
Foundry повертає `requires_action` з `tool_calls`, наш код виконує виклики і повертає `tool_outputs`.

---

## Definition of Done

- [x] `mcp-sentinel-db`: всі 5 tools повертають коректні дані при тесті з seed'ованою Cosmos DB
- [x] `mcp-qms`: `create_audit_entry` повертає AE ID і записує в Cosmos DB `capa-plans`
- [x] `mcp-cmms`: `create_work_order` повертає WO ID і записує в Cosmos DB `capa-plans`
- [x] Foundry Agent може викликати MCP tools через stdio transport (test script: `scripts/test_mcp_servers.py` — 8/8 passed)
- [x] `requirements.txt` актуальний
