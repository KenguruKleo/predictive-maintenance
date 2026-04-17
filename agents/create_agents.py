"""
create_agents.py — Provision Foundry agents for Sentinel Intelligence (T-025, T-026, T-024)

Run once (or with --update) to create/update Research, Document, and Orchestrator agents
in Azure AI Foundry Agent Service.

Usage:
    cd /workspace/predictive-maintenance
    AZURE_AI_FOUNDRY_AGENTS_ENDPOINT='swedencentral.api.azureml.ms;d16bb0b5-b7b2-4c3b-805b-f7ccb9ce3550;ODL-GHAZ-2177134;aip-sentinel-intel-dev-erzrpo' \
    AZURE_AI_SEARCH_CONNECTION_ID=<connection_id_from_hub> \
    python agents/create_agents.py [--update]

The AZURE_AI_FOUNDRY_AGENTS_ENDPOINT is the semicolon-delimited connection string for the
Azure AI Foundry Hub-based project (format: host;subscriptionId;resourceGroup;projectName).
This is equal to the Bicep output 'foundryProjectConnectionString'.

After running, copy the printed IDs into local.settings.json / Azure App Settings:
    ORCHESTRATOR_AGENT_ID=...
    RESEARCH_AGENT_ID=...
    DOCUMENT_AGENT_ID=...
"""

import argparse
import os
import sys
from pathlib import Path

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    AISearchIndexResource,
    AzureAISearchQueryType,
    AzureAISearchTool,
    AzureAISearchToolResource,
    ConnectedAgentTool,
    McpTool,
    ToolDefinition,
    ToolResources,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

# ── Prompt files (created during T-025 / T-026) ───────────────────────────
PROMPTS_DIR = Path(__file__).parent / "prompts"
RESEARCH_PROMPT = (PROMPTS_DIR / "research_system.md").read_text(encoding="utf-8")
DOCUMENT_PROMPT = (PROMPTS_DIR / "document_system.md").read_text(encoding="utf-8")
ORCHESTRATOR_PROMPT = (PROMPTS_DIR / "orchestrator_system.md").read_text(encoding="utf-8")

MODEL = "gpt-4o"

# Azure AI Foundry Agent Service supports max 1 index per agent (current beta limit).
# We attach the primary GMP index; override via AZURE_AI_SEARCH_INDEX_NAME.
# Additional indexes (equipment manuals, BPR, etc.) can be added when the limit is lifted,
# or by creating specialised sub-agents per domain.
PRIMARY_SEARCH_INDEX = os.environ.get("AZURE_AI_SEARCH_INDEX_NAME", "idx-sop-documents")


def _build_client() -> AgentsClient:
    endpoint = os.environ.get("AZURE_AI_FOUNDRY_AGENTS_ENDPOINT", "").strip()
    if not endpoint:
        # Fall back to connection string format
        endpoint = os.environ.get("AZURE_AI_FOUNDRY_PROJECT_CONNECTION_STRING", "").strip()
    if not endpoint:
        print("ERROR: AZURE_AI_FOUNDRY_AGENTS_ENDPOINT is not set.", file=sys.stderr)
        print(
            "  Set it to the project connection string (semicolon-delimited):\n"
            "  swedencentral.api.azureml.ms;{sub};{rg};{project-name}",
            file=sys.stderr,
        )
        sys.exit(1)

    # AgentsClient supports Hub-based ML projects via legacy connection string format.
    # Setting AZURE_AI_AGENTS_TESTS_IS_TEST_RUN activates the legacy endpoint path
    # (per azure-ai-agents SDK code comments, the proper 1DP support is in progress).
    os.environ.setdefault("AZURE_AI_AGENTS_TESTS_IS_TEST_RUN", "True")
    return AgentsClient(endpoint=endpoint, credential=DefaultAzureCredential())


def _find_existing(client: AgentsClient, name: str):
    for agent in client.list_agents():
        if agent.name == name:
            return agent
    return None


def _create_or_update(
    client: AgentsClient,
    name: str,
    model: str,
    instructions: str,
    tools: list[ToolDefinition],
    tool_resources: ToolResources | None,
    update: bool,
):
    existing = _find_existing(client, name)
    if existing and not update:
        print(f"  '{name}' already exists (id={existing.id}) — use --update to overwrite")
        return existing

    kwargs: dict = dict(model=model, name=name, instructions=instructions, tools=tools)
    if tool_resources is not None:
        kwargs["tool_resources"] = tool_resources

    if existing and update:
        agent = client.update_agent(agent_id=existing.id, **kwargs)
        print(f"  Updated '{name}' (id={agent.id})")
    else:
        agent = client.create_agent(**kwargs)
        print(f"  Created '{name}' (id={agent.id})")
    return agent


def main(update: bool = False) -> dict:
    search_connection_id = os.environ.get("AZURE_AI_SEARCH_CONNECTION_ID", "").strip()

    # MCP server URLs (output by infra/main.bicep or backend/scripts/deploy-mcp.sh)
    mcp_db_url = os.environ.get("MCP_SENTINEL_DB_URL", "").strip()
    mcp_search_url = os.environ.get("MCP_SENTINEL_SEARCH_URL", "").strip()
    mcp_qms_url = os.environ.get("MCP_QMS_URL", "").strip()
    mcp_cmms_url = os.environ.get("MCP_CMMS_URL", "").strip()

    if not any([mcp_db_url, mcp_search_url, mcp_qms_url, mcp_cmms_url]):
        print(
            "  INFO: No MCP_*_URL env vars set — MCP tools disabled.\n"
            "  Build and deploy MCP Container Apps first:\n"
            "    bash backend/scripts/deploy-mcp.sh --acr-build\n"
            "  Then set MCP_SENTINEL_DB_URL, MCP_SENTINEL_SEARCH_URL, "
            "MCP_QMS_URL, MCP_CMMS_URL."
        )

    client = _build_client()

    # ── 1. Research Agent (T-025) ─────────────────────────────────────────
    print("\n[1/3] Research Agent...")

    research_tools: list[ToolDefinition] = []
    research_tr: ToolResources | None = None

    if search_connection_id:
        # AzureAISearchTool.definitions  → [{'type': 'azure_ai_search'}] (enable the tool)
        # AzureAISearchToolResource      → single index config (API beta limit: max 1 index)
        search_tool = AzureAISearchTool(
            index_connection_id=search_connection_id,
            index_name=PRIMARY_SEARCH_INDEX,
        )
        research_tools = search_tool.definitions  # type: ignore[assignment]

        research_tr = ToolResources(
            azure_ai_search=AzureAISearchToolResource(
                index_list=[
                    AISearchIndexResource(
                        index_connection_id=search_connection_id,
                        index_name=PRIMARY_SEARCH_INDEX,
                        query_type=AzureAISearchQueryType.SEMANTIC,
                        top_k=5,
                    )
                ]
            )
        )
    else:
        print(
            "  WARNING: AZURE_AI_SEARCH_CONNECTION_ID not set — search tools disabled.\n"
            "  Get it with:\n"
            "    az ml connection list --workspace-name aih-sentinel-intel-dev-erzrpo "
            "--resource-group ODL-GHAZ-2177134 -o table"
        )

    # MCP tools: sentinel-db (equipment / batch / incident context)
    # and sentinel-search (5-index RAG: SOP, manuals, BPR, GMP, incidents)
    if mcp_db_url:
        db_mcp = McpTool(
            server_label="sentinel-db",
            server_url=mcp_db_url,
        )
        research_tools = research_tools + db_mcp.definitions  # type: ignore[operator]
        print(f"  + MCP sentinel-db: {mcp_db_url}")

    if mcp_search_url:
        search_mcp = McpTool(
            server_label="sentinel-search",
            server_url=mcp_search_url,
        )
        research_tools = research_tools + search_mcp.definitions  # type: ignore[operator]
        print(f"  + MCP sentinel-search: {mcp_search_url}")

    research_agent = _create_or_update(
        client, "sentinel-research-agent", MODEL, RESEARCH_PROMPT,
        research_tools, research_tr, update,
    )

    # ── 2. Document Agent (T-026) ─────────────────────────────────────────
    print("\n[2/3] Document Agent...")

    document_tools: list[ToolDefinition] = []

    # MCP tools: qms (create audit entries) and cmms (create work orders)
    if mcp_qms_url:
        qms_mcp = McpTool(
            server_label="sentinel-qms",
            server_url=mcp_qms_url,
        )
        document_tools = document_tools + qms_mcp.definitions  # type: ignore[operator]
        print(f"  + MCP sentinel-qms: {mcp_qms_url}")

    if mcp_cmms_url:
        cmms_mcp = McpTool(
            server_label="sentinel-cmms",
            server_url=mcp_cmms_url,
        )
        document_tools = document_tools + cmms_mcp.definitions  # type: ignore[operator]
        print(f"  + MCP sentinel-cmms: {mcp_cmms_url}")

    document_agent = _create_or_update(
        client, "sentinel-document-agent", MODEL, DOCUMENT_PROMPT,
        document_tools, None, update,
    )

    # ── 3. Orchestrator Agent (T-024, ADR-002) ────────────────────────────
    print("\n[3/3] Orchestrator Agent...")
    research_connected = ConnectedAgentTool(
        id=research_agent.id,
        name="research_agent",
        description=(
            "Gathers equipment context, batch records, SOPs, GMP regulations, "
            "and historical incidents relevant to the deviation."
        ),
    )
    document_connected = ConnectedAgentTool(
        id=document_agent.id,
        name="document_agent",
        description=(
            "Produces structured GMP deviation analysis: classification, risk level, "
            "root cause hypothesis, CAPA recommendation, and confidence score."
        ),
    )

    orchestrator_agent = _create_or_update(
        client, "sentinel-orchestrator-agent", MODEL, ORCHESTRATOR_PROMPT,
        research_connected.definitions + document_connected.definitions,  # type: ignore[operator]
        None,
        update,
    )

    print("\n" + "=" * 60)
    print("Agents provisioned. Add to local.settings.json / Azure App Settings:\n")
    print(f"  RESEARCH_AGENT_ID={research_agent.id}")
    print(f"  DOCUMENT_AGENT_ID={document_agent.id}")
    print(f"  ORCHESTRATOR_AGENT_ID={orchestrator_agent.id}")
    print("=" * 60)

    return {
        "research_agent_id": research_agent.id,
        "document_agent_id": document_agent.id,
        "orchestrator_agent_id": orchestrator_agent.id,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provision Sentinel Foundry agents")
    parser.add_argument("--update", action="store_true", help="Update existing agents")
    args = parser.parse_args()
    main(update=args.update)
