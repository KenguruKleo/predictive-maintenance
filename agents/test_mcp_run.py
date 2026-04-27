"""
test_mcp_run.py — Test Sentinel agents with MCP tool auto-approval.

The Foundry Agent API (2025-05-15-preview) does not persist tool_resources.mcp,
so MCP tools always default to require_approval="always". The Foundry Playground
has no approval handler, which causes `output: null`.

This script handles `submit_tool_approval` automatically: it approves every MCP
tool call so the Foundry runtime can execute it server-side.

Usage:
    python agents/test_mcp_run.py "Get equipment data for GR-204"
    python agents/test_mcp_run.py --agent document "Create audit entry for deviation on GR-204"
    python agents/test_mcp_run.py --agent orchestrator "Analyse deviation on GR-204, batch BATCH-2026-0416-GR204, impeller speed 950 RPM"
"""

import argparse
import os
import time

os.environ.setdefault("AZURE_AI_AGENTS_TESTS_IS_TEST_RUN", "True")

from azure.ai.agents import AgentsClient
from azure.ai.agents import models as agents_models
from azure.ai.agents.models import RunStatus
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

ToolApproval = getattr(agents_models, "ToolApproval", None)


def _build_client() -> AgentsClient:
    endpoint = os.environ.get("AZURE_AI_FOUNDRY_AGENTS_ENDPOINT", "").strip()
    if not endpoint:
        endpoint = (
            "swedencentral.api.azureml.ms;"
            "d16bb0b5-b7b2-4c3b-805b-f7ccb9ce3550;"
            "ODL-GHAZ-2177134;"
            "aip-sentinel-intel-dev-erzrpo"
        )
    return AgentsClient(endpoint=endpoint, credential=DefaultAzureCredential())


AGENT_IDS = {
    "research": os.environ.get("RESEARCH_AGENT_ID", "asst_NDuVHHTsxfRvY1mRSd7MtEGT"),
    "document": os.environ.get("DOCUMENT_AGENT_ID", "asst_AXgt7fxnSnUh5WXauR27S40L"),
    "orchestrator": os.environ.get("ORCHESTRATOR_AGENT_ID", "asst_CNYK3TZIaOCH4OPKcP4N9B2r"),
}


def _extract_tool_calls(required_action, attr_name: str) -> list:
    if isinstance(required_action, dict):
        return required_action.get(attr_name, {}).get("tool_calls", [])
    sub = getattr(required_action, attr_name, None)
    return getattr(sub, "tool_calls", []) if sub else []


def _call_id(call) -> str:
    return call.get("id", "") if isinstance(call, dict) else getattr(call, "id", "")


def _describe(call) -> str:
    if isinstance(call, dict):
        return f'{call.get("server_label", "?")}/{call.get("name", "?")}({call.get("arguments", "{}")})'
    return f'{getattr(call, "server_label", "?")}/{getattr(call, "name", "?")}({getattr(call, "arguments", "{}")})'


def _tool_approval_payload(call):
    payload = {"tool_call_id": _call_id(call), "approve": True}
    return ToolApproval(**payload) if ToolApproval is not None else payload


def run_with_auto_approval(
    client: AgentsClient,
    agent_id: str,
    user_message: str,
    *,
    tool_choice: str | None = None,
    max_iterations: int = 40,
    poll_interval: float = 2.0,
) -> str:
    """Create a thread+run and auto-approve MCP tool calls. Returns assistant text."""
    run_kwargs = {
        "agent_id": agent_id,
        "thread": {"messages": [{"role": "user", "content": user_message}]},
    }
    if tool_choice:
        run_kwargs["tool_choice"] = tool_choice
    run = client.create_thread_and_run(**run_kwargs)
    thread_id = run.thread_id
    run_id = run.id
    print(f"  Run {run_id}  Thread {thread_id}  status={run.status}")

    for i in range(max_iterations):
        time.sleep(poll_interval)
        run = client.runs.get(thread_id=thread_id, run_id=run_id)
        status = run.status

        if status == RunStatus.REQUIRES_ACTION or "REQUIRES_ACTION" in str(status):
            ra = run.required_action
            ra_type = getattr(ra, "type", "") if not isinstance(ra, dict) else ra.get("type", "")

            if "tool_approval" in str(ra_type):
                calls = _extract_tool_calls(ra, "submit_tool_approval")
                descs = [_describe(c) for c in calls]
                print(f"  [{i:2d}] requires_action — approving {len(calls)} tool(s): {', '.join(descs)}")
                approvals = [_tool_approval_payload(c) for c in calls]
                run = client.runs.submit_tool_outputs(
                    thread_id=thread_id, run_id=run_id, tool_approvals=approvals,
                )
                continue

            print(f"  [{i:2d}] requires_action type={ra_type} (unhandled)")
            continue

        if status in (RunStatus.IN_PROGRESS,) or "IN_PROGRESS" in str(status):
            print(f"  [{i:2d}] in_progress...")
            continue

        if status == RunStatus.QUEUED or "QUEUED" in str(status):
            continue

        if status == RunStatus.COMPLETED or "COMPLETED" in str(status):
            messages = client.messages.list(thread_id=thread_id)
            for m in messages:
                if m.role == "assistant":
                    for c in m.content:
                        if hasattr(c, "text"):
                            return c.text.value
            return "(no assistant response found)"

        if status == RunStatus.FAILED or "FAILED" in str(status):
            return f"FAILED: {run.last_error}"

        return f"Terminal status: {status}"

    return "Timed out waiting for completion"


def main():
    parser = argparse.ArgumentParser(description="Test Sentinel agent with MCP auto-approval")
    parser.add_argument("message", nargs="?", default="Get equipment data for GR-204")
    parser.add_argument("--agent", choices=list(AGENT_IDS.keys()), default="research")
    parser.add_argument("--tool-choice", choices=["auto", "required", "none"], default=None)
    args = parser.parse_args()

    agent_id = AGENT_IDS[args.agent]
    print(f"Agent: {args.agent} ({agent_id})")
    print(f"Prompt: {args.message}\n")

    client = _build_client()
    result = run_with_auto_approval(client, agent_id, args.message, tool_choice=args.tool_choice)
    print(f"\n{'='*60}")
    print(result)
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
