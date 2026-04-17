"""
mcp-qms — MCP stdio server

Simulates a Quality Management System (QMS) integration.

In production: Veeva Vault / SAP QM / MasterControl REST API.
In demo: writes GMP deviation audit entry records to Cosmos DB capa-plans container.

Run:
    python mcp-servers/mcp_qms/server.py

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
    "mcp-qms",
    host=os.getenv("FASTMCP_HOST", "127.0.0.1"),
    port=int(os.getenv("FASTMCP_PORT", "8000")),
    stateless_http=os.getenv("FASTMCP_STATELESS_HTTP", "false").lower() == "true",
)


@mcp.tool()
def create_audit_entry(
    incident_id: str,
    equipment_id: str,
    deviation_type: str,
    description: str,
    root_cause: str,
    capa_actions: str,
    batch_disposition: str,
    prepared_by: str,
) -> dict[str, Any]:
    """
    Create a GMP-compliant deviation audit entry in the Quality Management System.

    Records the deviation investigation, root cause, corrective and preventive actions (CAPA),
    and batch disposition decision. All fields are required for GMP compliance.

    Args:
        incident_id:       Source incident ID (e.g. INC-2026-0001)
        equipment_id:      Equipment where deviation occurred (e.g. GR-204)
        deviation_type:    Classification: process_parameter_excursion | equipment_malfunction | ...
        description:       Factual description of the deviation event
        root_cause:        Root cause investigation summary
        capa_actions:      Numbered CAPA actions (immediate + short-term + long-term)
        batch_disposition: conditional_release_pending_testing | rejected | release
        prepared_by:       User ID of QA person preparing the entry

    Returns:
        audit_entry_id: Generated AE ID (e.g. AE-2026-A4F2C1)
        qms_url:        URL to view entry in QMS
        created_at:     ISO 8601 timestamp

    In production: calls Veeva Vault / SAP QM API.
    In demo: stores record in Cosmos DB capa-plans container (type=audit_entry).
    """
    ae_id = f"AE-{datetime.now().strftime('%Y')}-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    doc = {
        "id": ae_id,
        "incidentId": incident_id,   # Cosmos partition key (/incidentId)
        "incident_id": incident_id,
        "equipment_id": equipment_id,
        "type": "audit_entry",
        "deviation_type": deviation_type,
        "description": description,
        "root_cause": root_cause,
        "capa_actions": capa_actions,
        "batch_disposition": batch_disposition,
        "prepared_by": prepared_by,
        "status": "draft",
        "regulatory_framework": "EU GMP Annex 15; GMP Annex — Qualification and Validation",
        "source_system": "sentinel-intelligence",
        "created_at": now,
        "updated_at": now,
    }

    _get_container("capa-plans").upsert_item(body=doc)

    return {
        "audit_entry_id": ae_id,
        "qms_url": f"https://qms.sentinelpharma.local/deviations/{ae_id}",
        "created_at": now,
    }


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)  # type: ignore[arg-type]
