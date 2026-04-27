# T-028 · MCP Servers (mcp-sentinel-db, mcp-qms, mcp-cmms)

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🔴 CRITICAL
**Status:** ✅ DONE
**Blocks:** T-025, T-026, T-027
**Depends on:** T-020 (Cosmos DB), T-021 (mock data)

---

## Goal

Implement 3 MCP servers (stdio transport) to provide Foundry Agents with access to structured data and mock external systems.

---

## Structure

```
backend/
mcp_sentinel_db/ # ← inside Functions deployment package
    __init__.py
    server.py          # FastMCP app + 5 read tools (Cosmos DB)
    
mcp_qms/ # ← inside Functions deployment package
    __init__.py
    server.py          # FastMCP app + create_audit_entry tool
    
mcp_cmms/ # ← inside the Functions deployment package
    __init__.py
    server.py          # FastMCP app + create_work_order tool
```

> MCP packages are in `backend/` — they go into Azure Functions deployment
> and imported directly from `run_foundry_agents.py` without subprocess.
> `mcp==1.6.0` is already in `backend/requirements.txt`.

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

## Usage in Activities (run_foundry_agents.py)

MCP packages are imported directly — without subprocess or HTTP:

```python
# backend/activities/run_foundry_agents.py
from mcp_sentinel_db.server import get_equipment, get_batch, search_incidents, get_template
from mcp_qms.server import create_audit_entry
from mcp_cmms.server import create_work_order
```

Functions are registered as `FunctionTool` when creating a Foundry agent (T-024).
Foundry returns `requires_action` from `tool_calls`, our code makes the calls and returns `tool_outputs`.

---

## Definition of Done

- [x] `mcp-sentinel-db`: all 5 tools return correct data when tested with seeded Cosmos DB
- [x] `mcp-qms`: `create_audit_entry` returns AE ID and writes to Cosmos DB `capa-plans`
- [x] `mcp-cmms`: `create_work_order` returns WO ID and writes to Cosmos DB `capa-plans`
- [x] Foundry Agent can call MCP tools via stdio transport (test script: `scripts/test_mcp_servers.py` — 8/8 passed)
- [x] `requirements.txt` is current
