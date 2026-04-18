"""
mcp-cmms — MCP stdio server

Simulates a Computerized Maintenance Management System (CMMS) integration.

In production: IBM Maximo / SAP PM / UpKeep REST API.
In demo: writes corrective maintenance work order records to Cosmos DB capa-plans container.

Run:
    python mcp-servers/mcp_cmms/server.py

Used by: Execution Agent (T-027)
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

# ── Cosmos client ─────────────────────────────────────────────────────────

COSMOS_ENDPOINT = os.getenv(
    "COSMOS_ENDPOINT",
    "https://cosmos-sentinel-intel-dev-erzrpo.documents.azure.com:443/",
)
COSMOS_DB = os.getenv("COSMOS_DATABASE", "sentinel-intelligence")

_client: CosmosClient | None = None


def _get_client() -> CosmosClient:
    global _client
    if _client is None:
        key = os.getenv("COSMOS_KEY")
        _client = CosmosClient(
            COSMOS_ENDPOINT,
            credential=key if key else DefaultAzureCredential(),
        )
    return _client


def _get_container(name: str):
    return _get_client().get_database_client(COSMOS_DB).get_container_client(name)


# ── FastMCP app ───────────────────────────────────────────────────────────

mcp = FastMCP(
    "mcp-cmms",
    host=os.getenv("FASTMCP_HOST", "127.0.0.1"),
    port=int(os.getenv("FASTMCP_PORT", "8000")),
    stateless_http=os.getenv("FASTMCP_STATELESS_HTTP", "false").lower() == "true",
)


@mcp.tool()
def create_work_order(
    incident_id: str,
    equipment_id: str,
    title: str,
    description: str,
    priority: str,
    assigned_to: str,
    due_date: str,
    work_type: str,
) -> dict[str, Any]:
    """
    Create a corrective maintenance work order in the CMMS.

    Schedules equipment inspection or repair following a GMP deviation.
    The work order is associated with the source incident for full traceability.

    Args:
        incident_id:  Source incident ID for traceability (e.g. INC-2026-0001)
        equipment_id: Equipment to be serviced (e.g. GR-204)
        title:        Short work order title (max 120 chars)
        description:  Detailed description of required maintenance/inspection work
        priority:     urgent | high | medium | low
        assigned_to:  Technician username or team name (e.g. maintenance_tech)
        due_date:     Completion deadline in ISO 8601 format (e.g. 2026-04-25)
        work_type:    corrective | preventive | inspection

    Returns:
        work_order_id: Generated WO ID (e.g. WO-2026-B3E7A2)
        cmms_url:      URL to view work order in CMMS
        created_at:    ISO 8601 timestamp

    In production: calls IBM Maximo / SAP PM API.
    In demo: stores record in Cosmos DB capa-plans container (type=work_order).
    """
    wo_id = f"WO-{datetime.now().strftime('%Y')}-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    doc = {
        "id": wo_id,
        "incidentId": incident_id,   # Cosmos partition key (/incidentId)
        "incident_id": incident_id,
        "equipment_id": equipment_id,
        "type": "work_order",
        "title": title,
        "description": description,
        "priority": priority,
        "assigned_to": assigned_to,
        "due_date": due_date,
        "work_type": work_type,
        "status": "open",
        "source_system": "sentinel-intelligence",
        "created_at": now,
        "updated_at": now,
    }

    _get_container("capa-plans").upsert_item(body=doc)

    return {
        "work_order_id": wo_id,
        "cmms_url": f"https://cmms.sentinelpharma.local/work-orders/{wo_id}",
        "created_at": now,
    }


if __name__ == "__main__":
    import json
    import uvicorn
    from starlette.applications import Starlette
    from starlette.middleware.cors import CORSMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def rest_create_work_order(request: Request) -> JSONResponse:
        try:
            body = await request.json()
            result = create_work_order(**body)
            return JSONResponse(result, status_code=201)
        except Exception as e:
            return JSONResponse({"error": str(e), "success": False})

    rest_routes = [
        Route("/api/work-orders", rest_create_work_order, methods=["POST"]),
    ]

    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "streamable-http":
        mcp_app = mcp.streamable_http_app()

        async def health(request: Request) -> JSONResponse:
            return JSONResponse({"status": "ok"})

        all_routes = rest_routes + [
            Route("/health", health),
            Route("/mcp{path:path}", mcp_app),
        ]

        app = CORSMiddleware(
            Starlette(routes=all_routes),
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        uvicorn.run(
            app,
            host=os.getenv("FASTMCP_HOST", "127.0.0.1"),
            port=int(os.getenv("FASTMCP_PORT", "8000")),
        )
    else:
        mcp.run(transport=transport)  # type: ignore[arg-type]
