"""
mcp-sentinel-db — MCP stdio server

Exposes read-only access to Sentinel Intelligence Cosmos DB data:
equipment, batches, incidents, templates.

Run:
    python mcp-servers/mcp_sentinel_db/server.py

Used by: Research Agent (T-025), Execution Agent (T-027)
"""

import os
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


def _clean(doc: dict) -> dict:
    """Strip Cosmos internal system fields (_rid, _ts, _self, _etag, _attachments)."""
    return {k: v for k, v in doc.items() if not k.startswith("_")}


# ── FastMCP app ───────────────────────────────────────────────────────────

mcp = FastMCP("mcp-sentinel-db")


@mcp.tool()
def get_equipment(equipment_id: str) -> dict[str, Any]:
    """
    Get equipment master data from Sentinel DB by equipment_id.

    Returns the full equipment document including:
    - validated_parameters (PAR ranges for all process parameters)
    - calibration dates, PM schedule
    - associated SOPs, criticality rating, location

    Example: get_equipment("GR-204")
    """
    container = _get_container("equipment")
    doc = container.read_item(item=equipment_id, partition_key=equipment_id)
    return _clean(doc)


@mcp.tool()
def get_batch(batch_id: str) -> dict[str, Any]:
    """
    Get batch context from Sentinel DB by batch_id.

    Returns:
    - product name, batch number, BPR reference
    - current stage and step
    - current process parameters (measured values)
    - operator and supervisor IDs

    Example: get_batch("BATCH-2026-0416-GR204")
    """
    container = _get_container("batches")
    items = list(
        container.query_items(
            query="SELECT * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": batch_id}],
            enable_cross_partition_query=True,
        )
    )
    if not items:
        raise ValueError(f"Batch '{batch_id}' not found in Sentinel DB")
    return _clean(items[0])


@mcp.tool()
def get_incident(incident_id: str) -> dict[str, Any]:
    """
    Get incident document from Sentinel DB by incident_id.

    Returns the full incident including:
    - deviation details (parameter, measured value, limit, duration)
    - current AI analysis (risk_level, recommendation, confidence)
    - workflow state (step, assigned_to, escalation_deadline)

    Example: get_incident("INC-2026-0001")
    """
    container = _get_container("incidents")
    items = list(
        container.query_items(
            query="SELECT * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": incident_id}],
            enable_cross_partition_query=True,
        )
    )
    if not items:
        raise ValueError(f"Incident '{incident_id}' not found in Sentinel DB")
    return _clean(items[0])


@mcp.tool()
def search_incidents(equipment_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """
    Find recent incidents for a given equipment_id.

    Returns up to `limit` incidents sorted newest first.
    Use this to find historical cases and patterns for the same equipment.

    Example: search_incidents("GR-204", limit=3)
    """
    container = _get_container("incidents")
    items = list(
        container.query_items(
            query="SELECT * FROM c WHERE c.equipmentId = @eq_id",
            parameters=[{"name": "@eq_id", "value": equipment_id}],
            partition_key=equipment_id,
        )
    )
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return [_clean(i) for i in items[:limit]]


@mcp.tool()
def get_template(template_type: str) -> dict[str, Any]:
    """
    Get a document template by type.

    Valid types:
    - 'work_order'   — corrective maintenance work order template
    - 'audit_entry'  — GMP deviation audit entry template

    Returns template fields used to pre-fill work orders and audit entries.

    Example: get_template("work_order")
    """
    container = _get_container("templates")
    items = list(
        container.query_items(
            query="SELECT * FROM c WHERE c.type = @type",
            parameters=[{"name": "@type", "value": template_type}],
            enable_cross_partition_query=True,
        )
    )
    if not items:
        raise ValueError(
            f"Template type '{template_type}' not found. Valid types: work_order, audit_entry"
        )
    return _clean(items[0])


if __name__ == "__main__":
    mcp.run()
