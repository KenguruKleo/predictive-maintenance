"""
mcp-sentinel-search — MCP stdio server

Exposes RAG semantic + vector search across all 5 Azure AI Search indexes:
  - idx-sop-documents      Standard Operating Procedures
  - idx-equipment-manuals  Equipment technical manuals
  - idx-bpr-documents      Batch Production Records / product process specs
  - idx-gmp-policies       GMP regulations and policies
  - idx-incident-history   Historical deviation incidents

Search strategy: hybrid (vector + keyword).
Embedding model: text-embedding-3-small (same as used during indexing).

Run:
    python backend/mcp_sentinel_search/server.py

Used by: Research Agent (T-025) — when deployed as HTTP SSE server.
For in-process use: import shared.search_utils directly.
"""

import sys
import os

# Allow running from either backend/ or project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from shared.search_utils import (
    search_index,
    IDX_SOP, IDX_MANUALS, IDX_BPR, IDX_GMP, IDX_INCIDENTS,
)

load_dotenv()

mcp = FastMCP(
    "mcp-sentinel-search",
    host=os.getenv("FASTMCP_HOST", "127.0.0.1"),
    port=int(os.getenv("FASTMCP_PORT", "8000")),
    stateless_http=os.getenv("FASTMCP_STATELESS_HTTP", "false").lower() == "true",
)


@mcp.tool()
def search_sop_documents(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """
    Semantic + vector search in Standard Operating Procedures (SOPs).

    Use this to find relevant SOP sections that apply to a GMP deviation.
    Returns text chunks with document title, section index, and relevance score.

    Examples:
        search_sop_documents("spray coating rate deviation investigation procedure")
        search_sop_documents("granulation endpoint determination out of spec")
    """
    return search_index(IDX_SOP, query, top_k)


@mcp.tool()
def search_equipment_manuals(
    query: str,
    equipment_id: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Semantic + vector search in equipment technical manuals.

    Use this to find maintenance procedures, alarm codes, component specs,
    and troubleshooting guides for specific equipment failures.

    Args:
        query:        Natural language description of the issue or question.
        equipment_id: Optional — filter by equipment ID (e.g. "GR-204").
        top_k:        Number of results to return (default 5).
    """
    filter_expr = f"equipment_ids/any(e: e eq '{equipment_id}')" if equipment_id else None
    return search_index(IDX_MANUALS, query, top_k, filter_expr)


@mcp.tool()
def search_bpr_documents(
    query: str,
    equipment_id: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Semantic + vector search in Batch Production Records (BPR) and product process specs.

    BPR ranges (NOR/PAR) are product-specific and NARROWER than equipment-level PAR.
    Always check BPR first for the exact product being manufactured.

    Args:
        query:        Natural language query about process parameters or product specs.
        equipment_id: Optional — filter by associated equipment ID.
        top_k:        Number of results to return (default 5).
    """
    filter_expr = f"equipment_ids/any(e: e eq '{equipment_id}')" if equipment_id else None
    return search_index(IDX_BPR, query, top_k, filter_expr)


@mcp.tool()
def search_gmp_policies(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """
    Semantic + vector search in GMP regulations and internal quality policies.

    Use this to cite applicable regulatory requirements (EU GMP Annex,
    ICH guidelines, FDA 21 CFR) and internal quality policies for a deviation.

    Examples:
        search_gmp_policies("deviation classification critical major minor criteria")
        search_gmp_policies("CAPA effectiveness check timeline requirements")
    """
    return search_index(IDX_GMP, query, top_k)


@mcp.tool()
def search_incident_history(
    query: str,
    equipment_id: str | None = None,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """
    Semantic + vector search in historical GMP deviation incidents.

    The index contains ALL closed incidents — both approved (real deviations)
    AND rejected (false positives / transient events dismissed by operators).
    Each result text includes a clear "HUMAN DECISION:" label:
      - "HUMAN DECISION: APPROVED" — the operator confirmed this was a real deviation
        (incident status = closed, approved by operator).
      - "HUMAN DECISION: REJECTED" — the operator dismissed this as a false positive
        (incident status = rejected, dismissed without corrective action).

    IMPORTANT for reasoning: Use the human decision to calibrate your recommendation.
    If similar past events were consistently REJECTED, treat the current event with
    lower alarm — it may be another false positive. If similar past events were
    consistently APPROVED, treat the current event seriously.

    Also check "Operator agreed with agent" to understand whether the AI was correct.

    Args:
        query:        Natural language description of the current deviation.
        equipment_id: Optional — filter to same equipment history only.
        top_k:        Number of results to return (default 8).
    """
    filter_expr = f"equipment_ids/any(e: e eq '{equipment_id}')" if equipment_id else None
    return search_index(IDX_INCIDENTS, query, top_k, filter_expr)


if __name__ == "__main__":
    import uvicorn
    from starlette.applications import Starlette
    from starlette.middleware.cors import CORSMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    # ── REST API routes (used by OpenApiTool in Foundry) ──────────────────
    async def rest_search_sop(request: Request) -> JSONResponse:
        q = request.query_params.get("query", "")
        top_k = int(request.query_params.get("top_k", "5"))
        return JSONResponse(search_sop_documents(q, top_k))

    async def rest_search_manuals(request: Request) -> JSONResponse:
        q = request.query_params.get("query", "")
        eq = request.query_params.get("equipment_id")
        top_k = int(request.query_params.get("top_k", "5"))
        return JSONResponse(search_equipment_manuals(q, eq, top_k))

    async def rest_search_bpr(request: Request) -> JSONResponse:
        q = request.query_params.get("query", "")
        eq = request.query_params.get("equipment_id")
        top_k = int(request.query_params.get("top_k", "5"))
        return JSONResponse(search_bpr_documents(q, eq, top_k))

    async def rest_search_gmp(request: Request) -> JSONResponse:
        q = request.query_params.get("query", "")
        top_k = int(request.query_params.get("top_k", "5"))
        return JSONResponse(search_gmp_policies(q, top_k))

    async def rest_search_incidents(request: Request) -> JSONResponse:
        q = request.query_params.get("query", "")
        eq = request.query_params.get("equipment_id")
        top_k = int(request.query_params.get("top_k", "5"))
        return JSONResponse(search_incident_history(q, eq, top_k))

    rest_routes = [
        Route("/api/search/sop", rest_search_sop),
        Route("/api/search/manuals", rest_search_manuals),
        Route("/api/search/bpr", rest_search_bpr),
        Route("/api/search/gmp", rest_search_gmp),
        Route("/api/search/incidents", rest_search_incidents),
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
