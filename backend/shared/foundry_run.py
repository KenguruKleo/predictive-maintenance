"""
Foundry Agent run helper with MCP tool auto-approval.

The Foundry Agent API (2025-05-15-preview) does not persist ``tool_resources.mcp``,
so MCP tools always default to ``require_approval="always"``.  The SDK's
``create_thread_and_process_run`` only handles ``SubmitToolOutputsAction`` (function
tools), **not** ``submit_tool_approval`` for MCP tools.

This module provides ``create_thread_and_process_run_with_approval`` which replaces
the SDK convenience method and handles both function-tool outputs and MCP-tool
approval transparently.
"""

import logging
import time
from typing import Any, cast

from azure.ai.agents import AgentsClient
from azure.ai.agents import models as agents_models
from azure.ai.agents.models import (
    AgentThreadCreationOptions,
    RunStatus,
)

ToolApproval = getattr(agents_models, "ToolApproval", None)

logger = logging.getLogger(__name__)

# Terminal run statuses that end the polling loop
_TERMINAL = {
    RunStatus.COMPLETED,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
    RunStatus.EXPIRED,
}

_MAX_ITERATIONS = 90
_POLL_INTERVAL = 2.0  # seconds


class FoundryRunTimeoutError(RuntimeError):
    """Raised when a Foundry agent run exceeds the caller's wall-clock budget."""


def create_thread_and_process_run_with_approval(
    client: AgentsClient,
    *,
    agent_id: str,
    thread: AgentThreadCreationOptions,
    max_iterations: int = _MAX_ITERATIONS,
    poll_interval: float = _POLL_INTERVAL,
    max_wait_seconds: float | None = None,
):
    """Create a thread + run and poll to completion, auto-approving MCP tool calls.

    Returns the completed ``AgentRun`` object (same shape as the SDK's
    ``create_thread_and_process_run``).

    Raises ``RuntimeError`` on timeout or unexpected terminal state.
    """
    run = client.create_thread_and_run(agent_id=agent_id, thread=thread)
    thread_id = run.thread_id
    run_id = run.id
    logger.info("Foundry run started: run=%s thread=%s", run_id, thread_id)
    deadline = time.monotonic() + max_wait_seconds if max_wait_seconds else None

    # When a wall-clock deadline is set, drive the loop by it (not by iteration
    # count) so the full time budget is always used.  The max_iterations cap
    # still applies when no deadline is given (e.g. standalone / test calls).
    i = 0
    while True:
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _cancel_run_if_possible(client, thread_id, run_id)
                raise FoundryRunTimeoutError(
                    f"Foundry run {run_id} exceeded {max_wait_seconds:.0f}s without reaching a terminal status"
                )
            time.sleep(min(poll_interval, remaining))
        else:
            if i >= max_iterations:
                break
            time.sleep(poll_interval)
        i += 1

        run = client.runs.get(thread_id=thread_id, run_id=run_id)
        status = run.status

        # ── MCP tool approval ────────────────────────────────────────────
        if status == RunStatus.REQUIRES_ACTION or "REQUIRES_ACTION" in str(status):
            ra = run.required_action
            ra_type = getattr(ra, "type", "") if not isinstance(ra, dict) else ra.get("type", "")

            if "tool_approval" in str(ra_type):
                calls = _extract_tool_calls(ra, "submit_tool_approval")
                logger.info(
                    "Auto-approving %d MCP tool call(s): %s",
                    len(calls),
                    ", ".join(_describe(c) for c in calls),
                )
                approvals = [_build_tool_approval(c) for c in calls]
                submit_tool_outputs = cast(Any, client.runs.submit_tool_outputs)
                run = submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run_id,
                    tool_approvals=approvals,
                )
                continue

            # Function-tool outputs (shouldn't happen for orchestrator, but handle generically)
            if "tool_outputs" in str(ra_type):
                logger.warning(
                    "Run %s requires function tool outputs — not handled by auto-approval. "
                    "Ensure the agent only uses MCP or built-in tools.",
                    run_id,
                )
                raise RuntimeError(
                    f"Run {run_id} requires function tool outputs which cannot be "
                    f"auto-supplied. Check agent tool configuration."
                )

            logger.warning("Unknown requires_action type: %s", ra_type)
            continue

        # ── Still working ────────────────────────────────────────────────
        if status in (RunStatus.IN_PROGRESS, RunStatus.QUEUED):
            continue

        # ── Terminal states ──────────────────────────────────────────────
        if status in _TERMINAL or any(t.name in str(status) for t in _TERMINAL):
            logger.info("Foundry run %s reached terminal status: %s", run_id, status)
            return run

    _cancel_run_if_possible(client, thread_id, run_id)
    if max_wait_seconds:
        raise FoundryRunTimeoutError(
            f"Foundry run {run_id} exceeded {max_wait_seconds:.0f}s without reaching a terminal status"
        )

    raise RuntimeError(
        f"Foundry run {run_id} did not complete within {max_iterations} iterations"
    )


# ── Helpers ──────────────────────────────────────────────────────────────


def _extract_tool_calls(required_action, attr_name: str) -> list:
    if isinstance(required_action, dict):
        return required_action.get(attr_name, {}).get("tool_calls", [])
    sub = getattr(required_action, attr_name, None)
    return getattr(sub, "tool_calls", []) if sub else []


def _call_id(call) -> str:
    return call.get("id", "") if isinstance(call, dict) else getattr(call, "id", "")


def _describe(call) -> str:
    if isinstance(call, dict):
        return f"{call.get('server_label', '?')}/{call.get('name', '?')}"
    return f"{getattr(call, 'server_label', '?')}/{getattr(call, 'name', '?')}"


def _build_tool_approval(call) -> Any:
    payload = {"tool_call_id": _call_id(call), "approve": True}
    if ToolApproval is None:
        return payload
    return ToolApproval(**payload)


def _cancel_run_if_possible(client: AgentsClient, thread_id: str, run_id: str) -> None:
    cancel = getattr(client.runs, "cancel", None)
    if not callable(cancel):
        return
    try:
        cancel(thread_id=thread_id, run_id=run_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to cancel Foundry run %s after timeout: %s", run_id, exc)
