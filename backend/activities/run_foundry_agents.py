"""
Activity: run_foundry_agents — call Foundry Orchestrator Agent (T-024, ADR-002)

Orchestrator Agent manages the Research → Document pipeline natively via
Connected Agents (AgentTool). This activity creates a thread, sends the full
incident context as a user message, and waits for the agent to produce a
structured JSON analysis.

Returns:
    {
        "title": str,
        "analysis": str,
        "root_cause": str,
        "operator_dialogue": str,    # concise human-facing summary for chat transcript
        "recommendations": list[dict],
        "regulatory_refs": list[str],
        "sop_refs": list[str],
        "confidence": float,          # 0.0–1.0
        "risk_level": str,
        "classification": str,
        "batch_disposition": str,
        "evidence_citations": list,
        "work_order_draft": dict,
        "audit_entry_draft": dict,
        "raw_response": str,          # always present for audit trail
    }
"""

import json
import logging
import os
import random
import re
import time
from collections.abc import Sequence
from datetime import datetime, timezone
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

import azure.durable_functions as df
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    AgentThreadCreationOptions,
    MessageRole,
    RunStatus,
    ThreadMessageOptions,
)
from azure.identity import DefaultAzureCredential

from shared.agent_telemetry import log_trace_json, log_trace_text
from shared.cosmos_client import get_container, get_cosmos_client
from shared.foundry_run import (
    FoundryRunTimeoutError,
    create_thread_and_process_run_with_approval,
)
from shared.incident_store import get_incident_by_id, patch_incident_by_id
from shared.search_utils import search_index
from shared.signalr_client import notify_incident_status_changed_sync

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))
SEARCH_ENABLED = bool(os.getenv("AZURE_SEARCH_ENDPOINT", ""))
DB_NAME = os.getenv("COSMOS_DATABASE", "sentinel-intelligence")
try:
    FOUNDRY_ACTIVITY_TIMEOUT_SECS = max(
        360.0,
        float(os.getenv("FOUNDRY_ACTIVITY_TIMEOUT_SECS", "360")),
    )
except ValueError:
    FOUNDRY_ACTIVITY_TIMEOUT_SECS = 360.0

try:
    FOUNDRY_SLOT_WAIT_SECS = max(
        30.0,
        float(os.getenv("FOUNDRY_SLOT_WAIT_SECS", "180")),
    )
except ValueError:
    FOUNDRY_SLOT_WAIT_SECS = 180.0

try:
    FOUNDRY_STALE_LOCK_SECS = max(
        300.0,
        float(os.getenv("FOUNDRY_STALE_LOCK_SECS", "1800")),
    )
except ValueError:
    FOUNDRY_STALE_LOCK_SECS = 1800.0

try:
    FOUNDRY_LOCK_GRACE_SECS = max(
        10.0,
        float(os.getenv("FOUNDRY_LOCK_GRACE_SECS", "60")),
    )
except ValueError:
    FOUNDRY_LOCK_GRACE_SECS = 60.0

INDEX_EVIDENCE_META = {
    "idx-sop-documents": {"type": "sop", "container": "blob-sop"},
    "idx-equipment-manuals": {"type": "manual", "container": "blob-manuals"},
    "idx-bpr-documents": {"type": "bpr", "container": "blob-bpr"},
    "idx-gmp-policies": {"type": "gmp", "container": "blob-gmp"},
    "idx-incident-history": {"type": "historical", "container": "blob-history"},
}

# Reverse lookup: citation type → index name (derived from INDEX_EVIDENCE_META)
_TYPE_TO_INDEX: dict[str, str] = {meta["type"]: idx for idx, meta in INDEX_EVIDENCE_META.items()}

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_PROMPTS_DIR = REPO_ROOT / "agents" / "prompts"

DEFAULT_RESEARCH_AGENT_MODEL = "gpt-4o-mini"
DEFAULT_DOCUMENT_AGENT_MODEL = "gpt-4o-mini"
DEFAULT_ORCHESTRATOR_AGENT_MODEL = "gpt-4o"

bp = df.Blueprint()


@bp.activity_trigger(input_name="input_data")
def run_foundry_agents(input_data: dict) -> dict:
    incident_id: str = input_data["incident_id"]
    context_data: dict = input_data["context"]
    previous_ai_result: dict = input_data.get("previous_ai_result") or {}
    more_info_round: int = input_data.get("more_info_round", 0)

    logger.info(
        "run_foundry_agents: incident=%s round=%d", incident_id, more_info_round
    )

    # Mark as queued first — we may have to wait for the Foundry concurrency slot.
    # The transition to "analyzing" happens AFTER the slot is acquired so the UI
    # can distinguish "queued behind another incident" from "actively in Foundry".
    _mark_incident_queued_for_analysis(incident_id, more_info_round)
    _write_analysis_queued_event(incident_id, more_info_round)

    # HACKATHON: fallback to the provisioned agent ID so local runs work without a
    # full env-var setup. Remove the fallback before a production deployment.
    _FALLBACK_AGENT_ID = "asst_CNYK3TZIaOCH4OPKcP4N9B2r"
    orchestrator_agent_id = os.environ.get("ORCHESTRATOR_AGENT_ID", "").strip() or _FALLBACK_AGENT_ID
    if not orchestrator_agent_id:
        raise EnvironmentError(
            "ORCHESTRATOR_AGENT_ID env var is not set. "
            "Run agents/create_agents.py first to provision Foundry agents."
        )

    # Keep the activity prompt compact. The Research Agent is the single evidence
    # collector; citation normalization can still resolve explicit document IDs
    # via targeted lookup after the Orchestrator returns the final JSON.
    rag_context: dict = {}

    # Foundry concurrency gate: wait until a slot is free, then mark self as active.
    # Cleared in the finally block below so the next queued incident can proceed.
    _equipment_id = (
        context_data.get("equipment_id")
        or context_data.get("equipment", {}).get("id")
        or context_data.get("alert_payload", {}).get("equipment_id")
        or ""
    )
    _db = get_cosmos_client().get_database_client(DB_NAME)
    _incidents_container = _db.get_container_client("incidents")
    _wait_for_foundry_slot(
        incident_id, _equipment_id, time.monotonic() + FOUNDRY_SLOT_WAIT_SECS
    )

    # Slot acquired — flip status to "analyzing" so the UI knows we are now actively
    # in Foundry (vs. just queued).
    _mark_incident_analyzing(incident_id, more_info_round)

    # Write analysis_started event AFTER the slot is acquired so the status history
    # reflects when the incident actually entered Foundry, not when it was queued.
    _write_analysis_started_event(incident_id, more_info_round)

    prompt = _build_prompt(
        incident_id,
        context_data,
        more_info_round,
        previous_ai_result,
    )
    _log_orchestrator_prompt_trace(
        incident_id=incident_id,
        more_info_round=more_info_round,
        orchestrator_agent_id=orchestrator_agent_id,
        prompt=prompt,
        context_data=context_data,
    )
    try:
        result = _call_orchestrator_agent(
            prompt,
            orchestrator_agent_id,
            incident_id=incident_id,
            more_info_round=more_info_round,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Foundry analysis failed for incident %s round=%d: %s",
            incident_id,
            more_info_round,
            exc,
            exc_info=True,
        )
        result = _build_agent_failure_result(
            incident_id=incident_id,
            previous_ai_result=previous_ai_result,
            more_info_round=more_info_round,
            error=exc,
        )
    finally:
        # Always release the Foundry slot so the next waiting incident can proceed.
        _set_foundry_active(_incidents_container, incident_id, _equipment_id, False)

    result = _normalize_agent_result(
        result,
        rag_context,
        more_info_round,
        previous_ai_result=previous_ai_result,
        operator_questions=context_data.get("operator_questions", []),
    )

    # Confidence gate (RAI Gap #4): log warning but still return result
    confidence = result.get("confidence", 0.0)
    if confidence < CONFIDENCE_THRESHOLD:
        logger.warning(
            "Low confidence %.2f for incident %s (threshold=%.2f). "
            "Consider requesting more_info.",
            confidence,
            incident_id,
            CONFIDENCE_THRESHOLD,
        )
        result["confidence_flag"] = "LOW_CONFIDENCE"

    _log_trace_json(
        incident_id=incident_id,
        more_info_round=more_info_round,
        trace_kind="normalized_result",
        payload=result,
    )

    return result


# ── Internal helpers ──────────────────────────────────────────────────────


_RATE_LIMIT_MAX_RETRIES = 5
# Base backoff in seconds; actual wait = base + random jitter (0..base/2)
# This prevents thundering herd when multiple incidents retry simultaneously.
_RATE_LIMIT_BACKOFF_SECS = [45, 90, 135, 180, 270]


_MAX_CONCURRENT_FOUNDRY = int(os.getenv("MAX_CONCURRENT_FOUNDRY", "1"))
_FOUNDRY_SLOT_POLL_SECS = 10


class FoundrySlotUnavailableError(RuntimeError):
    """Raised when an incident cannot acquire the Foundry concurrency slot."""


def _set_foundry_active(container, incident_id: str, equipment_id: str, active: bool) -> bool:
    """Patch foundry_active flag on the incident document.

    Uses Cosmos partial-document patch — atomic on the single field, no read-modify-write
    race with concurrent writers (e.g. _mark_incident_analyzing). The partition key MUST
    be equipmentId (the container's PK path).
    """
    if not equipment_id:
        logger.warning(
            "Cannot set foundry_active=%s for %s: equipment_id missing", active, incident_id
        )
        return False
    try:
        patch_operations = [
            {"op": "set", "path": "/foundry_active", "value": active},
        ]
        if active:
            patch_operations.append(
                {
                    "op": "set",
                    "path": "/foundry_active_at",
                    "value": datetime.now(timezone.utc).isoformat(),
                }
            )
        else:
            patch_operations.extend(
                [
                    {"op": "set", "path": "/foundry_active_at", "value": None},
                    {
                        "op": "set",
                        "path": "/foundry_released_at",
                        "value": datetime.now(timezone.utc).isoformat(),
                    },
                ]
            )
        container.patch_item(
            item=incident_id,
            partition_key=equipment_id,
            patch_operations=patch_operations,
        )
        return True
    except Exception as exc:
        logger.warning(
            "Could not patch foundry_active=%s for %s (pk=%s): %s",
            active, incident_id, equipment_id, exc,
        )
        return False


def _parse_utc(value: object) -> datetime | None:
    if not value:
        return None
    try:
        raw = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(raw)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _lock_sort_key(item: dict) -> tuple[datetime, str]:
    parsed = _parse_utc(item.get("foundry_active_at")) or _parse_utc(item.get("updated_at"))
    return (parsed or datetime.min.replace(tzinfo=timezone.utc), str(item.get("id") or ""))


def _release_stale_foundry_locks(container) -> None:
    now = datetime.now(timezone.utc)
    query = (
        "SELECT c.id, c.equipmentId, c.equipment_id, c.status, c.foundry_active_at, "
        "c.updated_at, c.updatedAt FROM c WHERE c.foundry_active = true"
    )
    try:
        active_items = list(container.query_items(query=query, enable_cross_partition_query=True))
    except Exception as exc:
        raise FoundrySlotUnavailableError(f"Could not inspect Foundry locks: {exc}") from exc

    for item in active_items:
        active_at = _parse_utc(item.get("foundry_active_at"))
        updated_at = _parse_utc(item.get("updated_at") or item.get("updatedAt"))
        age_source = active_at or updated_at
        age_secs = (now - age_source).total_seconds() if age_source else float("inf")
        status = str(item.get("status") or "")
        stale = age_secs > FOUNDRY_STALE_LOCK_SECS or (
            status != "analyzing" and age_secs > FOUNDRY_LOCK_GRACE_SECS
        )
        if not stale:
            continue
        equipment_id = str(item.get("equipmentId") or item.get("equipment_id") or "")
        logger.warning(
            "Releasing stale Foundry lock: incident=%s status=%s age=%.0fs",
            item.get("id"), status, age_secs,
        )
        _set_foundry_active(container, str(item.get("id") or ""), equipment_id, False)


def _get_active_foundry_locks(container) -> list[dict]:
    query = (
        "SELECT c.id, c.equipmentId, c.equipment_id, c.status, c.foundry_active_at, "
        "c.updated_at, c.updatedAt FROM c WHERE c.foundry_active = true"
    )
    try:
        items = list(container.query_items(query=query, enable_cross_partition_query=True))
    except Exception as exc:
        raise FoundrySlotUnavailableError(f"Could not query Foundry locks: {exc}") from exc
    return sorted(items, key=_lock_sort_key)


def _wait_for_foundry_slot(
    incident_id: str, equipment_id: str, gate_deadline: float
) -> None:
    """Block until fewer than _MAX_CONCURRENT_FOUNDRY incidents have foundry_active=true.

    Uses a dedicated 'foundry_active' boolean field on the Cosmos incident document as a
    lightweight mutex — distinct from 'analyzing' status, which ALL concurrent incidents
    already share before this gate is reached.  Using 'analyzing' caused deadlock: every
    incident saw every other incident as 'analyzing' and all waited forever.

    Protocol:
      1. Poll: count how many OTHER incidents have foundry_active=true.
      2. If count < MAX: set own foundry_active=true.
      3. Re-read active locks and keep only the oldest MAX lock holders; if we lost
         a simultaneous race, release our flag and keep waiting.
      4. Caller must call _set_foundry_active(..., False) after Foundry returns.
      5. On deadline: raise so Durable retries later, rather than violating the
         one-active-Foundry invariant.
    """
    db = get_cosmos_client().get_database_client(DB_NAME)
    container = db.get_container_client("incidents")

    while True:
        remaining = gate_deadline - time.monotonic()
        if remaining <= 0:
            raise FoundrySlotUnavailableError(
                f"Foundry slot unavailable for {incident_id} after {FOUNDRY_SLOT_WAIT_SECS:.0f}s"
            )

        try:
            _release_stale_foundry_locks(container)
            active_locks = _get_active_foundry_locks(container)
        except FoundrySlotUnavailableError as exc:
            logger.warning(
                "Foundry slot poll failed for %s — retrying within budget: %s",
                incident_id, exc,
            )
            time.sleep(min(_FOUNDRY_SLOT_POLL_SECS, max(0.0, remaining)))
            continue

        other_active = [item for item in active_locks if item.get("id") != incident_id]
        count = len(other_active)

        if count < _MAX_CONCURRENT_FOUNDRY:
            if not _set_foundry_active(container, incident_id, equipment_id, True):
                raise FoundrySlotUnavailableError(
                    f"Could not acquire Foundry slot for {incident_id}"
                )
            try:
                winners = {
                    str(item.get("id"))
                    for item in _get_active_foundry_locks(container)[:_MAX_CONCURRENT_FOUNDRY]
                }
            except FoundrySlotUnavailableError as exc:
                logger.warning(
                    "Foundry slot race check failed for %s — releasing tentative lock: %s",
                    incident_id, exc,
                )
                _set_foundry_active(container, incident_id, equipment_id, False)
                time.sleep(min(_FOUNDRY_SLOT_POLL_SECS, max(0.0, remaining)))
                continue
            if incident_id in winners:
                logger.info(
                    "Foundry slot acquired for %s (%d other(s) active, max=%d)",
                    incident_id, count, _MAX_CONCURRENT_FOUNDRY,
                )
                return
            logger.info(
                "Foundry slot race lost for %s — releasing and waiting", incident_id
            )
            _set_foundry_active(container, incident_id, equipment_id, False)

        logger.info(
            "Foundry busy (%d/%d active) — %s waiting %ds (%.0fs budget left)",
            count, _MAX_CONCURRENT_FOUNDRY, incident_id, _FOUNDRY_SLOT_POLL_SECS, remaining,
        )
        time.sleep(_FOUNDRY_SLOT_POLL_SECS)


def _is_rate_limit_error(err: object) -> bool:
    """Return True if the error is a transient rate-limit / throttle error.

    Handles both plain exceptions/strings and Azure SDK RunError objects
    that expose ``.code`` / ``.message`` attributes.
    """
    # Collect all text representations
    parts = [str(err)]
    if hasattr(err, "code"):
        parts.append(str(getattr(err, "code", "") or ""))
    if hasattr(err, "message"):
        parts.append(str(getattr(err, "message", "") or ""))
    combined = " ".join(parts).lower()
    return (
        "rate_limit" in combined
        or "rate limit" in combined
        or "429" in combined
        or "throttl" in combined
    )


def _call_orchestrator_agent(
    prompt: str,
    agent_id: str,
    *,
    incident_id: str,
    more_info_round: int,
) -> dict:
    """Create a Foundry thread, run the Orchestrator Agent, return parsed result.

    Uses ``create_thread_and_process_run_with_approval`` to handle MCP tool
    approval automatically — the Foundry API (2025-05-15-preview) does not
    persist ``require_approval="never"`` for MCP tools, so every MCP call
    triggers a ``submit_tool_approval`` action that must be approved client-side.

    Rate-limit errors are retried up to _RATE_LIMIT_MAX_RETRIES times with
    exponential back-off.
    """
    deadline = time.monotonic() + FOUNDRY_ACTIVITY_TIMEOUT_SECS

    last_exc: Exception | None = None
    for attempt in range(_RATE_LIMIT_MAX_RETRIES + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise FoundryRunTimeoutError(
                f"Foundry activity budget exhausted after {FOUNDRY_ACTIVITY_TIMEOUT_SECS:.0f}s"
            )

        if attempt > 0:
            base = _RATE_LIMIT_BACKOFF_SECS[min(attempt - 1, len(_RATE_LIMIT_BACKOFF_SECS) - 1)]
            wait = base + random.uniform(0, base / 2)
            wait = min(wait, max(0.0, remaining - 5.0))
            if wait <= 0:
                raise FoundryRunTimeoutError(
                    f"Foundry activity budget exhausted during retry backoff after {FOUNDRY_ACTIVITY_TIMEOUT_SECS:.0f}s"
                )
            logger.warning(
                "Rate limit hit for incident agent (attempt %d/%d) — waiting %.0fs (remaining budget %.0fs)",
                attempt, _RATE_LIMIT_MAX_RETRIES, wait,
                max(0.0, deadline - time.monotonic()),
            )
            time.sleep(wait)

        try:
            client = _build_agents_client()
            with client:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise FoundryRunTimeoutError(
                        f"Foundry activity budget exhausted before run start after {FOUNDRY_ACTIVITY_TIMEOUT_SECS:.0f}s"
                    )

                run = create_thread_and_process_run_with_approval(
                    client,
                    agent_id=agent_id,
                    thread=AgentThreadCreationOptions(
                        messages=[
                            ThreadMessageOptions(role=MessageRole.USER, content=prompt)
                        ]
                    ),
                    max_wait_seconds=remaining,
                )

                if run.status in (RunStatus.FAILED, "failed") or str(run.status).lower() == "failed":
                    err = getattr(run, "last_error", run.status)
                    logger.warning(
                        "Foundry run failed (attempt %d/%d): code=%s message=%s",
                        attempt + 1, _RATE_LIMIT_MAX_RETRIES + 1,
                        getattr(err, "code", ""),
                        getattr(err, "message", str(err))[:200],
                    )
                    if _is_rate_limit_error(err):
                        last_exc = RuntimeError(f"Foundry Orchestrator run failed: {err}")
                        continue  # retry
                    raise RuntimeError(f"Foundry Orchestrator run failed: {err}")

                logger.info(
                    "Foundry run completed: status=%s thread=%s run=%s",
                    run.status, run.thread_id, run.id,
                )

                message_items = list(client.messages.list(thread_id=run.thread_id))
                _run_usage = getattr(run, "usage", None)
                _usage_payload: dict = {}
                if _run_usage is not None:
                    _usage_payload = {
                        "prompt_tokens": getattr(_run_usage, "prompt_tokens", None),
                        "completion_tokens": getattr(_run_usage, "completion_tokens", None),
                        "total_tokens": getattr(_run_usage, "total_tokens", None),
                        "model": "orchestrator",
                    }
                _log_trace_json(
                    incident_id=incident_id,
                    more_info_round=more_info_round,
                    trace_kind="thread_messages",
                    payload={
                        "thread_id": run.thread_id,
                        "run_id": run.id,
                        "status": str(run.status),
                        "usage": _usage_payload or None,
                        "messages": _serialize_thread_messages(message_items),
                    },
                )

                # list_messages returns newest-first; first AGENT message is the answer.
                # NOTE: azure-ai-agents SDK uses MessageRole.AGENT (value="assistant"),
                # but str(MessageRole.AGENT) == "MessageRole.AGENT", NOT "assistant".
                raw_text = ""
                for msg in message_items:
                    role = getattr(msg, "role", None)
                    is_agent = (
                        role == MessageRole.AGENT
                        if hasattr(MessageRole, "AGENT")
                        else "assistant" in str(getattr(role, "value", role)).lower()
                    )
                    if is_agent:
                        for block in msg.content:
                            text_block = getattr(block, "text", None)
                            text_value = getattr(text_block, "value", None)
                            if text_value:
                                raw_text += str(text_value)
                        break

                logger.info(
                    "Foundry raw response length=%d first 500 chars: %s",
                    len(raw_text), raw_text[:500],
                )
                _log_trace_text(
                    incident_id=incident_id,
                    more_info_round=more_info_round,
                    trace_kind="raw_response",
                    text=raw_text,
                    metadata={
                        "thread_id": run.thread_id,
                        "run_id": run.id,
                        "agent_id": agent_id,
                    },
                )
                parsed = _parse_response(raw_text)
                _log_trace_json(
                    incident_id=incident_id,
                    more_info_round=more_info_round,
                    trace_kind="parsed_response",
                    payload=parsed,
                    metadata={
                        "thread_id": run.thread_id,
                        "run_id": run.id,
                        "agent_id": agent_id,
                    },
                )
                return parsed

        except Exception as exc:  # noqa: BLE001
            if _is_rate_limit_error(exc):
                last_exc = exc
                continue  # retry on rate limit
            raise  # re-raise non-rate-limit errors immediately

    # All retries exhausted
    raise last_exc or RuntimeError("run_foundry_agents: all retries exhausted")


def _build_agent_failure_result(
    *,
    incident_id: str,
    previous_ai_result: dict,
    more_info_round: int,
    error: Exception,
) -> dict:
    previous = dict(previous_ai_result or {})
    error_text = str(error).strip() or error.__class__.__name__
    is_timeout = isinstance(error, FoundryRunTimeoutError)
    failure_flag = "FOUNDRY_TIMEOUT" if is_timeout else "FOUNDRY_FAILURE"

    if previous and more_info_round > 0:
        analysis_note = (
            "The latest AI follow-up did not complete successfully, so the previous completed recommendation remains the current guidance. "
            f"Reason: {error_text[:300]}"
        )
        previous_analysis = str(previous.get("analysis") or "").strip()
        merged_analysis = (
            f"{analysis_note}\n\nPrevious completed analysis:\n{previous_analysis}"
            if previous_analysis
            else analysis_note
        )
        return {
            **previous,
            "incident_id": incident_id,
            "analysis": merged_analysis[:4000],
            "operator_dialogue": (
                "I could not finish the follow-up review in time. "
                "The previous completed recommendation is still the latest guidance; "
                "please review it manually or retry the follow-up question later."
            )[:800],
            "confidence_flag": failure_flag,
            "manual_review_required": True,
            "raw_response": error_text,
        }

    return {
        "incident_id": incident_id,
        "title": "Manual Review Required",
        "classification": "analysis_unavailable",
        "risk_level": "LOW_CONFIDENCE",
        "confidence": 0.0,
        "root_cause": "The AI agent did not complete the analysis successfully.",
        "analysis": (
            "The AI analysis did not complete within the allowed execution budget. "
            "The workflow returned a controlled fallback so the incident does not remain stuck in awaiting_agents. "
            f"Reason: {error_text[:300]}"
        ),
        "recommendation": (
            "Manual review is required before proceeding. Retry the AI analysis later if additional automated guidance is still needed."
        ),
        "operator_dialogue": (
            "I could not complete the AI analysis in time. "
            "Manual review is required before proceeding, but the incident is no longer stuck waiting for the agent."
        )[:800],
        "capa_suggestion": "Manual QA review required before CAPA execution.",
        "recommendations": [],
        "regulatory_reference": "",
        "regulatory_refs": [],
        "sop_refs": [],
        "evidence_citations": [],
        "work_order_draft": {},
        "audit_entry_draft": {},
        "batch_disposition": "under_review",
        "confidence_flag": failure_flag,
        "manual_review_required": True,
        "raw_response": error_text,
    }


def _build_prompt(
    incident_id: str,
    context_data: dict,
    more_info_round: int,
    previous_ai_result: dict | None = None,
) -> str:
    """Build the user message that drives the Orchestrator Agent."""
    equipment = _compact_equipment_context(context_data.get("equipment") or {})
    batch = _compact_batch_context(context_data.get("batch") or {})
    recent_incidents = _compact_recent_incidents(context_data.get("recent_incidents") or [])
    alert_payload = context_data.get("alert_payload", {})
    operator_questions = context_data.get("operator_questions", [])

    lines = [
        f"## GMP Deviation Analysis Request — Incident {incident_id}",
        f"**Timestamp:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "### Alert Payload",
        "```json",
        json.dumps(alert_payload, indent=2, default=str),
        "```",
        "",
        "### Known Equipment Summary (routing context only)",
        "```json",
        json.dumps(equipment, indent=2, default=str),
        "```",
        "",
        "### Known Batch Summary (routing context only)",
        "```json",
        json.dumps(batch, indent=2, default=str),
        "```",
        "",
        f"### Known Recent Incident Decisions (last {len(recent_incidents)} on this equipment)",
        "```json",
        json.dumps(recent_incidents, indent=2, default=str),
        "```",
    ]

    if operator_questions:
        lines += [
            "",
            f"### Operator Follow-up Questions (round {more_info_round})",
        ]
        for q in operator_questions:
            lines.append(
                f"- **Round {q['round']}** ({q.get('asked_by', 'operator')}): {q['question']}"
            )

    if more_info_round > 0 and previous_ai_result:
        lines += [
            "",
            "### Previous Recommendation Snapshot (for round comparison)",
            "Use this snapshot to explain what changed or stayed the same in this follow-up response.",
            "```json",
            json.dumps(
                {
                    "recommendation": previous_ai_result.get("recommendation", ""),
                    "root_cause": previous_ai_result.get("root_cause", ""),
                    "risk_level": previous_ai_result.get("risk_level", ""),
                    "batch_disposition": previous_ai_result.get("batch_disposition", ""),
                },
                indent=2,
                default=str,
            ),
            "```",
        ]

    lines += [
        "",
        "---",
        "### Instructions",
        (
            "The summaries above are only routing context to help you call the right tools. "
            "Use your Research sub-agent as the single source of evidence for SOPs, "
            "equipment manuals, BPR product specs, GMP regulations, and historical incidents. "
            "You must actually call the Research sub-agent; do not simulate tool_calls_log or "
            "invent citations from model memory. "
            "You, the Orchestrator, must produce the final structured analysis and decision. "
            "Use your Document sub-agent only after you decide, and pass it only the compact "
            "documentation package it needs: incident identifiers, your final decision fields, "
            "audit/work-order drafting inputs, and citations used."
        ),
        "",
        "Return one JSON object that matches the configured response schema. Required top-level fields: ",
        (
            "incident_id, title, classification, risk_level, confidence, confidence_flag, "
            "root_cause, analysis, recommendation, agent_recommendation, operator_dialogue, "
            "capa_suggestion, regulatory_reference, "
            "batch_disposition, recommendations, regulatory_refs, sop_refs, evidence_citations, "
            "audit_entry_draft, work_order_draft, tool_calls_log, "
            "audit_entry_id, work_order_id. Include execution_error only when a tool/documentation "
            "step fails or returns an error."
        ),
        "Carry forward tool_calls_log from the Research Agent. Merge only documentation fields from Document Agent.",
        "If Research Agent did not return real SOP/GMP/BPR/manual/history evidence, lower confidence and explain the evidence gap.",
        "For REJECT decisions, work_order_draft and work_order_id must be null.",
        "Never fabricate data. Cite sources. Keep operator_dialogue under 120 words and answer follow-up questions directly.",
    ]

    return "\n".join(lines)


def _compact_equipment_context(equipment: dict) -> dict:
    return _pick_present(
        equipment,
        [
            "id",
            "equipment_id",
            "name",
            "equipment_name",
            "type",
            "equipment_type",
            "criticality",
            "equipment_criticality",
            "location",
            "validated_parameters",
            "calibration_status",
            "last_calibration",
            "next_calibration",
        ],
    )


def _compact_batch_context(batch: dict) -> dict:
    return _pick_present(
        batch,
        [
            "id",
            "batch_id",
            "batch_number",
            "product",
            "product_name",
            "stage",
            "stage_step",
            "production_stage",
            "status",
            "bpr_reference",
            "process_parameters",
        ],
    )


def _compact_recent_incidents(recent_incidents: list[dict]) -> list[dict]:
    keys = [
        "id",
        "incident_id",
        "title",
        "parameter",
        "deviation_type",
        "severity",
        "status",
        "createdAt",
        "created_at",
        "lastDecision",
        "finalDecision",
        "agentRecommendation",
        "operatorAgreesWithAgent",
    ]
    return [
        _pick_present(item, keys)
        for item in recent_incidents[:5]
        if isinstance(item, dict)
    ]


def _pick_present(source: dict, keys: list[str]) -> dict:
    return {key: source[key] for key in keys if key in source and source[key] not in (None, "")}


def _log_orchestrator_prompt_trace(
    *,
    incident_id: str,
    more_info_round: int,
    orchestrator_agent_id: str,
    prompt: str,
    context_data: dict,
) -> None:
    # Tracing guard is enforced inside log_trace_text; no separate check needed here.
    prompt_bundle = {
        "orchestrator_agent_id": orchestrator_agent_id,
        "configured_models": _configured_agent_models(),
        "operator_questions": context_data.get("operator_questions", []),
        "system_prompts": _system_prompt_snapshot(orchestrator_agent_id),
    }
    _log_trace_json(
        incident_id=incident_id,
        more_info_round=more_info_round,
        trace_kind="prompt_context",
        payload=prompt_bundle,
    )
    _log_trace_text(
        incident_id=incident_id,
        more_info_round=more_info_round,
        trace_kind="orchestrator_user_prompt",
        text=prompt,
        metadata={"orchestrator_agent_id": orchestrator_agent_id},
    )


def _configured_agent_models() -> dict[str, str]:
    return {
        "research": _resolve_agent_model(
            "FOUNDRY_RESEARCH_AGENT_MODEL", DEFAULT_RESEARCH_AGENT_MODEL
        ),
        "document": _resolve_agent_model(
            "FOUNDRY_DOCUMENT_AGENT_MODEL",
            DEFAULT_DOCUMENT_AGENT_MODEL,
        ),
        "orchestrator": _resolve_agent_model(
            "FOUNDRY_ORCHESTRATOR_AGENT_MODEL",
            DEFAULT_ORCHESTRATOR_AGENT_MODEL,
        ),
    }


def _resolve_agent_model(env_var: str, default_model: str) -> str:
    override = os.getenv(env_var, "").strip()
    if override:
        return override

    global_override = os.getenv("FOUNDRY_AGENT_MODEL", "").strip()
    if global_override:
        return global_override

    return default_model


def _build_agents_client() -> AgentsClient:
    endpoint = os.environ.get(
        "AZURE_AI_FOUNDRY_AGENTS_ENDPOINT",
        os.environ.get("AZURE_AI_FOUNDRY_PROJECT_CONNECTION_STRING", ""),
    )
    return AgentsClient(endpoint=endpoint, credential=DefaultAzureCredential())


def _system_prompt_snapshot(orchestrator_agent_id: str) -> dict[str, str]:
    return {
        "orchestrator": _read_agent_prompt(orchestrator_agent_id, "orchestrator_system.md"),
        "research": _read_agent_prompt(
            os.getenv("RESEARCH_AGENT_ID", "").strip(),
            "research_system.md",
        ),
        "document": _read_agent_prompt(
            os.getenv("DOCUMENT_AGENT_ID", "").strip(),
            "document_system.md",
        ),
    }


def _read_agent_prompt(agent_id: str, file_name: str) -> str:
    live_instructions = _get_live_agent_instructions(agent_id)
    if live_instructions:
        return live_instructions

    prompt_path = _resolve_prompt_path(file_name)
    if prompt_path is None:
        return f"<prompt file unavailable: {file_name}>"

    try:
        return prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"<failed to read {prompt_path}: {exc}>"


@lru_cache(maxsize=8)
def _get_live_agent_instructions(agent_id: str) -> str:
    if not agent_id:
        return ""

    try:
        client = _build_agents_client()
        with client:
            agent = client.get_agent(agent_id)
        return str(getattr(agent, "instructions", "") or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch live agent instructions for %s: %s", agent_id, exc)
        return ""


def _resolve_prompt_path(file_name: str) -> Path | None:
    direct_candidate = AGENT_PROMPTS_DIR / file_name
    if direct_candidate.is_file():
        return direct_candidate

    for parent in Path(__file__).resolve().parents:
        candidate = parent / "agents" / "prompts" / file_name
        if candidate.is_file():
            return candidate

    return None


def _serialize_thread_messages(messages: Sequence[object]) -> list[dict[str, object]]:
    serialized: list[dict[str, object]] = []
    for message in messages:
        serialized.append(
            {
                "id": getattr(message, "id", None),
                "role": _serialize_value(getattr(message, "role", None)),
                "created_at": getattr(message, "created_at", None),
                "metadata": _serialize_value(getattr(message, "metadata", None)),
                "content": _serialize_message_content(getattr(message, "content", [])),
            }
        )
    return serialized


def _serialize_message_content(content_blocks: Sequence[object] | None) -> list[dict[str, object]]:
    serialized_blocks: list[dict[str, object]] = []
    for block in content_blocks or []:
        text_block = getattr(block, "text", None)
        text_value = getattr(text_block, "value", None)
        serialized_blocks.append(
            {
                "type": getattr(block, "type", block.__class__.__name__),
                "text": text_value,
                "raw": _serialize_value(block if text_value is None else None),
            }
        )
    return serialized_blocks


def _serialize_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_value(item) for item in value]
    if hasattr(value, "__dict__"):
        return {
            str(key): _serialize_value(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return str(value)


# Aliases kept so call-sites within this file don't need to change
_log_trace_json = log_trace_json
_log_trace_text = log_trace_text


def _parse_response(raw_text: str) -> dict:
    """Extract JSON block from agent response, with graceful fallback."""
    # Try ```json ... ``` block first
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            data.setdefault("raw_response", raw_text)
            return data
        except json.JSONDecodeError:
            pass

    # Try to parse the whole response as JSON
    try:
        data = json.loads(raw_text.strip())
        data.setdefault("raw_response", raw_text)
        return data
    except json.JSONDecodeError:
        pass

    # Fallback — unstructured response (shouldn't happen in production)
    logger.warning("Could not parse structured JSON from Foundry agent response")
    return {
        "title": "Deviation Review Required",
        "analysis": raw_text[:2000] if raw_text else "Analysis not available.",
        "root_cause": "Could not determine root cause automatically.",
        "operator_dialogue": "I could not produce a structured follow-up summary for the operator.",
        "classification": "unknown",
        "risk_level": "unknown",
        "confidence": 0.5,
        "confidence_flag": "PARSE_ERROR",
        "recommendations": [],
        "regulatory_refs": [],
        "sop_refs": [],
        "evidence_citations": [],
        "work_order_draft": {},
        "audit_entry_draft": {},
        "batch_disposition": "hold_pending_review",
        "raw_response": raw_text,
    }


def _normalize_agent_result(
    result: dict,
    rag_context: dict | None,
    more_info_round: int,
    previous_ai_result: dict | None = None,
    operator_questions: list[dict] | None = None,
) -> dict:
    """Make citation output stable for the operator UI."""
    result["title"] = _normalize_incident_title(result)
    result["evidence_citations"] = _normalize_evidence_citations(
        result,
        rag_context or {},
        current_incident_id=str(result.get("incident_id") or ""),
    )
    result["sop_refs"] = _normalize_reference_collection(
        result["evidence_citations"],
        citation_type="sop",
    )
    result["regulatory_refs"] = _normalize_reference_collection(
        result["evidence_citations"],
        citation_type="gmp",
    )
    normalized_reference = _build_regulatory_reference_summary(
        result["sop_refs"],
        result["regulatory_refs"],
    )
    if normalized_reference or result["evidence_citations"]:
        result["regulatory_reference"] = normalized_reference
    result["operator_dialogue"] = _normalize_operator_dialogue(
        result,
        more_info_round,
        previous_ai_result=previous_ai_result or {},
        operator_questions=operator_questions or [],
    )
    # Normalize agent_recommendation: keep APPROVE/REJECT as-is, derive from risk_level as fallback
    raw_rec = str(result.get("agent_recommendation") or "").strip().upper()
    if raw_rec in ("APPROVE", "REJECT"):
        result["agent_recommendation"] = raw_rec
    else:
        risk = str(result.get("risk_level") or "").upper()
        if risk in ("BLOCKED", "LOW_CONFIDENCE") or result.get("manual_review_required"):
            result["agent_recommendation"] = None
        elif risk in ("HIGH", "CRITICAL", "MEDIUM"):
            result["agent_recommendation"] = "APPROVE"
        elif risk == "LOW":
            result["agent_recommendation"] = "REJECT"
        else:
            result["agent_recommendation"] = None
    return result


def _normalize_reference_collection(
    citations: list[dict],
    *,
    citation_type: str,
) -> list[dict]:
    normalized_refs: list[dict] = []

    for citation in citations:
        if str(citation.get("type") or "") != citation_type:
            continue

        section_display = _reference_section_display(citation)
        base_ref = {
            "type": citation_type,
            "source": citation.get("source", ""),
            "reference": citation.get("reference", ""),
            "document_id": citation.get("document_id", ""),
            "document_title": citation.get("document_title", ""),
            "section": section_display,
            "section_heading": citation.get("section_heading", ""),
            "section_key": citation.get("section_key", ""),
            "section_path": citation.get("section_path", ""),
            "text_excerpt": citation.get("text_excerpt", ""),
            "source_blob": citation.get("source_blob", ""),
            "container": citation.get("container", ""),
            "index_name": citation.get("index_name", ""),
            "chunk_index": citation.get("chunk_index"),
            "score": citation.get("score"),
            "url": citation.get("url", ""),
            "resolution_status": citation.get("resolution_status", ""),
            "unresolved_reason": citation.get("unresolved_reason", ""),
        }

        if citation_type == "sop":
            normalized_refs.append(
                {
                    **base_ref,
                    "id": citation.get("document_id") or citation.get("source") or "",
                    "title": citation.get("document_title") or citation.get("source") or "",
                    "relevant_section": section_display,
                }
            )
            continue

        normalized_refs.append(
            {
                **base_ref,
                "regulation": _reference_label(citation),
            }
        )

    if citation_type != "sop":
        normalized_refs.sort(key=lambda item: 0 if str(item.get("section") or "").strip() else 1)

    return normalized_refs


def _build_regulatory_reference_summary(
    sop_refs: list[dict],
    regulatory_refs: list[dict],
) -> str:
    parts: list[str] = []
    seen: set[str] = set()

    for item in [*(sop_refs or []), *(regulatory_refs or [])]:
        label = _reference_label(item)
        if not label:
            continue

        if _should_skip_reference_summary_item(item, label):
            continue

        section = _reference_summary_section_display(item)
        summary = f"{label} {section}".strip() if section else label
        if not summary:
            continue

        key = summary.lower()
        if key in seen:
            continue

        seen.add(key)
        parts.append(summary)

    return "; ".join(parts)


def _reference_label(item: dict) -> str:
    citation_type = str(item.get("type") or "")
    if citation_type == "sop":
        candidates = [
            item.get("source"),
            item.get("document_title"),
            item.get("title"),
            item.get("id"),
            item.get("document_id"),
        ]
    else:
        candidates = [
            item.get("document_title"),
            item.get("regulation"),
            item.get("reference"),
            item.get("source"),
            item.get("document_id"),
        ]

    fallback = ""
    for candidate in candidates:
        label = _display_reference_label(candidate)
        if not label:
            continue
        if not fallback:
            fallback = label
        if _is_generic_reference_label(label):
            continue
        return label

    return "" if _is_generic_reference_label(fallback) else fallback


def _display_reference_label(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    for separator in (" — ", " · "):
        prefix, found, _suffix = text.partition(separator)
        if found and prefix.strip():
            return prefix.strip()

    return text


def _is_generic_reference_label(value: str) -> bool:
    normalized = _normalize_text(value)
    return normalized in {
        "sop",
        "gmp",
        "bpr",
        "manual",
        "historical",
        "document",
        "incident",
        "evidence",
    }


def _should_skip_reference_summary_item(item: dict, label: str) -> bool:
    if _is_generic_reference_label(label):
        return True

    if str(item.get("resolution_status") or "") != "unresolved":
        return False

    has_link = bool(str(item.get("url") or "").strip())
    has_document = bool(str(item.get("document_id") or "").strip())
    return not has_link and not has_document


def _reference_section_display(citation: dict) -> str:
    if _should_suppress_unverified_section(citation):
        return ""

    section_key = str(citation.get("section_key") or "").strip()
    if section_key and re.fullmatch(r"\d+(?:\.\d+)*", section_key):
        return f"§{section_key}"

    return str(
        citation.get("section")
        or citation.get("relevant_section")
        or citation.get("section_heading")
        or ""
    ).strip()


def _reference_summary_section_display(citation: dict) -> str:
    if _has_unverified_authoritative_section(citation):
        return ""

    return _reference_section_display(citation)


def _should_suppress_unverified_section(citation: dict) -> bool:
    if _is_weak_generic_regulatory_citation(citation):
        return True

    if (
        _has_unverified_authoritative_section(citation)
        and str(citation.get("_source_collection") or "") == "regulatory_refs"
    ):
        return True

    return False


def _is_weak_generic_regulatory_citation(citation: dict) -> bool:
    citation_type = str(citation.get("type") or "").strip()
    if citation_type == "sop":
        return False

    source = str(citation.get("source") or "").strip()
    reference = str(citation.get("reference") or "").strip()
    return _is_generic_reference_label(source) and not reference


def _has_unverified_authoritative_section(citation: dict) -> bool:
    unresolved_reason = _normalize_text(str(citation.get("unresolved_reason") or ""))
    return "authoritative section match" in unresolved_reason


def _normalize_operator_dialogue(
    result: dict,
    more_info_round: int,
    previous_ai_result: dict | None = None,
    operator_questions: list[dict] | None = None,
) -> str:
    explicit = str(result.get("operator_dialogue") or "").strip()
    previous_ai_result = previous_ai_result or {}
    operator_questions = operator_questions or []

    if more_info_round <= 0 and _should_rewrite_initial_operator_dialogue(explicit):
        explicit = ""

    if explicit and not _should_rewrite_followup_dialogue(
        explicit,
        result,
        previous_ai_result,
        operator_questions,
        more_info_round,
    ):
        return explicit[:800]

    recommendation = str(result.get("recommendation") or "").strip()
    analysis = str(result.get("analysis") or "").strip()

    if more_info_round <= 0:
        return (recommendation or analysis or "AI agent provided an initial recommendation.")[:800]

    if recommendation:
        return _build_followup_operator_dialogue(
            result,
            previous_ai_result,
            operator_questions,
        )[:800]

    return (
        "I reviewed your follow-up question and updated the analysis using available data."
    )[:800]


def _should_rewrite_initial_operator_dialogue(explicit: str) -> bool:
    normalized_explicit = _normalize_text(explicit)
    if not normalized_explicit:
        return False

    invalid_initial_markers = (
        "recommendation remains",
        "remains the same",
        "remains unchanged",
        "stayed the same",
        "recommendation stayed",
        "updated recommendation",
        "updated root cause",
        "follow-up question",
    )
    return any(marker in normalized_explicit for marker in invalid_initial_markers)


def _should_rewrite_followup_dialogue(
    explicit: str,
    result: dict,
    previous_ai_result: dict,
    operator_questions: list[dict],
    more_info_round: int,
) -> bool:
    if more_info_round <= 0:
        return not explicit

    normalized_explicit = _normalize_text(explicit)
    if not normalized_explicit:
        return True

    recommendation = _normalize_text(str(result.get("recommendation") or ""))
    previous_dialogue = _normalize_text(str(previous_ai_result.get("operator_dialogue") or ""))

    if len(normalized_explicit.split()) < 12:
        return True

    if recommendation and SequenceMatcher(None, normalized_explicit, recommendation).ratio() >= 0.88:
        return True

    if previous_dialogue and SequenceMatcher(None, normalized_explicit, previous_dialogue).ratio() >= 0.88:
        return True

    latest_question = _get_latest_operator_question(operator_questions)
    if latest_question and _is_direct_requirement_question(latest_question):
        if not _answers_direct_requirement_question(normalized_explicit):
            return True

    if latest_question and not _mentions_change_or_reason(normalized_explicit):
        return True

    return False


def _build_followup_operator_dialogue(
    result: dict,
    previous_ai_result: dict,
    operator_questions: list[dict],
) -> str:
    latest_question = _get_latest_operator_question(operator_questions)
    root_cause = str(result.get("root_cause") or "").strip()
    changed_fields = _get_changed_followup_fields(result, previous_ai_result)
    direct_requirement_answer = _build_direct_requirement_answer(latest_question, result)

    if latest_question:
        intro = f'I reviewed your follow-up question: "{_shorten_text(latest_question, 90)}".'
    else:
        intro = "I reviewed your follow-up question and re-checked the available evidence."

    if changed_fields:
        field_summary = _human_join(changed_fields)
        details: list[str] = [intro]
        if direct_requirement_answer:
            details.append(direct_requirement_answer)
        details.append(f"I updated {field_summary} based on the available evidence.")
        details.append(_build_updated_decision_summary(result))
        if root_cause and "the root cause hypothesis" in changed_fields:
            details.append(f"Updated root cause hypothesis: {_shorten_text(root_cause, 120)}")
        return _compose_dialogue_parts(details)

    no_change_parts = [intro]
    if direct_requirement_answer:
        no_change_parts.append(direct_requirement_answer)
        no_change_parts.append(_build_no_change_decision_reason(result))
    else:
        no_change_parts.append(
            "I did not find enough new evidence to change the current recommendation or root-cause hypothesis."
        )
    decision_summary = _build_current_decision_summary(result)
    if decision_summary:
        no_change_parts.append(decision_summary)
    return _compose_dialogue_parts(no_change_parts)


def _get_changed_followup_fields(result: dict, previous_ai_result: dict) -> list[str]:
    labels = {
        "recommendation": "the recommendation",
        "root_cause": "the root cause hypothesis",
        "risk_level": "the risk level",
        "batch_disposition": "the batch disposition",
    }
    changed: list[str] = []
    for field, label in labels.items():
        current_value = _normalize_text(str(result.get(field) or ""))
        previous_value = _normalize_text(str(previous_ai_result.get(field) or ""))
        if current_value and current_value != previous_value:
            changed.append(label)
    return changed


def _get_latest_operator_question(operator_questions: list[dict]) -> str:
    if not operator_questions:
        return ""
    latest = operator_questions[-1]
    return str(latest.get("question") or "").strip()


def _is_direct_requirement_question(question: str) -> bool:
    normalized_question = _normalize_text(question)
    if not normalized_question:
        return False

    requirement_markers = (
        "direct requirement",
        "directly require",
        "mandate",
        "requirement to",
        "required to",
        "must stop",
        "stop the line",
        "line stop",
    )
    document_markers = ("bpr", "sop", "document", "procedure")
    return any(marker in normalized_question for marker in requirement_markers) and any(
        marker in normalized_question for marker in document_markers
    )


def _answers_direct_requirement_question(normalized_dialogue: str) -> bool:
    answer_markers = (
        "i did not find a direct",
        "i found a direct",
        "there is no direct requirement",
        "there is a direct requirement",
        "the bpr does not",
        "the bpr requires",
        "the sop does not",
        "the sop requires",
        "does not directly require",
        "directly requires",
        "does not state",
        "states that",
    )
    return any(marker in normalized_dialogue for marker in answer_markers)


def _build_direct_requirement_answer(latest_question: str, result: dict) -> str:
    if not _is_direct_requirement_question(latest_question):
        return ""

    source, section, excerpt = _extract_requirement_evidence(result)
    if excerpt and _has_direct_stop_requirement(excerpt):
        source_label = _format_evidence_label(source, section)
        if source_label:
            return (
                f'I found a retrieved document instruction in {source_label} that directly requires a stop or hold action: '
                f'"{_shorten_text(excerpt, 140)}".'
            )
        return (
            f'I found a retrieved document instruction that directly requires a stop or hold action: '
            f'"{_shorten_text(excerpt, 140)}".'
        )

    if excerpt:
        source_label = _format_evidence_label(source, section)
        if source_label:
            return (
                "I did not find a retrieved BPR or SOP instruction that directly requires stopping the line at this condition. "
                f'The closest cited document limit in {source_label} is "{_shorten_text(excerpt, 140)}".'
            )
        return (
            "I did not find a retrieved BPR or SOP instruction that directly requires stopping the line at this condition. "
            f'The closest cited document limit is "{_shorten_text(excerpt, 140)}".'
        )

    return "I did not find a retrieved BPR or SOP instruction that directly requires stopping the line at this condition."


def _build_no_change_decision_reason(result: dict) -> str:
    source, section, excerpt = _extract_requirement_evidence(result)
    source_label = _format_evidence_label(source, section)
    batch_disposition = _humanize_batch_disposition(str(result.get("batch_disposition") or ""))

    if excerpt:
        if source_label and batch_disposition:
            return (
                f'I kept the recommendation and batch disposition unchanged because {source_label} still points to '
                f'"{_shorten_text(excerpt, 140)}", so the batch should remain {batch_disposition} while the deviation is investigated.'
            )
        if source_label:
            return (
                f'I kept the recommendation unchanged because {source_label} still points to '
                f'"{_shorten_text(excerpt, 140)}", and that does not support changing the current decision.'
            )

    if batch_disposition:
        return (
            f'I kept the recommendation and batch disposition unchanged because the available evidence still supports '
            f'keeping the batch {batch_disposition} while the deviation is investigated.'
        )

    return "I kept the recommendation unchanged because the available evidence still supports the current decision."


def _build_current_decision_summary(result: dict) -> str:
    summary_parts: list[str] = []

    batch_disposition = _humanize_batch_disposition(str(result.get("batch_disposition") or ""))
    if batch_disposition:
        summary_parts.append(f"The batch remains {batch_disposition}.")

    recommendation = str(result.get("recommendation") or "").strip()
    if recommendation:
        summary_parts.append(f"Recommended next action: {recommendation}")

    return " ".join(summary_parts).strip()


def _build_updated_decision_summary(result: dict) -> str:
    summary_parts: list[str] = []

    batch_disposition = _humanize_batch_disposition(str(result.get("batch_disposition") or ""))
    if batch_disposition:
        summary_parts.append(f"The batch is now {batch_disposition}.")

    recommendation = str(result.get("recommendation") or "").strip()
    if recommendation:
        summary_parts.append(f"Recommended next action: {_shorten_text(recommendation, 160)}")

    return " ".join(summary_parts).strip()


def _humanize_batch_disposition(batch_disposition: str) -> str:
    labels = {
        "hold_pending_review": "on hold pending review",
        "conditional_release_pending_testing": "under conditional release pending testing",
        "rejected": "rejected",
        "release": "released",
    }
    normalized = _normalize_text(batch_disposition)
    return labels.get(normalized, batch_disposition.replace("_", " ").strip())


def _extract_requirement_evidence(result: dict) -> tuple[str, str, str]:
    prioritized: list[tuple[str, str, str]] = []
    fallback: list[tuple[str, str, str]] = []

    for collection_name in ("evidence_citations", "sop_refs", "regulatory_refs"):
        for item in result.get(collection_name, []) or []:
            if not isinstance(item, dict):
                continue

            source = str(
                item.get("source")
                or item.get("document_title")
                or item.get("id")
                or item.get("regulation")
                or ""
            ).strip()
            section = str(item.get("section") or item.get("relevant_section") or "").strip()
            excerpt = str(item.get("text_excerpt") or "").strip()
            if not excerpt:
                continue

            normalized_haystack = _normalize_text(f"{source} {section} {excerpt}")
            candidate = (source, section, excerpt)
            if "bpr" in normalized_haystack or "product nor" in normalized_haystack:
                prioritized.append(candidate)
            elif "sop" in normalized_haystack or "procedure" in normalized_haystack:
                prioritized.append(candidate)
            else:
                fallback.append(candidate)

    if prioritized:
        return prioritized[0]
    if fallback:
        return fallback[0]
    return "", "", ""


def _has_direct_stop_requirement(excerpt: str) -> bool:
    normalized_excerpt = _normalize_text(excerpt)
    stop_markers = (
        "stop the line",
        "must stop",
        "halt production",
        "production must be stopped",
        "hold the batch",
        "batch must be held",
        "reject the batch",
    )
    return any(marker in normalized_excerpt for marker in stop_markers)


def _format_evidence_label(source: str, section: str) -> str:
    if source and section:
        return f"{source} {section}"
    return source or section


def _mentions_change_or_reason(normalized_text: str) -> bool:
    markers = (
        "reviewed",
        "checked",
        "question",
        "changed",
        "change",
        "same",
        "remains",
        "because",
        "evidence",
        "updated",
        "no change",
    )
    return any(marker in normalized_text for marker in markers)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _shorten_text(text: str, limit: int) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    shortened = compact[: limit - 3].rsplit(" ", 1)[0].strip()
    return f"{shortened}..." if shortened else compact[: limit - 3] + "..."


def _compose_dialogue_parts(parts: list[str], limit: int = 800) -> str:
    message = ""
    for part in parts:
        compact_part = re.sub(r"\s+", " ", str(part or "")).strip()
        if not compact_part:
            continue

        candidate = f"{message} {compact_part}".strip() if message else compact_part
        if len(candidate) <= limit:
            message = candidate
            continue

        remaining = limit - len(message) - (1 if message else 0)
        if remaining <= 0:
            break

        shortened_part = _shorten_text(compact_part, remaining)
        message = f"{message} {shortened_part}".strip() if message else shortened_part
        break

    return message


def _human_join(items: list[str]) -> str:
    if not items:
        return "the analysis"
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _normalize_incident_title(result: dict) -> str:
    explicit_title = str(result.get("title") or "").strip()
    if explicit_title:
        return explicit_title

    classification = str(result.get("classification") or result.get("deviation_classification") or "").strip()
    recommendation = str(result.get("recommendation") or result.get("analysis") or "").strip()

    if classification:
        return classification.replace("_", " ").title()

    if recommendation:
        short = recommendation.split(".", 1)[0].strip()
        return short[:80] if short else "Deviation Review Required"

    return "Deviation Review Required"


def _normalize_evidence_citations(
    result: dict,
    rag_context: dict,
    *,
    current_incident_id: str = "",
) -> list[dict]:
    flat_hits = _flatten_rag_hits(rag_context)
    raw_items: list[dict] = []
    has_type_from_evidence: set[str] = set()

    for item in result.get("evidence_citations", []) or []:
        if isinstance(item, dict):
            raw_items.append(item)
            item_type = str(item.get("type") or "").strip()
            if item_type:
                has_type_from_evidence.add(item_type)
        elif isinstance(item, str):
            raw_items.append({"source": item})

    if "sop" not in has_type_from_evidence:
        for item in result.get("sop_refs", []) or []:
            if isinstance(item, dict):
                raw_items.append({"type": "sop", **item})
            elif isinstance(item, str):
                raw_items.append({"type": "sop", "source": item, "document_id": item})

    if "gmp" not in has_type_from_evidence:
        for item in result.get("regulatory_refs", []) or []:
            if isinstance(item, dict):
                raw_items.append({"type": "gmp", "_source_collection": "regulatory_refs", **item})
            elif isinstance(item, str):
                raw_items.append({"type": "gmp", "_source_collection": "regulatory_refs", "source": item, "document_title": item})

    normalized: list[dict] = []
    seen: set[tuple] = set()
    for item in raw_items:
        citation = _normalize_single_citation(item, flat_hits)
        if citation.get("type") == "incident" or _citation_points_to_incident(
            citation,
            current_incident_id,
        ):
            continue
        key = _citation_identity_key(citation)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(citation)

    _append_historical_citation_fallback(
        normalized,
        flat_hits,
        seen,
        current_incident_id=current_incident_id,
    )

    # Post-normalization: fix section-mismatch unresolved citations via targeted search
    _resolve_section_mismatch_citations(normalized)

    # Remove ghost citations that duplicate a real document citation for the same section
    normalized = _deduplicate_ghost_citations(normalized)

    return normalized


def _append_historical_citation_fallback(
    normalized: list[dict],
    flat_hits: list[dict],
    seen: set[tuple],
    *,
    current_incident_id: str = "",
) -> None:
    if any(str(citation.get("type") or "") == "historical" for citation in normalized):
        return

    for hit in flat_hits:
        if hit.get("index_name") != "idx-incident-history":
            continue

        citation = _normalize_single_citation(
            {
                "type": "historical",
                "document_id": hit.get("document_id", ""),
                "document_title": hit.get("document_title", ""),
                "source_blob": hit.get("source", ""),
                "chunk_index": hit.get("chunk_index"),
                "score": hit.get("score"),
                "text_excerpt": hit.get("text", ""),
            },
            flat_hits,
        )
        if _citation_points_to_incident(citation, current_incident_id):
            continue

        key = _citation_identity_key(citation)
        if key in seen:
            continue

        seen.add(key)
        normalized.append(citation)
        return


def _flatten_rag_hits(rag_context: dict) -> list[dict]:
    hits: list[dict] = []
    for index_name, index_hits in rag_context.items():
        meta = INDEX_EVIDENCE_META.get(index_name, {})
        for hit in index_hits or []:
            hits.append(
                {
                    **hit,
                    "index_name": index_name,
                    "type": meta.get("type", hit.get("document_type", "")),
                    "container": meta.get("container", ""),
                }
            )
    return hits


def _normalize_single_citation(item: dict, flat_hits: list[dict]) -> dict:
    # When the agent supplies an explicit document_id (enforced by JSON schema),
    # pin the search to that document instead of fuzzy-matching across all RAG
    # hits.  This prevents the cross-document mismatch that occurs when the RAG
    # top hit is a different document than the one the agent actually cited.
    explicit_doc_id = str(item.get("document_id") or "").strip()
    # Track whether the match was pinned to the agent's explicit document_id so
    # we can trust the authoritative section heading without requiring the
    # agent's section name to match verbatim.
    _pinned_doc_match = False
    if explicit_doc_id:
        pinned_hits = [
            h for h in flat_hits
            if str(h.get("document_id") or "").strip().lower() == explicit_doc_id.lower()
        ]
        match = _find_matching_hit(item, pinned_hits) if pinned_hits else None
        if match:
            _pinned_doc_match = True
        # Document not present in RAG cache — do a live targeted lookup so we
        # can still resolve the section even if the agent cited a document that
        # was not the top RAG result for the original search query.
        if not match:
            citation_type_hint = str(item.get("type") or "").strip().lower()
            index_name = _TYPE_TO_INDEX.get(citation_type_hint, "")
            section_claim = str(item.get("section") or "").strip()
            if index_name and section_claim:
                match = _targeted_section_lookup(explicit_doc_id, section_claim, index_name)
                if match:
                    _pinned_doc_match = True
    else:
        match = _find_matching_hit(item, flat_hits)
    citation_type = item.get("type") or _infer_citation_type(item, match)
    source = item.get("source") or (match or {}).get("document_id") or (match or {}).get("document_title") or ""
    reference = item.get("reference") or item.get("regulation") or ""
    document_title = (
        item.get("document_title")
        or item.get("title")
        or item.get("regulation")
        or item.get("reference")
        or (match or {}).get("document_title")
        or item.get("source")
        or ""
    )
    document_id = (
        item.get("document_id")
        or item.get("id")
        or item.get("reference")
        or (match or {}).get("document_id")
        or ""
    )
    source_blob = item.get("source_blob") or item.get("sourceBlob") or (match or {}).get("source", "")
    container = item.get("container") or (match or {}).get("container", "")
    if citation_type == "historical" and not document_id:
        document_id = _extract_historical_incident_id(source_blob or source or document_title)
    known_doc = _infer_known_document(item)
    if not document_id and known_doc:
        document_id = known_doc.get("document_id", "")
    if not source_blob and known_doc:
        source_blob = known_doc["source_blob"]
    if not container and known_doc:
        container = known_doc["container"]
    if known_doc and document_id == known_doc.get("document_id") and document_title != known_doc["document_title"]:
        document_title = known_doc["document_title"]
    elif known_doc and (
        not document_title
        or document_title in {"equipment_manual_notes", "incident", "details", "sop", "gmp", "manual", "batch record", "bpr_constraints"}
        or document_title.lower() in {
            known_doc.get("document_id", "").lower(),
            str(source or "").lower(),
            str(reference or "").lower(),
        }
    ):
        document_title = known_doc["document_title"]
    if citation_type == "historical" and document_id and document_title.lower() in {"incident", "details", "historical"}:
        document_title = f"Similar incident {document_id}"
    if not document_title:
        if citation_type == "historical" and document_id:
            document_title = f"Similar incident {document_id}"
        else:
            document_title = source or reference
    section_claim = str(item.get("section") or item.get("relevant_section") or "").strip()
    raw_excerpt_matches_source = _raw_excerpt_matches_hit(item, match)
    # When the agent explicitly identified the document and we found a match in
    # that document, trust the document's authoritative section heading even if
    # the agent's section name doesn't match verbatim.
    section, section_verified = _resolve_citation_section(
        section_claim,
        match,
        citation_type=citation_type,
        prefer_authoritative=raw_excerpt_matches_source or _pinned_doc_match,
    )
    section_heading = str(item.get("section_heading") or (match or {}).get("section_heading") or section).strip()
    section_key = str(
        item.get("section_key")
        or ((match or {}).get("section_key") if section_verified else "")
        or _normalize_section_key(section)
    ).strip()
    section_path = str(item.get("section_path") or (match or {}).get("section_path") or section_heading or section).strip()
    text_excerpt = _build_citation_excerpt(item, match)
    url = item.get("url") or _citation_url(
        citation_type=citation_type,
        document_id=document_id,
        container=container,
        source_blob=source_blob,
    )
    resolution_status, unresolved_reason = _classify_citation_resolution(
        citation_type=citation_type,
        document_title=document_title,
        section=section,
        section_verified=section_verified,
        authoritative_section_available=bool((match or {}).get("section_heading")),
        text_excerpt=text_excerpt,
        url=url,
        container=container,
        source_blob=source_blob,
    )

    citation = {
        "type": citation_type,
        "source": source,
        "reference": reference,
        "document_id": document_id,
        "document_title": document_title,
        "section": section,
        "section_heading": section_heading,
        "section_key": section_key,
        "section_path": section_path,
        "text_excerpt": text_excerpt,
        "source_blob": source_blob,
        "container": container,
        "index_name": item.get("index_name") or (match or {}).get("index_name", ""),
        "chunk_index": item.get("chunk_index", (match or {}).get("chunk_index")),
        "score": item.get("score", (match or {}).get("score")),
        "resolution_status": resolution_status,
        "unresolved_reason": unresolved_reason,
        "_source_collection": item.get("_source_collection", ""),
    }
    citation["url"] = url
    return citation


def _citation_identity_key(citation: dict) -> tuple[str, str, str, str]:
    primary_id = (
        str(citation.get("source_blob") or "").strip()
        or str(citation.get("document_id") or "").strip()
        or str(citation.get("url") or "").strip()
        or str(citation.get("reference") or "").strip()
        or str(citation.get("source") or "").strip()
        or str(citation.get("document_title") or "").strip()
    )
    if _should_suppress_unverified_section(citation):
        section = ""
    else:
        section = str(citation.get("section_key") or citation.get("section") or "").strip()
    citation_type = str(citation.get("type") or "").strip()
    return (citation_type, primary_id.lower(), section.lower(), "")


def _citation_points_to_incident(citation: dict, incident_id: str) -> bool:
    expected = str(incident_id or "").strip().upper()
    if not expected:
        return False

    candidates = (
        citation.get("document_id"),
        citation.get("source_blob"),
        citation.get("source"),
        citation.get("reference"),
        citation.get("document_title"),
        citation.get("url"),
    )
    for value in candidates:
        text = str(value or "").strip()
        if not text:
            continue
        if text.upper() == expected:
            return True
        extracted = _extract_historical_incident_id(text)
        if extracted == expected:
            return True
    return False


def _normalize_section_key(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    explicit_matches = re.findall(r"§\s*(\d+(?:\.\d+)*)", text)
    if explicit_matches:
        return explicit_matches[-1].lower()

    matches = re.findall(r"(?<!\w)(\d+(?:\.\d+)*)(?!\w)", text)
    if matches:
        return matches[-1].lower()

    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:80]


def _section_claim_matches_hit(section_claim: str, hit: dict | None) -> bool:
    if not section_claim or not hit:
        return False

    claim_text = str(section_claim).strip().lower()
    claim_key = _normalize_section_key(section_claim)
    hit_heading = str(hit.get("section_heading") or "").strip()
    hit_path = str(hit.get("section_path") or "").strip()
    hit_key = _normalize_section_key(hit.get("section_key") or hit_heading or hit_path)

    if claim_key and hit_key and claim_key == hit_key:
        return True

    return any(
        claim_text and claim_text in value.lower()
        for value in (hit_heading, hit_path)
        if value
    )


def _resolve_citation_section(
    section_claim: str,
    match: dict | None,
    *,
    citation_type: str,
    prefer_authoritative: bool,
) -> tuple[str, bool]:
    authoritative_heading = str((match or {}).get("section_heading") or "").strip()

    if citation_type == "historical" and not section_claim:
        section_claim = "Incident summary"

    if not authoritative_heading:
        return section_claim, bool(section_claim)

    if not section_claim:
        return authoritative_heading, True

    if _section_claim_matches_hit(section_claim, match):
        return section_claim, True

    if prefer_authoritative:
        return authoritative_heading, True

    return section_claim, False


def _raw_excerpt_matches_hit(item: dict, hit: dict | None) -> bool:
    if not hit:
        return False

    raw_excerpt = _clean_excerpt_text(
        item.get("text_excerpt") or item.get("quote") or item.get("relevance") or ""
    )
    if len(raw_excerpt) < 12:
        return False

    return raw_excerpt.lower() in _clean_excerpt_text(hit.get("text", "")).lower()


def _build_citation_excerpt(item: dict, match: dict | None) -> str:
    raw_excerpt = _clean_excerpt_text(
        item.get("text_excerpt") or item.get("quote") or item.get("relevance") or ""
    )
    match_text = _clean_excerpt_text((match or {}).get("text", ""))

    if raw_excerpt and len(raw_excerpt) >= 120:
        return _trim_excerpt(raw_excerpt)

    if match_text:
        if raw_excerpt and len(raw_excerpt) >= 12:
            anchor_idx = match_text.lower().find(raw_excerpt.lower())
            if anchor_idx >= 0:
                return _excerpt_window(match_text, anchor_idx, len(raw_excerpt))
        return _trim_excerpt(match_text)

    if raw_excerpt:
        return _trim_excerpt(raw_excerpt)

    return ""


def _clean_excerpt_text(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text


def _trim_excerpt(text: str, max_chars: int = 300, min_break: int = 180) -> str:
    clean = _clean_excerpt_text(text)
    if len(clean) <= max_chars:
        return clean

    cut = clean[: max_chars + 1]
    for marker in (". ", "; ", ": ", ", ", " "):
        boundary = cut.rfind(marker)
        if boundary >= min_break:
            snippet = cut[: boundary + (1 if marker == " " else len(marker) - 1)].rstrip(" ,;:")
            return f"{snippet}..."

    return f"{clean[:max_chars].rstrip()}..."


def _excerpt_window(text: str, anchor_idx: int, anchor_len: int, radius: int = 120) -> str:
    start = max(0, anchor_idx - radius)
    end = min(len(text), anchor_idx + anchor_len + radius)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = f"...{snippet}"
    if end < len(text):
        snippet = f"{snippet}..."
    return _trim_excerpt(snippet)


def _targeted_section_lookup(
    document_id: str,
    section_claim: str,
    index_name: str,
) -> dict | None:
    """Search for a specific section within a known document.

    Used when _find_matching_hit resolved the document but matched the wrong
    section (e.g. §6.1 instead of claimed §6.3).  We re-query the index with a
    ``document_id`` OData filter so Azure AI Search only returns chunks from
    the correct document, then pick the chunk whose section_key matches the
    claim.
    """
    if not SEARCH_ENABLED:
        return None
    section_key = _normalize_section_key(section_claim)
    query = f"section {section_claim} {section_key}"
    try:
        safe_id = document_id.replace("'", "''")
        hits = search_index(
            index_name,
            query,
            top_k=10,
            filter_expr=f"document_id eq '{safe_id}'",
        )
    except Exception:
        return None
    for hit in hits:
        hit_key = _normalize_section_key(hit.get("section_key") or hit.get("section_heading") or "")
        if hit_key == section_key:
            return hit
    return None


def _resolve_section_mismatch_citations(citations: list[dict]) -> None:
    """Fix citations that are unresolved only because of section mismatch.

    Mutates citations in-place.  For each ``unresolved`` citation whose reason
    is "Missing authoritative section match" and that already has a real
    document_id + index_name, attempt a targeted lookup to find the correct
    section chunk and upgrade the citation to resolved.
    """
    for citation in citations:
        if citation.get("resolution_status") != "unresolved":
            continue
        reason = str(citation.get("unresolved_reason") or "")
        if "authoritative section match" not in reason:
            continue
        document_id = str(citation.get("document_id") or "").strip()
        index_name = str(citation.get("index_name") or "").strip()
        section_claim = str(citation.get("section") or "").strip()
        if not document_id or not index_name or not section_claim:
            continue
        hit = _targeted_section_lookup(document_id, section_claim, index_name)
        if not hit:
            continue
        # Upgrade to resolved with the correct section metadata
        citation["section_heading"] = hit.get("section_heading") or citation["section_heading"]
        citation["section_key"] = hit.get("section_key") or citation["section_key"]
        citation["section_path"] = hit.get("section_path") or citation["section_path"]
        citation["chunk_index"] = hit.get("chunk_index", citation.get("chunk_index"))
        if not citation.get("text_excerpt") and hit.get("text"):
            citation["text_excerpt"] = _trim_excerpt(hit["text"])
        citation["resolution_status"] = "resolved"
        citation["unresolved_reason"] = ""


def _deduplicate_ghost_citations(citations: list[dict]) -> list[dict]:
    """Remove ghost (unresolvable) citations when a real citation covers the same section.

    A ghost citation has no document_id and a generic source label (e.g.
    ``source="gmp"``).  If a real citation exists with the same type and the
    same section_key claim, the ghost is a redundant AI hallucination artifact
    and should be dropped.
    """
    # Build a set of (type, section_key) for citations that have a real document
    real_keys: set[tuple[str, str]] = set()
    for c in citations:
        if str(c.get("document_id") or "").strip():
            c_type = str(c.get("type") or "").strip()
            # Use original section claim normalised, not the matched section_key
            # which may have been overwritten to the wrong section.
            c_section = _normalize_section_key(str(c.get("section") or c.get("section_key") or ""))
            if c_type and c_section:
                real_keys.add((c_type, c_section))

    result: list[dict] = []
    for c in citations:
        doc_id = str(c.get("document_id") or "").strip()
        source = str(c.get("source") or "").strip()
        if not doc_id and _is_generic_reference_label(source):
            c_type = str(c.get("type") or "").strip()
            c_section = "" if _should_suppress_unverified_section(c) else _normalize_section_key(
                str(c.get("section") or c.get("section_key") or "")
            )
            if (c_type, c_section) in real_keys:
                # Ghost citation — already covered by a real document citation
                continue
        result.append(c)
    return result


def _classify_citation_resolution(
    *,
    citation_type: str,
    document_title: str,
    section: str,
    section_verified: bool,
    authoritative_section_available: bool,
    text_excerpt: str,
    url: str,
    container: str,
    source_blob: str,
) -> tuple[str, str]:
    missing: list[str] = []

    if not document_title:
        missing.append("document title")
    if not section:
        missing.append("section")
    elif authoritative_section_available and not section_verified:
        missing.append("authoritative section match")
    if not text_excerpt:
        missing.append("excerpt")
    if not url and not (container and source_blob):
        missing.append("link")

    if not missing:
        return "resolved", ""

    reason = f"Missing {', '.join(missing)} for {citation_type or 'evidence'} citation"
    return "unresolved", reason


def _citation_url(*, citation_type: str, document_id: str, container: str, source_blob: str) -> str:
    if citation_type == "incident":
        # For primary incident citations, document_id is the incident ID
        if document_id:
            return f"/incidents/{quote(document_id, safe='')}"
        return ""
    if citation_type == "historical":
        incident_id = _extract_historical_incident_id(document_id or source_blob)
        if incident_id:
            return f"/incidents/{quote(incident_id, safe='')}"
        return ""
    return _document_url(container, source_blob)


def _extract_historical_incident_id(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    stem = Path(text).stem
    match = re.search(r"(INC-\d{4}-\d{4,})", stem, re.IGNORECASE)
    return match.group(1).upper() if match else ""


def _find_matching_hit(item: dict, flat_hits: list[dict]) -> dict | None:
    candidates = [
        str(item.get("document_id") or "").strip(),
        str(item.get("id") or "").strip(),
        str(item.get("document_title") or "").strip(),
        str(item.get("title") or "").strip(),
        str(item.get("regulation") or "").strip(),
        str(item.get("reference") or "").strip(),
        str(item.get("source") or "").strip(),
        str(item.get("source_blob") or "").strip(),
    ]
    section_claim = str(item.get("section") or item.get("relevant_section") or "").strip()
    excerpt = _clean_excerpt_text(item.get("text_excerpt") or item.get("quote") or "")

    best_hit: dict | None = None
    best_score = 0

    for hit in flat_hits:
        score = _document_match_score(candidates, hit)
        if excerpt:
            score += _excerpt_match_score(excerpt, hit)
        if section_claim:
            score += _section_match_score(section_claim, hit)

        if score > best_score:
            best_score = score
            best_hit = hit

    return best_hit if best_score > 0 else None


def _document_match_score(candidates: list[str], hit: dict) -> int:
    hit_values = [
        str(hit.get("document_id") or "").strip(),
        str(hit.get("document_title") or "").strip(),
        str(hit.get("source") or "").strip(),
        str(hit.get("document_type") or "").strip(),
    ]

    best = 0
    for candidate in candidates:
        candidate_lower = candidate.lower()
        if not candidate_lower:
            continue
        for hit_value in hit_values:
            hit_lower = hit_value.lower()
            if not hit_lower:
                continue
            if candidate_lower == hit_lower:
                best = max(best, 100)
            elif len(candidate_lower) >= 6 and (
                candidate_lower in hit_lower or hit_lower in candidate_lower
            ):
                best = max(best, 70)
    return best


def _excerpt_match_score(excerpt: str, hit: dict) -> int:
    normalized_excerpt = _clean_excerpt_text(excerpt)
    if len(normalized_excerpt) < 12:
        return 0

    hit_text = _clean_excerpt_text(hit.get("text", ""))
    return 60 if normalized_excerpt.lower() in hit_text.lower() else 0


def _section_match_score(section_claim: str, hit: dict) -> int:
    return 40 if _section_claim_matches_hit(section_claim, hit) else 0


def _infer_citation_type(item: dict, match: dict | None) -> str:
    text = " ".join(
        str(item.get(k, ""))
        for k in ("source", "reference", "document_title", "title", "regulation")
    ).lower()
    if match and match.get("type"):
        return match["type"]
    if "sop" in text:
        return "sop"
    if "gmp" in text or "annex" in text or "21 cfr" in text:
        return "gmp"
    if "manual" in text or "equipment" in text:
        return "manual"
    if "bpr" in text or "batch" in text:
        return "bpr"
    if "incident" in text or text.startswith("inc-"):
        return "historical"
    return "document"


def _document_url(container: str, source_blob: str) -> str:
    if not container or not source_blob:
        return ""
    return f"/api/documents/{container}/{quote(source_blob, safe='/')}"


def _infer_known_document(item: dict) -> dict | None:
    # HACKATHON ONLY — hardcoded fallback for mock documents whose metadata may not
    # be fully populated in the search index during the demo.
    # PRODUCTION NOTE: remove this function; the search index must be the sole source
    # of document metadata. If a document isn't matched via _find_matching_hit, the
    # root cause is missing/incomplete index data, not a missing code mapping.
    if os.getenv("KNOWN_DOCUMENT_FALLBACK_DISABLED", "").strip().lower() in {"1", "true", "yes"}:
        return None
    text = " ".join(
        str(item.get(k, ""))
        for k in ("document_id", "document_title", "reference", "source", "text_excerpt", "id", "title", "regulation")
    ).lower()
    if "sop-dev-001" in text:
        return {
            "document_id": "SOP-DEV-001",
            "container": "blob-sop",
            "source_blob": "SOP-DEV-001-Deviation-Management.md",
            "document_title": "Deviation Management (SOP-DEV-001)",
        }
    if "sop-man-gr-001" in text or "granulator operation" in text:
        return {
            "document_id": "SOP-MAN-GR-001",
            "container": "blob-sop",
            "source_blob": "SOP-MAN-GR-001-Granulator-Operation.md",
            "document_title": "Granulator Operation (SOP-MAN-GR-001)",
        }
    if "annex 15" in text or "eu gmp" in text:
        return {
            "document_id": "GMP-Annex15-Excerpt",
            "container": "blob-gmp",
            "source_blob": "GMP-Annex15-Excerpt.md",
            "document_title": "EU GMP Annex 15",
        }
    if "metformin" in text or "b26041701" in text:
        return {
            "document_id": "BPR-MET-500-v3.2",
            "container": "blob-bpr",
            "source_blob": "BPR-MET-500-v3.2-Process-Specification.md",
            "document_title": "BPR Metformin 500mg Process Specification",
        }
    return None


def _write_analysis_started_event(incident_id: str, more_info_round: int = 0) -> None:
    """Write an analysis_started audit event when the AI agent begins processing.

    Uses a stable, round-aware id so durable activity replays/retries hit the
    CosmosResourceExistsError branch instead of writing duplicate history rows.
    """
    from azure.cosmos.exceptions import CosmosResourceExistsError
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    event = {
        "id": f"{incident_id}-analysis-started-r{more_info_round}",
        "incident_id": incident_id,
        "incidentId": incident_id,
        "timestamp": now,
        "action": "analysis_started",
        "actor": "AI Orchestrator",
        "actor_type": "agent",
        "category": "status",
        "details": "AI agent started analyzing the incident — researching SOPs, equipment history and GMP guidelines.",
    }
    try:
        container = get_container("incident_events")
        container.create_item(event, enable_automatic_id_generation=False)
    except CosmosResourceExistsError:
        pass  # idempotent on orchestrator replay
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not write analysis_started event for %s: %s", incident_id, exc)


def _write_analysis_queued_event(incident_id: str, more_info_round: int = 0) -> None:
    """Write an idempotent audit event when the incident enters the Foundry queue."""
    from azure.cosmos.exceptions import CosmosResourceExistsError
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    event = {
        "id": f"{incident_id}-analysis-queued-r{more_info_round}",
        "incident_id": incident_id,
        "incidentId": incident_id,
        "timestamp": now,
        "action": "analysis_queued",
        "actor": "AI Orchestrator",
        "actor_type": "agent",
        "category": "status",
        "details": "Incident queued for AI analysis; waiting for an available Foundry analyzer slot.",
    }
    try:
        container = get_container("incident_events")
        container.create_item(event, enable_automatic_id_generation=False)
    except CosmosResourceExistsError:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not write analysis_queued event for %s: %s", incident_id, exc)


def _mark_incident_queued_for_analysis(incident_id: str, more_info_round: int) -> None:
    """Persist the transition to 'queued_for_analysis' before entering the Foundry gate.

    This lets the UI distinguish between incidents waiting for a Foundry concurrency
    slot ('queued_for_analysis') and those actively running in Foundry ('analyzing').
    """
    db = get_cosmos_client().get_database_client(DB_NAME)
    incident = get_incident_by_id(db, incident_id)
    previous_status = str(incident.get("status") or "").strip() or None
    workflow_state = incident.get("workflow_state") or {}
    now_iso = datetime.now(timezone.utc).isoformat()

    patch_incident_by_id(
        db,
        incident_id,
        [
            {"op": "set", "path": "/status", "value": "queued_for_analysis"},
            {
                "op": "set",
                "path": "/workflow_state",
                "value": {
                    **workflow_state,
                    "durable_instance_id": f"durable-{incident_id}",
                    "current_step": (
                        "queued_for_analysis_followup"
                        if more_info_round > 0
                        else "queued_for_analysis"
                    ),
                },
            },
            {"op": "set", "path": "/updatedAt", "value": now_iso},
            {"op": "set", "path": "/updated_at", "value": now_iso},
        ],
    )

    if previous_status != "queued_for_analysis":
        try:
            notify_incident_status_changed_sync(
                incident_id=incident_id,
                new_status="queued_for_analysis",
                previous_status=previous_status,
                equipment_id=str(
                    incident.get("equipment_id") or incident.get("equipmentId") or ""
                ),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Could not push queued_for_analysis status change for %s: %s",
                incident_id,
                exc,
            )


def _mark_incident_analyzing(incident_id: str, more_info_round: int) -> None:
    """Persist the transition to active AI analysis for initial and follow-up runs."""
    db = get_cosmos_client().get_database_client(DB_NAME)
    incident = get_incident_by_id(db, incident_id)
    previous_status = str(incident.get("status") or "").strip() or None
    workflow_state = incident.get("workflow_state") or {}

    now_iso = datetime.now(timezone.utc).isoformat()
    patch_incident_by_id(
        db,
        incident_id,
        [
            {"op": "set", "path": "/status", "value": "analyzing"},
            {
                "op": "set",
                "path": "/workflow_state",
                "value": {
                    **workflow_state,
                    "durable_instance_id": f"durable-{incident_id}",
                    "current_step": "analyzing_followup" if more_info_round > 0 else "analyzing",
                },
            },
            {"op": "set", "path": "/updatedAt", "value": now_iso},
            {"op": "set", "path": "/updated_at", "value": now_iso},
        ],
    )

    if previous_status != "analyzing":
        try:
            notify_incident_status_changed_sync(
                incident_id=incident_id,
                new_status="analyzing",
                previous_status=previous_status,
                equipment_id=str(incident.get("equipment_id") or incident.get("equipmentId") or ""),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Could not push analyzing status change for %s: %s",
                incident_id,
                exc,
            )
