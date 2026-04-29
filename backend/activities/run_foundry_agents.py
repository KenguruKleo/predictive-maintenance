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

DEFAULT_RESEARCH_AGENT_MODEL = "gpt-4o"
DEFAULT_EVIDENCE_SYNTHESIZER_AGENT_MODEL = "gpt-4o"
DEFAULT_DOCUMENT_AGENT_MODEL = "gpt-4o"
DEFAULT_ORCHESTRATOR_AGENT_MODEL = "gpt-4o"
EVIDENCE_SYNTHESIZER_AGENT_NAME = "sentinel-evidence-synthesizer-agent"

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

    research_package, rag_context = _collect_research_evidence_package(
        context_data,
        current_incident_id=incident_id,
    )

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

    evidence_synthesizer_agent_id = _resolve_optional_foundry_agent_id(
        "EVIDENCE_SYNTHESIZER_AGENT_ID",
        EVIDENCE_SYNTHESIZER_AGENT_NAME,
    )
    research_package = _add_evidence_synthesis(
        research_package,
        evidence_synthesizer_agent_id,
        incident_id=incident_id,
        more_info_round=more_info_round,
        context_data=context_data,
    )
    orchestrator_research_package = _build_orchestrator_research_package(research_package)

    prompt = _build_prompt(
        incident_id,
        context_data,
        more_info_round,
        previous_ai_result,
        research_package=orchestrator_research_package,
    )
    _log_orchestrator_prompt_trace(
        incident_id=incident_id,
        more_info_round=more_info_round,
        orchestrator_agent_id=orchestrator_agent_id,
        evidence_synthesizer_agent_id=evidence_synthesizer_agent_id,
        prompt=prompt,
        context_data=context_data,
    )
    try:
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

        result = _normalize_agent_result(
            result,
            rag_context,
            more_info_round,
            previous_ai_result=previous_ai_result,
            operator_questions=context_data.get("operator_questions", []),
            authoritative_research_package=research_package,
        )
        result, applied_synthesized_dialogue = _apply_synthesized_operator_dialogue(
            result,
            research_package,
            incident_id=incident_id,
            more_info_round=more_info_round,
        )
        if not applied_synthesized_dialogue:
            result = _revise_followup_operator_dialogue_with_model(
                result,
                orchestrator_agent_id,
                incident_id=incident_id,
                more_info_round=more_info_round,
                context_data=context_data,
                research_package=research_package,
                previous_ai_result=previous_ai_result,
            )
    finally:
        # Always release the Foundry slot so the next waiting incident can proceed.
        _set_foundry_active(_incidents_container, incident_id, _equipment_id, False)

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
    trace_label: str = "orchestrator",
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
                        "model": trace_label,
                    }
                _log_trace_json(
                    incident_id=incident_id,
                    more_info_round=more_info_round,
                    trace_kind=_agent_trace_kind("thread_messages", trace_label),
                    payload={
                        "thread_id": run.thread_id,
                        "run_id": run.id,
                        "status": str(run.status),
                        "usage": _usage_payload or None,
                        "messages": _serialize_thread_messages(message_items),
                    },
                    metadata={"agent_id": agent_id, "agent_name": trace_label},
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
                    trace_kind=_agent_trace_kind("raw_response", trace_label),
                    text=raw_text,
                    metadata={
                        "thread_id": run.thread_id,
                        "run_id": run.id,
                        "agent_id": agent_id,
                        "agent_name": trace_label,
                    },
                )
                parsed = _parse_response(raw_text)
                _log_trace_json(
                    incident_id=incident_id,
                    more_info_round=more_info_round,
                    trace_kind=_agent_trace_kind("parsed_response", trace_label),
                    payload=parsed,
                    metadata={
                        "thread_id": run.thread_id,
                        "run_id": run.id,
                        "agent_id": agent_id,
                        "agent_name": trace_label,
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


def _agent_trace_kind(base_kind: str, trace_label: str) -> str:
    if trace_label == "orchestrator":
        return base_kind
    return f"{trace_label}_{base_kind}"


def _add_evidence_synthesis(
    research_package: dict,
    agent_id: str,
    *,
    incident_id: str,
    more_info_round: int,
    context_data: dict,
) -> dict:
    if not agent_id:
        return research_package

    operator_questions = context_data.get("operator_questions", [])
    latest_operator_question = _get_latest_operator_question(operator_questions)
    synthesis_prompt = _build_evidence_synthesis_prompt(
        incident_id=incident_id,
        latest_operator_question=latest_operator_question,
        research_package=research_package,
    )
    _log_trace_text(
        incident_id=incident_id,
        more_info_round=more_info_round,
        trace_kind="evidence_synthesizer_prompt",
        text=synthesis_prompt,
        metadata={"agent_id": agent_id, "agent_name": "evidence_synthesizer"},
    )

    try:
        raw_synthesis = _call_orchestrator_agent(
            synthesis_prompt,
            agent_id,
            incident_id=incident_id,
            more_info_round=more_info_round,
            trace_label="evidence_synthesizer",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Evidence synthesis failed for incident %s round=%d: %s",
            incident_id,
            more_info_round,
            exc,
            exc_info=True,
        )
        return research_package

    synthesis = _normalize_evidence_synthesis(raw_synthesis, latest_operator_question)
    if not synthesis:
        return research_package

    updated = dict(research_package)
    updated["evidence_synthesis"] = synthesis
    _log_trace_json(
        incident_id=incident_id,
        more_info_round=more_info_round,
        trace_kind="evidence_synthesis_result",
        payload=synthesis,
        metadata={"agent_id": agent_id, "agent_name": "evidence_synthesizer"},
    )
    return updated


def _build_evidence_synthesis_prompt(
    *,
    incident_id: str,
    latest_operator_question: str,
    research_package: dict,
) -> str:
    synthesis_evidence = _compact_evidence_for_synthesis(research_package)
    question = latest_operator_question or "No operator follow-up question. Summarize evidence for the initial decision."
    return "\n".join(
        [
            f"## Evidence Synthesis Request - Incident {incident_id}",
            "Use only the provided evidence package excerpt. Do not call tools or use model memory.",
            "Return one JSON object matching your configured response schema.",
            "",
            "### Latest Operator Question",
            question,
            "",
            "### Evidence Package Excerpt",
            "```json",
            json.dumps(synthesis_evidence, indent=2, default=str),
            "```",
            "",
            "### Synthesis Requirements",
            "- Produce a compact evidence brief for the Orchestrator and operator-facing follow-up answer.",
            "- Answer the latest question first when there is one.",
            "- Distinguish explicit support from unknown or missing facts.",
            "- For count/comparison questions, report checked evidence count, explicit support count, contradiction count, and unknown count.",
            "- Do not infer that an action did not happen merely because an excerpt does not mention it.",
            "- Negative support also requires explicit evidence; omission means unknown, not proof.",
            "- Use `all`, `most`, or `none` only with numbers that support the comparison.",
            "- If requested facts are absent or ambiguous, say the count is not determinable from retrieved evidence.",
            "- Do not make the final GMP approval/rejection decision; provide only a decision impact hint.",
            "- Keep `operator_dialogue` under 120 words.",
            "- Return the data object itself, not JSON Schema. Do not include `type`, `properties`, `required`, or `additionalProperties`.",
            "",
            "Return JSON only.",
        ]
    )


def _compact_evidence_for_synthesis(research_package: dict) -> dict:
    return _pick_present(
        {
            "follow_up_context": research_package.get("follow_up_context"),
            "incident_facts": research_package.get("incident_facts"),
            "equipment_facts": research_package.get("equipment_facts"),
            "batch_facts": research_package.get("batch_facts"),
            "bpr_constraints": _compact_prompt_mapping(research_package.get("bpr_constraints")),
            "historical_incidents": _compact_historical_for_prompt(
                research_package.get("historical_incidents"),
                limit=8,
            ),
            "historical_pattern_summary": research_package.get("historical_pattern_summary"),
            "evidence_citations": _compact_citations_for_prompt(
                research_package.get("evidence_citations"),
                limit=16,
            ),
            "evidence_gaps": research_package.get("evidence_gaps"),
            "context_summary": research_package.get("context_summary"),
        },
        [
            "follow_up_context",
            "incident_facts",
            "equipment_facts",
            "batch_facts",
            "bpr_constraints",
            "historical_incidents",
            "historical_pattern_summary",
            "evidence_citations",
            "evidence_gaps",
            "context_summary",
        ],
    )


def _build_orchestrator_research_package(research_package: dict) -> dict:
    if not isinstance(research_package.get("evidence_synthesis"), dict):
        return research_package

    return _pick_present(
        {
            "evidence_synthesis": research_package.get("evidence_synthesis"),
            "follow_up_context": research_package.get("follow_up_context"),
            "incident_facts": research_package.get("incident_facts"),
            "equipment_facts": research_package.get("equipment_facts"),
            "batch_facts": research_package.get("batch_facts"),
            "bpr_constraints": _compact_prompt_mapping(research_package.get("bpr_constraints")),
            "historical_incidents": _compact_historical_for_prompt(
                research_package.get("historical_incidents"),
                limit=8,
            ),
            "historical_pattern_summary": research_package.get("historical_pattern_summary"),
            "evidence_citations": _compact_citations_for_prompt(
                research_package.get("evidence_citations"),
                limit=16,
            ),
            "evidence_gaps": research_package.get("evidence_gaps"),
            "context_summary": research_package.get("context_summary"),
        },
        [
            "evidence_synthesis",
            "follow_up_context",
            "incident_facts",
            "equipment_facts",
            "batch_facts",
            "bpr_constraints",
            "historical_incidents",
            "historical_pattern_summary",
            "evidence_citations",
            "evidence_gaps",
            "context_summary",
        ],
    )


def _compact_prompt_mapping(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    return _pick_present(
        value,
        [
            "type",
            "document_id",
            "document_title",
            "section_heading",
            "section",
            "text_excerpt",
            "source_blob",
            "index_name",
            "url",
        ],
    )


def _compact_historical_for_prompt(value: object, *, limit: int) -> list[dict]:
    if not isinstance(value, list):
        return []
    compact: list[dict] = []
    for item in value[:limit]:
        if not isinstance(item, dict):
            continue
        compact.append(
            _pick_present(
                {
                    "incident_id": item.get("incident_id"),
                    "document_title": item.get("document_title"),
                    "status": item.get("status"),
                    "human_decision": item.get("human_decision"),
                    "decision_evidence": item.get("decision_evidence"),
                    "evidence_excerpt": item.get("evidence_excerpt"),
                    "source_url": item.get("source_url"),
                },
                [
                    "incident_id",
                    "document_title",
                    "status",
                    "human_decision",
                    "decision_evidence",
                    "evidence_excerpt",
                    "source_url",
                ],
            )
        )
    return compact


def _compact_citations_for_prompt(value: object, *, limit: int) -> list[dict]:
    if not isinstance(value, list):
        return []
    compact: list[dict] = []
    for item in value[:limit]:
        if not isinstance(item, dict):
            continue
        compact.append(
            _pick_present(
                {
                    "type": item.get("type"),
                    "document_id": item.get("document_id"),
                    "document_title": item.get("document_title"),
                    "section_heading": item.get("section_heading"),
                    "text_excerpt": item.get("text_excerpt"),
                    "source_blob": item.get("source_blob"),
                    "index_name": item.get("index_name"),
                    "url": item.get("url"),
                },
                [
                    "type",
                    "document_id",
                    "document_title",
                    "section_heading",
                    "text_excerpt",
                    "source_blob",
                    "index_name",
                    "url",
                ],
            )
        )
    return compact


def _normalize_evidence_synthesis(raw_synthesis: dict, latest_operator_question: str) -> dict:
    if not isinstance(raw_synthesis, dict):
        return {}
    if isinstance(raw_synthesis.get("properties"), dict):
        raw_synthesis = raw_synthesis["properties"]

    def _as_int(value: object) -> int:
        if value in (None, ""):
            return 0
        if not isinstance(value, int | float | str):
            return 0
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    supporting_evidence = raw_synthesis.get("supporting_evidence")
    if not isinstance(supporting_evidence, list):
        supporting_evidence = []
    evidence_gaps = raw_synthesis.get("evidence_gaps")
    if not isinstance(evidence_gaps, list):
        evidence_gaps = []

    answerability = str(raw_synthesis.get("answerability") or "not_determinable").strip()
    if answerability not in {"answered", "partially_answered", "not_determinable", "not_applicable"}:
        answerability = "not_determinable"

    return {
        "latest_question": str(raw_synthesis.get("latest_question") or latest_operator_question or "").strip(),
        "question_focus": str(raw_synthesis.get("question_focus") or "").strip(),
        "answerability": answerability,
        "direct_answer": str(raw_synthesis.get("direct_answer") or "").strip(),
        "operator_dialogue": str(raw_synthesis.get("operator_dialogue") or "").strip(),
        "checked_evidence_count": _as_int(raw_synthesis.get("checked_evidence_count")),
        "explicit_support_count": _as_int(raw_synthesis.get("explicit_support_count")),
        "contradiction_count": _as_int(raw_synthesis.get("contradiction_count")),
        "unknown_count": _as_int(raw_synthesis.get("unknown_count")),
        "supporting_evidence": [item for item in supporting_evidence if isinstance(item, dict)],
        "evidence_gaps": [str(item) for item in evidence_gaps if str(item).strip()],
        "decision_impact_hint": str(raw_synthesis.get("decision_impact_hint") or "").strip(),
        "reasoning_summary": str(raw_synthesis.get("reasoning_summary") or "").strip(),
    }


def _apply_synthesized_operator_dialogue(
    result: dict,
    research_package: dict,
    *,
    incident_id: str,
    more_info_round: int,
) -> tuple[dict, bool]:
    if more_info_round <= 0:
        return result, False

    synthesis = research_package.get("evidence_synthesis")
    if not isinstance(synthesis, dict):
        return result, False

    dialogue = str(synthesis.get("operator_dialogue") or "").strip()
    if not dialogue:
        return result, False

    updated = dict(result)
    updated["operator_dialogue"] = dialogue[:800]
    _log_trace_json(
        incident_id=incident_id,
        more_info_round=more_info_round,
        trace_kind="operator_dialogue_synthesis_result",
        payload={
            "previous_operator_dialogue": result.get("operator_dialogue"),
            "synthesized_operator_dialogue": updated["operator_dialogue"],
            "answerability": synthesis.get("answerability"),
            "checked_evidence_count": synthesis.get("checked_evidence_count"),
            "explicit_support_count": synthesis.get("explicit_support_count"),
            "unknown_count": synthesis.get("unknown_count"),
        },
        metadata={"agent_name": "evidence_synthesizer"},
    )
    return updated, True


def _revise_followup_operator_dialogue_with_model(
    result: dict,
    agent_id: str,
    *,
    incident_id: str,
    more_info_round: int,
    context_data: dict,
    research_package: dict,
    previous_ai_result: dict | None,
) -> dict:
    if more_info_round <= 0:
        return result
    if str(result.get("confidence_flag") or "") in {"FOUNDRY_FAILURE", "FOUNDRY_TIMEOUT"}:
        return result

    operator_questions = context_data.get("operator_questions", [])
    latest_operator_question = _get_latest_operator_question(operator_questions)
    if not latest_operator_question:
        return result

    revision_prompt = _build_operator_dialogue_revision_prompt(
        incident_id=incident_id,
        latest_operator_question=latest_operator_question,
        result=result,
        research_package=research_package,
        previous_ai_result=previous_ai_result or {},
    )
    _log_trace_text(
        incident_id=incident_id,
        more_info_round=more_info_round,
        trace_kind="operator_dialogue_revision_prompt",
        text=revision_prompt,
        metadata={"agent_id": agent_id},
    )

    try:
        revised = _call_orchestrator_agent(
            revision_prompt,
            agent_id,
            incident_id=incident_id,
            more_info_round=more_info_round,
            trace_label="operator_dialogue_revision",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Operator dialogue revision failed for incident %s round=%d: %s",
            incident_id,
            more_info_round,
            exc,
            exc_info=True,
        )
        return result

    revised_dialogue = str(revised.get("operator_dialogue") or "").strip()
    if not revised_dialogue:
        return result

    updated = dict(result)
    updated["operator_dialogue"] = revised_dialogue[:800]
    _log_trace_json(
        incident_id=incident_id,
        more_info_round=more_info_round,
        trace_kind="operator_dialogue_revision_result",
        payload={
            "previous_operator_dialogue": result.get("operator_dialogue"),
            "revised_operator_dialogue": updated["operator_dialogue"],
        },
    )
    return updated


def _build_operator_dialogue_revision_prompt(
    *,
    incident_id: str,
    latest_operator_question: str,
    result: dict,
    research_package: dict,
    previous_ai_result: dict,
) -> str:
    previous_snapshot = _pick_present(
        {
            "recommendation": previous_ai_result.get("recommendation"),
            "root_cause": previous_ai_result.get("root_cause"),
            "risk_level": previous_ai_result.get("risk_level"),
            "batch_disposition": previous_ai_result.get("batch_disposition"),
        },
        ["recommendation", "root_cause", "risk_level", "batch_disposition"],
    )
    decision_summary = _pick_present(
        {
            "incident_id": result.get("incident_id"),
            "title": result.get("title"),
            "classification": result.get("classification"),
            "risk_level": result.get("risk_level"),
            "confidence": result.get("confidence"),
            "confidence_flag": result.get("confidence_flag"),
            "root_cause": result.get("root_cause"),
            "analysis": result.get("analysis"),
            "recommendation": result.get("recommendation"),
            "agent_recommendation": result.get("agent_recommendation"),
            "agent_recommendation_rationale": result.get("agent_recommendation_rationale"),
            "batch_disposition": result.get("batch_disposition"),
            "current_operator_dialogue": result.get("operator_dialogue"),
        },
        [
            "incident_id",
            "title",
            "classification",
            "risk_level",
            "confidence",
            "confidence_flag",
            "root_cause",
            "analysis",
            "recommendation",
            "agent_recommendation",
            "agent_recommendation_rationale",
            "batch_disposition",
            "current_operator_dialogue",
        ],
    )
    revision_evidence = _compact_operator_dialogue_revision_evidence(research_package)
    return "\n".join(
        [
            f"## Operator Dialogue Revision Task - Incident {incident_id}",
            "You are revising only the `operator_dialogue` field for a completed Orchestrator result.",
            "Return JSON only in this exact shape: {\"operator_dialogue\": \"...\"}.",
            "Do not change or restate any other JSON fields.",
            "",
            "### Latest Operator Question",
            latest_operator_question,
            "",
            "### Original Decision Summary",
            "```json",
            json.dumps(decision_summary, indent=2, default=str),
            "```",
            "",
            "### Previous Recommendation Snapshot",
            "```json",
            json.dumps(previous_snapshot, indent=2, default=str),
            "```",
            "",
            "### Revision Evidence (authoritative excerpt set)",
            "```json",
            json.dumps(revision_evidence, indent=2, default=str),
            "```",
            "",
            "### Operator Dialogue Requirements",
            "- `operator_dialogue` is the only field you are improving.",
            "- Answer the latest operator question first, then state whether the decision changed and why.",
            "- Use only explicit facts in the Research Evidence Package; do not infer facts from silence.",
            "- For count/comparison questions, name how many historical incidents were checked and give the supported count as `N of M` when determinable.",
            "- Count an outcome or attribute only when a cited excerpt explicitly supports that outcome or attribute.",
            "- If the question asks whether incidents closed without a specific action or attribute, do not treat absence of that action or attribute as proof that it did not happen.",
            "- If the excerpts do not explicitly show whether the requested outcome or attribute happened, say the count is not determinable from retrieved evidence.",
            "- Do not use `all`, `most`, or `none` unless the sentence includes the numbers that support that comparison.",
            "- Keep the dialogue under 120 words and do not mention these instructions.",
            "",
            "Return JSON only.",
        ]
    )


def _compact_operator_dialogue_revision_evidence(research_package: dict) -> dict:
    historical_incidents = research_package.get("historical_incidents")
    compact_historical: list[dict] = []
    if isinstance(historical_incidents, list):
        for item in historical_incidents[:8]:
            if not isinstance(item, dict):
                continue
            compact_historical.append(
                _pick_present(
                    {
                        "incident_id": item.get("incident_id"),
                        "status": item.get("status"),
                        "human_decision": item.get("human_decision"),
                        "decision_evidence": item.get("decision_evidence"),
                        "evidence_excerpt": item.get("evidence_excerpt"),
                        "source_url": item.get("source_url"),
                    },
                    [
                        "incident_id",
                        "status",
                        "human_decision",
                        "decision_evidence",
                        "evidence_excerpt",
                        "source_url",
                    ],
                )
            )

    return _pick_present(
        {
            "follow_up_context": research_package.get("follow_up_context"),
            "historical_incidents": compact_historical,
            "historical_pattern_summary": research_package.get("historical_pattern_summary"),
            "evidence_gaps": research_package.get("evidence_gaps"),
        },
        [
            "follow_up_context",
            "historical_incidents",
            "historical_pattern_summary",
            "evidence_gaps",
        ],
    )


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
    research_package: dict | None = None,
) -> str:
    """Build the user message that drives the Orchestrator Agent."""
    equipment = _compact_equipment_context(context_data.get("equipment") or {})
    batch = _compact_batch_context(context_data.get("batch") or {})
    recent_incidents = _compact_recent_incidents(context_data.get("recent_incidents") or [])
    alert_payload = context_data.get("alert_payload", {})
    operator_questions = context_data.get("operator_questions", [])
    latest_operator_question = _get_latest_operator_question(operator_questions)

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

    if research_package:
        lines += [
            "",
            "### Research Evidence Package (authoritative)",
            "This package was retrieved directly from Sentinel DB/Search before this Orchestrator run.",
            (
                "Use its `evidence_citations` as the source of truth for your reasoning. "
                "When `evidence_synthesis` is present, treat it as the compact model-owned "
                "brief for the latest question and preserve its explicit-support vs unknown distinctions. "
                "The backend will attach the canonical citations and tool log after your decision, "
                "so do not echo the large evidence/tool arrays in your final JSON."
            ),
            "```json",
            json.dumps(research_package, indent=2, default=str),
            "```",
        ]

    if more_info_round > 0 and latest_operator_question:
        lines += [
            "",
            "### Latest Operator Question - Answer Task",
            "Treat this as the primary user intent for `operator_dialogue`.",
            f"Question: {latest_operator_question}",
            "Answer contract for `operator_dialogue`:",
            "- Start by answering the concrete question the operator asked, not by restating the recommendation.",
            "- Use the Research Evidence Package to say what evidence was checked and what it did or did not show.",
            "- When `evidence_synthesis` is present, preserve its checked/support/unknown counts and evidence gaps.",
            "- For count/comparison wording such as 'how many', 'most', or 'similar cases', include explicit supported counts from the evidence.",
            "- Count an outcome or attribute only when cited evidence explicitly supports it; absence of a detail in an excerpt is unknown, not proof it did not happen.",
            "- Do not say 'all', 'most', or 'none' unless the cited evidence supports that exact comparison.",
            "- If the retrieved evidence is insufficient to answer any part, say that explicitly and name the missing fact.",
            "- Then say whether recommendation, root cause, risk, or batch disposition changed or stayed the same, and why.",
            "- Keep the response source-agnostic: work with any future evidence source added to the package.",
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
            "The summaries above are only routing context for your final decision. "
            "Use the Research Evidence Package above as the single source of evidence for SOPs, "
            "equipment manuals, BPR product specs, GMP regulations, and historical incidents. "
            "When `evidence_synthesis` is present, use it to explain the final decision in terms of "
            "explicit support, unknowns, evidence gaps, and decision impact. "
            "When the prompt contains a Research Evidence Package, that package is the Research "
            "output for this run; do not call connected agents or external tools. "
            "Do not simulate tool_calls_log or invent citations from model memory. "
            "When the Research Evidence Package is present, keep the final JSON compact: set "
            "evidence_citations, sop_refs, regulatory_refs, and tool_calls_log to empty arrays. "
            "The backend will carry forward the full canonical package. If the package is absent, "
            "copy only real Research Agent citations/tool calls and preserve canonical fields. "
            "You, the Orchestrator, must produce the final structured analysis and decision. "
            "Draft audit_entry_draft and, for APPROVE only, work_order_draft directly in the final JSON; "
            "leave audit_entry_id and work_order_id null. For source alerts with severity=critical, "
            "keep risk_level=critical when agent_recommendation=APPROVE unless the evidence supports "
            "a REJECT false-positive/no-impact transient."
        ),
        "",
        "Return one JSON object that matches the configured response schema. Required top-level fields: ",
        (
            "incident_id, title, classification, risk_level, confidence, confidence_flag, "
            "root_cause, analysis, recommendation, agent_recommendation, operator_dialogue, "
            "agent_recommendation_rationale, capa_suggestion, regulatory_reference, "
            "batch_disposition, recommendations, regulatory_refs, sop_refs, evidence_citations, "
            "audit_entry_draft, work_order_draft, tool_calls_log, "
            "audit_entry_id, work_order_id. Include execution_error only when a tool/documentation "
            "step fails or returns an error."
        ),
        "When the Research Evidence Package is present, return compact empty arrays for evidence_citations, sop_refs, regulatory_refs, and tool_calls_log; backend normalization restores them. Do not call connected agents or external tools.",
        "If Research Agent did not return real canonical SOP/GMP/BPR/manual/history evidence, lower confidence and explain the evidence gap.",
        "For REJECT decisions, work_order_draft and work_order_id must be null.",
        "Never fabricate data. Cite sources. Keep operator_dialogue under 120 words and answer the latest follow-up question directly before summarizing decision impact.",
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


def _collect_research_evidence_package(
    context_data: dict,
    *,
    current_incident_id: str,
) -> tuple[dict, dict]:
    alert_payload = context_data.get("alert_payload") or {}
    equipment = context_data.get("equipment") or {}
    batch = context_data.get("batch") or {}
    latest_operator_question = _get_latest_operator_question(
        context_data.get("operator_questions") or []
    )
    follow_up_search_terms = re.sub(r"\s+", " ", latest_operator_question).strip()
    if len(follow_up_search_terms) > 240:
        follow_up_search_terms = follow_up_search_terms[:240].rsplit(" ", 1)[0].strip()

    equipment_id = str(
        alert_payload.get("equipment_id")
        or equipment.get("id")
        or equipment.get("equipment_id")
        or ""
    ).strip()
    equipment_name = str(equipment.get("name") or equipment.get("equipment_name") or "").strip()
    equipment_type = str(equipment.get("type") or equipment.get("equipment_type") or "").strip()
    equipment_tags = " ".join(
        str(tag) for tag in (equipment.get("tags") or []) if str(tag).strip()
    )
    parameter = str(alert_payload.get("parameter") or "").strip()
    parameter_terms = parameter.replace("_", " ")
    product = str(
        batch.get("product")
        or batch.get("product_name")
        or alert_payload.get("product")
        or ""
    ).strip()
    stage = str(
        batch.get("stage")
        or batch.get("stage_step")
        or batch.get("production_stage")
        or ""
    ).strip()
    bpr_reference = str(batch.get("bpr_reference") or "").strip()
    lower_limit = alert_payload.get("lower_limit", "")
    upper_limit = alert_payload.get("upper_limit", "")
    measured_value = alert_payload.get("measured_value", "")
    duration_seconds = alert_payload.get("duration_seconds", "")
    deviation_type = str(alert_payload.get("deviation_type") or "").replace("_", " ")
    equipment_terms = " ".join(
        value
        for value in [equipment_id, equipment_name, equipment_type, equipment_tags, stage]
        if value
    )

    eq_filter = None
    if equipment_id:
        safe_equipment_id = equipment_id.replace("'", "''")
        eq_filter = f"equipment_ids/any(e: e eq '{safe_equipment_id}')"
    search_plan = [
        (
            "sentinel_search_search_bpr_documents",
            "idx-bpr-documents",
            " ".join(
                str(value)
                for value in [
                    product,
                    bpr_reference,
                    parameter_terms,
                    stage,
                    "Product NOR Product PAR validated range",
                    lower_limit,
                    upper_limit,
                    follow_up_search_terms,
                ]
                if value not in (None, "")
            ),
            10,
            eq_filter,
        ),
        (
            "sentinel_search_search_sop_documents",
            "idx-sop-documents",
            " ".join(
                str(value)
                for value in [
                    equipment_terms,
                    parameter_terms,
                    deviation_type,
                    "operation GMP deviation investigation SOP",
                    lower_limit,
                    upper_limit,
                    follow_up_search_terms,
                ]
                if value not in (None, "")
            ),
            5,
            None,
        ),
        (
            "sentinel_search_search_gmp_policies",
            "idx-gmp-policies",
            " ".join(
                str(value)
                for value in [
                    deviation_type,
                    parameter_terms,
                    "process parameter excursion documented investigated product quality impact CAPA",
                    duration_seconds,
                    follow_up_search_terms,
                ]
                if value not in (None, "")
            ),
            5,
            None,
        ),
        (
            "sentinel_search_search_equipment_manuals",
            "idx-equipment-manuals",
            " ".join(
                str(value)
                for value in [
                    equipment_terms,
                    parameter_terms,
                    "operational limits troubleshooting maintenance calibration current speed control",
                    measured_value,
                    follow_up_search_terms,
                ]
                if value not in (None, "")
            ),
            5,
            eq_filter,
        ),
        (
            "sentinel_search_search_incident_history",
            "idx-incident-history",
            " ".join(
                str(value)
                for value in [
                    equipment_id,
                    parameter_terms,
                    deviation_type,
                    measured_value,
                    lower_limit,
                    upper_limit,
                    "human decision approved rejected",
                    follow_up_search_terms,
                ]
                if value not in (None, "")
            ),
            5,
            eq_filter,
        ),
    ]

    rag_context: dict[str, list[dict]] = {}
    tool_calls_log: list[dict] = []
    evidence_gaps: list[str] = []

    if not SEARCH_ENABLED:
        evidence_gaps.append("Azure AI Search endpoint is not configured for backend retrieval.")

    for tool_name, index_name, query, top_k, filter_expr in search_plan:
        args = {"query": query, "top_k": top_k}
        if filter_expr:
            args["filter"] = filter_expr
        try:
            hits = search_index(index_name, query, top_k=top_k, filter_expr=filter_expr)
            rag_context[index_name] = hits
            status = "success" if hits else "no_results"
            tool_calls_log.append({"tool": tool_name, "args": args, "status": status, "error": None})
            if not hits:
                evidence_gaps.append(f"No results from {index_name} for query: {query}")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Research evidence search failed for %s: %s", index_name, exc)
            rag_context[index_name] = []
            tool_calls_log.append(
                {"tool": tool_name, "args": args, "status": "error", "error": str(exc)[:300]}
            )
            evidence_gaps.append(f"Search failed for {index_name}: {str(exc)[:160]}")

    per_index_limits = {
        "idx-bpr-documents": 2,
        "idx-sop-documents": 2,
        "idx-gmp-policies": 2,
        "idx-equipment-manuals": 2,
        "idx-incident-history": 3,
    }

    citations: list[dict] = []
    seen_citations: set[tuple[str, str, int]] = set()
    for index_name, hits in rag_context.items():
        scored_hits = [
            (_research_hit_score(hit, alert_payload, batch, equipment), position, hit)
            for position, hit in enumerate(hits)
        ]
        scored_hits.sort(key=lambda item: (-item[0], item[1]))

        selected_count = 0
        seen_hits: set[tuple[str, int]] = set()
        for _score, _position, hit in scored_hits:
            hit_key = (str(hit.get("document_id") or ""), int(hit.get("chunk_index") or 0))
            if hit_key in seen_hits:
                continue
            seen_hits.add(hit_key)
            citation = _canonical_citation_from_search_hit(index_name, hit)
            if not citation:
                continue
            if _citation_points_to_incident(citation, current_incident_id):
                continue
            if not _citation_applies_to_equipment(citation, hit, equipment_id):
                continue
            if not _citation_applies_to_bpr_reference(citation, hit, bpr_reference):
                continue
            citation_key = (
                str(citation.get("index_name") or ""),
                str(citation.get("document_id") or ""),
                int(citation.get("chunk_index") or 0),
            )
            if citation_key in seen_citations:
                continue
            seen_citations.add(citation_key)
            citations.append(citation)
            selected_count += 1
            if selected_count >= per_index_limits.get(index_name, 2):
                break

    if not citations:
        evidence_gaps.append("No canonical evidence citations were retrieved from Azure AI Search.")
    if bpr_reference and not any(citation.get("type") == "bpr" for citation in citations):
        evidence_gaps.append(
            f"No BPR citation matched batch bpr_reference '{bpr_reference}'; product-specific BPR evidence is missing from search results."
        )

    historical_citations = [c for c in citations if c.get("type") == "historical"]
    bpr_citation = next((c for c in citations if c.get("type") == "bpr"), None)
    historical_summaries: list[dict] = []
    approved_count = 0
    rejected_count = 0
    for citation in historical_citations:
        excerpt = str(citation.get("text_excerpt") or "").strip()
        decision, decision_evidence = _extract_human_decision_from_evidence(excerpt)
        if decision == "approved":
            decision = "approved"
            approved_count += 1
        elif decision == "rejected":
            decision = "rejected"
            rejected_count += 1
        status = _extract_history_status(excerpt)
        historical_summaries.append(
            _pick_present(
                {
                    "incident_id": citation.get("document_id", ""),
                    "document_title": citation.get("document_title", ""),
                    "status": status,
                    "human_decision": decision,
                    "decision_evidence": decision_evidence,
                    "evidence_excerpt": excerpt,
                    "source_url": citation.get("url", ""),
                    "similarity_reason": "Retrieved from incident-history search for the current alert and follow-up context.",
                },
                [
                    "incident_id",
                    "document_title",
                    "status",
                    "human_decision",
                    "decision_evidence",
                    "evidence_excerpt",
                    "source_url",
                    "similarity_reason",
                ],
            )
        )

    if historical_summaries:
        historical_pattern_summary = (
            f"Retrieved historical split: {approved_count} approved, "
            f"{rejected_count} rejected among cited similar incidents."
        )
    else:
        historical_pattern_summary = "No historical incident citations retrieved."

    if citations:
        by_type: dict[str, int] = {}
        for citation in citations:
            citation_type = str(citation.get("type") or "document")
            by_type[citation_type] = by_type.get(citation_type, 0) + 1
        type_summary = ", ".join(f"{count} {name}" for name, count in sorted(by_type.items()))
        context_summary = f"Retrieved canonical evidence citations from Azure AI Search: {type_summary}."
    elif evidence_gaps:
        context_summary = "No canonical evidence retrieved; see evidence_gaps."
    else:
        context_summary = "No research evidence was requested."

    if follow_up_search_terms:
        context_summary = (
            f"{context_summary} Latest operator follow-up question was included in backend retrieval."
        )

    follow_up_context = _pick_present(
        {
            "latest_question": latest_operator_question,
            "retrieval_terms": follow_up_search_terms,
            "retrieved_historical_incident_count": len(historical_summaries),
            "historical_human_decision_counts": {
                "approved": approved_count,
                "rejected": rejected_count,
                "unknown": max(len(historical_summaries) - approved_count - rejected_count, 0),
            } if historical_summaries else {},
            "answering_guidance": (
                "The model must answer the latest question from retrieved evidence first, "
                "then state decision impact. If evidence is insufficient, it must say which "
                "fact could not be determined instead of substituting a generic recommendation summary. "
                "For count or comparison questions, include explicit supported counts from cited evidence; "
                "count an attribute only when it is explicitly present in an excerpt, because silence is unknown, "
                "if the requested attribute is missing from the excerpts, say the count is not determinable "
                "from retrieved evidence."
            ) if latest_operator_question else "",
        },
        [
            "latest_question",
            "retrieval_terms",
            "retrieved_historical_incident_count",
            "historical_human_decision_counts",
            "answering_guidance",
        ],
    )

    package = {
        "tool_calls_log": tool_calls_log,
        "follow_up_context": follow_up_context,
        "incident_facts": _pick_present(
            {
                "incident_id": current_incident_id,
                "equipment_id": equipment_id,
                "batch_id": alert_payload.get("batch_id"),
                "parameter": parameter,
                "measured_value": measured_value,
                "lower_limit": lower_limit,
                "upper_limit": upper_limit,
                "duration_seconds": duration_seconds,
                "deviation_type": alert_payload.get("deviation_type"),
                "severity": alert_payload.get("severity"),
            },
            [
                "incident_id",
                "equipment_id",
                "batch_id",
                "parameter",
                "measured_value",
                "lower_limit",
                "upper_limit",
                "duration_seconds",
                "deviation_type",
                "severity",
            ],
        ),
        "equipment_facts": _compact_equipment_context(equipment),
        "batch_facts": _compact_batch_context(batch),
        "bpr_constraints": bpr_citation,
        "historical_incidents": historical_summaries,
        "historical_pattern_summary": historical_pattern_summary,
        "evidence_citations": citations,
        "evidence_gaps": evidence_gaps,
        "context_summary": context_summary,
    }
    return package, rag_context


def _research_hit_score(hit: dict, alert_payload: dict, batch: dict, equipment: dict) -> int:
    haystack = _normalize_text(
        " ".join(
            str(value or "")
            for value in [
                hit.get("document_id"),
                hit.get("document_title"),
                hit.get("source"),
                hit.get("text"),
            ]
        )
    )
    score = 0
    for value, weight in [
        (alert_payload.get("equipment_id") or equipment.get("id") or equipment.get("equipment_id"), 4),
        (alert_payload.get("parameter"), 4),
        (batch.get("product") or batch.get("product_name"), 5),
        (batch.get("bpr_reference"), 5),
        (alert_payload.get("lower_limit"), 2),
        (alert_payload.get("upper_limit"), 2),
        (alert_payload.get("measured_value"), 2),
    ]:
        normalized = _normalize_text(str(value or "").replace("_", " "))
        if normalized and normalized in haystack:
            score += weight

    parameter_words = [
        word for word in _normalize_text(str(alert_payload.get("parameter") or "").replace("_", " ")).split()
        if len(word) > 2
    ]
    score += sum(2 for word in parameter_words if word in haystack)
    if "human decision" in haystack:
        score += 3
    return score


def _canonical_citation_from_search_hit(index_name: str, hit: dict) -> dict | None:
    meta = INDEX_EVIDENCE_META.get(index_name, {})
    citation_type = str(meta.get("type") or hit.get("document_type") or "document")
    source_blob = str(hit.get("source") or hit.get("source_blob") or "").strip()
    if not source_blob:
        return None
    chunk_index = int(hit.get("chunk_index") or 0)
    section_heading = str(hit.get("section_heading") or "").strip()
    if not section_heading:
        for line in str(hit.get("text") or "").splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                section_heading = stripped.lstrip("#").strip()
                break
    if not section_heading:
        section_heading = f"Chunk {chunk_index}"

    raw_text = str(hit.get("text") or "")
    if index_name == "idx-incident-history":
        text_excerpt = _history_evidence_excerpt(raw_text)
    else:
        text_excerpt = _trim_excerpt(raw_text, max_chars=500, min_break=220)
    document_id = str(hit.get("document_id") or "").strip()
    document_title = str(hit.get("document_title") or document_id).strip()
    container = str(meta.get("container") or "")
    return {
        "type": citation_type,
        "document_id": document_id,
        "document_title": document_title,
        "section_heading": section_heading,
        "section": section_heading,
        "section_key": str(hit.get("section_key") or _normalize_section_key(section_heading)),
        "section_path": str(hit.get("section_path") or section_heading),
        "text_excerpt": text_excerpt,
        "source_blob": source_blob,
        "index_name": index_name,
        "chunk_index": chunk_index,
        "score": float(hit.get("score") or 0.0),
        "url": _citation_url(
            citation_type=citation_type,
            document_id=document_id,
            container=container,
            source_blob=source_blob,
        ),
    }


def _history_evidence_excerpt(text: str) -> str:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if not lines:
        return _trim_excerpt(str(text or ""), max_chars=1200, min_break=700)

    preferred_prefixes = (
        "incident id:",
        "equipment:",
        "status:",
        "deviation type:",
        "description:",
        "root cause:",
        "classification:",
        "risk level:",
        "agent recommendation:",
        "operator agreed with agent:",
        "human decision:",
        "human decision reason:",
        "recommendation:",
        "capa:",
        "batch disposition:",
    )
    selected = [line for line in lines if line.lower().startswith(preferred_prefixes)]
    if not selected:
        selected = lines
    excerpt = "\n".join(selected)
    if len(excerpt) <= 1400:
        return excerpt
    shortened_lines: list[str] = []
    total_length = 0
    for line in selected:
        next_length = total_length + len(line) + (1 if shortened_lines else 0)
        if next_length > 1397:
            break
        shortened_lines.append(line)
        total_length = next_length
    shortened = "\n".join(shortened_lines).strip()
    return f"{shortened}\n..." if shortened else excerpt[:1397] + "..."


def _extract_human_decision_from_evidence(text: str) -> tuple[str, str]:
    decision_line = _extract_labeled_line(text, "human decision")
    normalized = _normalize_text(decision_line or text)
    if "approved" in normalized:
        return "approved", decision_line
    if "rejected" in normalized:
        return "rejected", decision_line
    return "unknown", decision_line


def _extract_history_status(text: str) -> str:
    status_line = _extract_labeled_line(text, "status")
    if not status_line:
        return ""
    status_value = status_line.split(":", 1)[-1].strip()
    return status_value.split("|", 1)[0].strip()


def _extract_labeled_line(text: str, label: str) -> str:
    normalized_label = label.strip().lower()
    for line in str(text or "").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(f"{normalized_label}:"):
            return stripped
    return ""


def _log_orchestrator_prompt_trace(
    *,
    incident_id: str,
    more_info_round: int,
    orchestrator_agent_id: str,
    evidence_synthesizer_agent_id: str,
    prompt: str,
    context_data: dict,
) -> None:
    # Tracing guard is enforced inside log_trace_text; no separate check needed here.
    prompt_bundle = {
        "orchestrator_agent_id": orchestrator_agent_id,
        "evidence_synthesizer_agent_id": evidence_synthesizer_agent_id,
        "configured_models": _configured_agent_models(),
        "operator_questions": context_data.get("operator_questions", []),
        "system_prompts": _system_prompt_snapshot(
            orchestrator_agent_id,
            evidence_synthesizer_agent_id,
        ),
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
        "evidence_synthesizer": _resolve_agent_model(
            "FOUNDRY_EVIDENCE_SYNTHESIZER_AGENT_MODEL",
            DEFAULT_EVIDENCE_SYNTHESIZER_AGENT_MODEL,
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


def _system_prompt_snapshot(
    orchestrator_agent_id: str,
    evidence_synthesizer_agent_id: str = "",
) -> dict[str, str]:
    return {
        "orchestrator": _read_agent_prompt(orchestrator_agent_id, "orchestrator_system.md"),
        "evidence_synthesizer": _read_agent_prompt(
            evidence_synthesizer_agent_id,
            "evidence_synthesizer_system.md",
        ),
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


def _resolve_optional_foundry_agent_id(env_var: str, agent_name: str) -> str:
    configured = os.getenv(env_var, "").strip()
    if configured:
        return configured

    resolved = _find_foundry_agent_id_by_name(agent_name)
    if resolved:
        return resolved

    logger.warning(
        "Could not resolve Foundry agent id for %s (env %s); continuing without it",
        agent_name,
        env_var,
    )
    return ""


@lru_cache(maxsize=16)
def _find_foundry_agent_id_by_name(agent_name: str) -> str:
    if not agent_name:
        return ""
    try:
        client = _build_agents_client()
        with client:
            for agent in client.list_agents():
                if getattr(agent, "name", "") == agent_name:
                    return str(getattr(agent, "id", "") or "")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to resolve Foundry agent by name %s: %s", agent_name, exc)
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


_MISSING_JSON_FIELD = object()


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

    recovered = _recover_truncated_agent_json(raw_text)
    if recovered:
        return recovered

    # Fallback — unstructured response (shouldn't happen in production)
    logger.warning("Could not parse structured JSON from Foundry agent response")
    stripped = raw_text.strip()
    fallback_analysis = (
        "Structured agent response could not be parsed. See raw_response in the audit trace."
        if stripped.startswith("{")
        else raw_text[:2000]
        if raw_text
        else "Analysis not available."
    )
    return {
        "title": "Deviation Review Required",
        "analysis": fallback_analysis,
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


def _recover_truncated_agent_json(raw_text: str) -> dict | None:
    """Recover top-level decision fields when Foundry truncates a JSON response.

    The Orchestrator sometimes emits a valid JSON prefix but exhausts output budget
    while copying large citation/tool arrays. The backend owns those arrays anyway,
    so recovering complete scalar fields is safer than surfacing raw JSON to the UI.
    """
    text = raw_text.strip()
    if not text.startswith("{"):
        return None

    recovered: dict[str, object] = {}
    for field_name in [
        "incident_id",
        "title",
        "classification",
        "risk_level",
        "confidence",
        "confidence_flag",
        "root_cause",
        "analysis",
        "recommendation",
        "agent_recommendation",
        "agent_recommendation_rationale",
        "operator_dialogue",
        "capa_suggestion",
        "regulatory_reference",
        "batch_disposition",
        "recommendations",
        "work_order_draft",
        "audit_entry_draft",
        "work_order_id",
        "audit_entry_id",
    ]:
        value = _extract_top_level_json_field(text, field_name)
        if value is not _MISSING_JSON_FIELD:
            recovered[field_name] = value

    if not any(
        field_name in recovered
        for field_name in ("analysis", "recommendation", "agent_recommendation", "risk_level")
    ):
        return None

    analysis = str(recovered.get("analysis") or "Structured analysis recovered from a truncated agent response.")
    root_cause = str(recovered.get("root_cause") or "Could not determine root cause automatically.")
    classification = str(recovered.get("classification") or "unknown")
    recommendation = str(
        recovered.get("recommendation")
        or recovered.get("agent_recommendation_rationale")
        or analysis
    )
    capa_suggestion = str(recovered.get("capa_suggestion") or "")
    audit_entry = recovered.get("audit_entry_draft")
    if not isinstance(audit_entry, dict):
        audit_entry = {
            "deviation_type": classification,
            "description": analysis[:500],
            "root_cause": root_cause,
            "capa_actions": capa_suggestion or recommendation[:500],
        }

    result = {
        "incident_id": str(recovered.get("incident_id") or ""),
        "title": str(recovered.get("title") or "Deviation Review Required"),
        "classification": classification,
        "risk_level": str(recovered.get("risk_level") or "unknown"),
        "confidence": recovered.get("confidence") if isinstance(recovered.get("confidence"), (int, float)) else 0.5,
        "confidence_flag": recovered.get("confidence_flag"),
        "root_cause": root_cause,
        "analysis": analysis,
        "recommendation": recommendation,
        "agent_recommendation": recovered.get("agent_recommendation"),
        "agent_recommendation_rationale": str(recovered.get("agent_recommendation_rationale") or ""),
        "operator_dialogue": str(recovered.get("operator_dialogue") or analysis[:500]),
        "capa_suggestion": capa_suggestion,
        "regulatory_reference": str(recovered.get("regulatory_reference") or ""),
        "batch_disposition": str(recovered.get("batch_disposition") or "hold_pending_review"),
        "recommendations": recovered.get("recommendations") if isinstance(recovered.get("recommendations"), list) else [],
        "regulatory_refs": [],
        "sop_refs": [],
        "evidence_citations": [],
        "work_order_draft": recovered.get("work_order_draft") if isinstance(recovered.get("work_order_draft"), dict) else None,
        "audit_entry_draft": audit_entry,
        "tool_calls_log": [],
        "work_order_id": recovered.get("work_order_id") if isinstance(recovered.get("work_order_id"), str) else None,
        "audit_entry_id": recovered.get("audit_entry_id") if isinstance(recovered.get("audit_entry_id"), str) else None,
        "execution_error": "Foundry response JSON was truncated; recovered scalar decision fields from the response prefix.",
        "raw_response": raw_text,
    }
    logger.warning("Recovered scalar fields from truncated Foundry JSON response")
    return result


def _extract_top_level_json_field(text: str, field_name: str) -> object:
    match = re.search(rf'"{re.escape(field_name)}"\s*:', text)
    if not match:
        return _MISSING_JSON_FIELD

    decoder = json.JSONDecoder()
    value_text = text[match.end():].lstrip()
    try:
        value, _end = decoder.raw_decode(value_text)
        return value
    except json.JSONDecodeError:
        return _MISSING_JSON_FIELD


def _normalize_agent_result(
    result: dict,
    rag_context: dict | None,
    more_info_round: int,
    previous_ai_result: dict | None = None,
    operator_questions: list[dict] | None = None,
    authoritative_research_package: dict | None = None,
) -> dict:
    """Make citation output stable for the operator UI."""
    result["title"] = _normalize_incident_title(result)
    package_citations = (authoritative_research_package or {}).get("evidence_citations")
    if isinstance(package_citations, list):
        result["evidence_citations"] = _normalize_authoritative_research_citations(
            package_citations,
            current_incident_id=str(result.get("incident_id") or ""),
        )
    else:
        result["evidence_citations"] = _normalize_evidence_citations(
            result,
            rag_context or {},
            current_incident_id=str(result.get("incident_id") or ""),
        )
    package_tool_calls = (authoritative_research_package or {}).get("tool_calls_log")
    if isinstance(package_tool_calls, list):
        result["tool_calls_log"] = package_tool_calls
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
    _normalize_agent_recommendation_contract(result)
    _normalize_risk_level_contract(result, authoritative_research_package or {})
    _normalize_low_confidence_contract(result)
    result["operator_dialogue"] = _normalize_operator_dialogue(
        result,
        more_info_round,
        previous_ai_result=previous_ai_result or {},
        operator_questions=operator_questions or [],
    )
    return result


def _normalize_risk_level_contract(result: dict, authoritative_research_package: dict) -> None:
    if str(result.get("agent_recommendation") or "").strip().upper() != "APPROVE":
        return

    incident_facts = authoritative_research_package.get("incident_facts")
    if not isinstance(incident_facts, dict):
        return
    if _normalize_text(str(incident_facts.get("severity") or "")) != "critical":
        return

    risk = _normalize_text(str(result.get("risk_level") or ""))
    if risk in {"", "unknown", "low", "medium", "high"}:
        result["risk_level"] = "critical"


def _normalize_low_confidence_contract(result: dict) -> None:
    risk = _normalize_text(str(result.get("risk_level") or ""))
    flag = _normalize_text(str(result.get("confidence_flag") or ""))
    confidence = result.get("confidence")

    if flag not in {"", "low_confidence"}:
        return
    if risk == "blocked":
        return

    if flag == "low_confidence" or risk == "low_confidence":
        is_low_confidence = True
    else:
        is_low_confidence = isinstance(confidence, (int, float)) and confidence < CONFIDENCE_THRESHOLD

    if not is_low_confidence:
        return

    result["confidence_flag"] = "LOW_CONFIDENCE"
    result["risk_level"] = "LOW_CONFIDENCE"


def _normalize_agent_recommendation_contract(result: dict) -> None:
    verdict = str(result.get("agent_recommendation") or "").strip().upper()
    if verdict not in {"APPROVE", "REJECT"}:
        result["agent_recommendation_rationale"] = ""
        return

    rationale = _build_agent_recommendation_rationale(result, verdict)
    result["agent_recommendation_rationale"] = rationale

    if verdict != "REJECT":
        _normalize_approve_batch_disposition(result)
        return

    had_corrective_actions = bool(result.get("recommendations") or result.get("work_order_draft"))
    result["work_order_draft"] = None
    result["work_order_id"] = None
    result["recommendations"] = []

    if had_corrective_actions or _looks_like_corrective_action_text(result.get("recommendation")):
        result["recommendation"] = rationale
    if _looks_like_corrective_action_text(result.get("capa_suggestion")):
        result["capa_suggestion"] = "No CAPA/work order required; document the event and continue routine trend monitoring."

    audit_entry_draft = result.get("audit_entry_draft")
    if isinstance(audit_entry_draft, dict) and _looks_like_corrective_action_text(
        audit_entry_draft.get("capa_actions")
    ):
        audit_entry_draft["capa_actions"] = (
            "No CAPA/work order required; document the event and continue routine trend monitoring."
        )


def _build_agent_recommendation_rationale(result: dict, verdict: str) -> str:
    analysis = _shorten_text(str(result.get("analysis") or "").strip(), 280)
    recommendation = _shorten_text(str(result.get("recommendation") or "").strip(), 220)
    root_cause = _shorten_text(str(result.get("root_cause") or "").strip(), 180)

    if verdict == "APPROVE":
        reason = recommendation or analysis or root_cause
        return f"APPROVE because corrective action is warranted: {reason}" if reason else "APPROVE because corrective action is warranted by the available evidence."

    reason = analysis or recommendation or root_cause
    return f"REJECT because no formal CAPA/work order is warranted: {reason}" if reason else "REJECT because the available evidence does not support a formal CAPA/work order."


def _normalize_approve_batch_disposition(result: dict) -> None:
    disposition = _normalize_text(str(result.get("batch_disposition") or ""))
    if disposition not in {"hold_pending_review", "hold pending review", "under_review", "under review"}:
        return
    if _approval_requires_testing(result):
        result["batch_disposition"] = "conditional_release_pending_testing"


def _approval_requires_testing(result: dict) -> bool:
    values: list[object] = [
        result.get("recommendation"),
        result.get("analysis"),
        result.get("operator_dialogue"),
        result.get("capa_suggestion"),
    ]
    audit_entry_draft = result.get("audit_entry_draft")
    if isinstance(audit_entry_draft, dict):
        values.extend(audit_entry_draft.values())
    work_order_draft = result.get("work_order_draft")
    if isinstance(work_order_draft, dict):
        values.extend(work_order_draft.values())
    for item in result.get("recommendations") or []:
        if isinstance(item, dict):
            values.extend(item.values())

    text = _normalize_text(" ".join(str(value or "") for value in values))
    testing_markers = [
        "test",
        "testing",
        "qc",
        "quality control",
        "quality testing",
        "granule distribution",
        "moisture",
        "psd",
        "particle size",
    ]
    return any(marker in text for marker in testing_markers)


def _looks_like_corrective_action_text(value: object) -> bool:
    text = _normalize_text(str(value or ""))
    if not text:
        return False
    no_action_markers = ["no corrective action", "no capa", "no formal capa", "no action required"]
    if any(marker in text for marker in no_action_markers):
        return False
    action_markers = [
        "calibrat",
        "inspect",
        "investigat",
        "repair",
        "replace",
        "clean",
        "work order",
        "corrective",
        "conduct",
        "perform",
    ]
    return any(marker in text for marker in action_markers)


def _citation_applies_to_equipment(citation: dict, hit: dict, equipment_id: str) -> bool:
    if not equipment_id:
        return True
    index_name = str(citation.get("index_name") or "")
    if index_name not in {"idx-sop-documents", "idx-equipment-manuals"}:
        return True

    equipment_ids = {
        str(value).strip().upper()
        for value in (hit.get("equipment_ids") or [])
        if str(value).strip()
    }
    current_equipment = equipment_id.strip().upper()
    if equipment_ids:
        return current_equipment in equipment_ids

    # Older or partially populated indexes may not return equipment_ids for SOPs.
    # Keep global procedures, but reject equipment-specific SOP/manual documents
    # whose identity points at a different equipment family.
    document_identity = " ".join(
        str(value or "")
        for value in [
            citation.get("document_id"),
            citation.get("document_title"),
            citation.get("source_blob"),
            citation.get("section_path"),
        ]
    ).upper()
    current_prefix = current_equipment.split("-", 1)[0]
    specific_sop_match = re.search(r"\bSOP-MAN-([A-Z]+)-", document_identity)
    if specific_sop_match:
        return specific_sop_match.group(1) == current_prefix

    explicit_equipment_ids = set(
        re.findall(r"\b(?:GR|MIX|DRY|COMP|PKG|FBD|BLD)-\d{3,4}\b", document_identity)
    )
    if explicit_equipment_ids:
        return current_equipment in explicit_equipment_ids

    return True


def _citation_applies_to_bpr_reference(citation: dict, hit: dict, bpr_reference: str) -> bool:
    if str(citation.get("index_name") or "") != "idx-bpr-documents":
        return True
    expected = _normalize_document_match_key(bpr_reference)
    if not expected:
        return True

    identity = _normalize_document_match_key(
        " ".join(
            str(value or "")
            for value in [
                citation.get("document_id"),
                citation.get("document_title"),
                citation.get("source_blob"),
                citation.get("section_path"),
                hit.get("document_id"),
                hit.get("document_title"),
                hit.get("source"),
                hit.get("source_blob"),
            ]
        )
    )
    return expected in identity


def _normalize_document_match_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _normalize_authoritative_research_citations(
    citations: list[dict],
    *,
    current_incident_id: str,
) -> list[dict]:
    normalized: list[dict] = []
    seen: set[tuple[str, str, int]] = set()
    for item in citations:
        if not isinstance(item, dict):
            continue

        citation = dict(item)
        if citation.get("type") == "incident" or _citation_points_to_incident(
            citation,
            current_incident_id,
        ):
            continue

        index_name = str(citation.get("index_name") or "").strip()
        citation_type = str(citation.get("type") or INDEX_EVIDENCE_META.get(index_name, {}).get("type") or "document")
        document_id = str(citation.get("document_id") or "").strip()
        source_blob = str(citation.get("source_blob") or citation.get("source") or "").strip()
        chunk_index = int(citation.get("chunk_index") or 0)
        key = (index_name, document_id or source_blob, chunk_index)
        if key in seen:
            continue
        seen.add(key)

        section_heading = str(citation.get("section_heading") or citation.get("section") or "").strip()
        container = str(citation.get("container") or INDEX_EVIDENCE_META.get(index_name, {}).get("container") or "")
        citation.update(
            {
                "type": citation_type,
                "document_id": document_id,
                "document_title": str(citation.get("document_title") or document_id).strip(),
                "section_heading": section_heading,
                "section": str(citation.get("section") or section_heading).strip(),
                "section_key": str(citation.get("section_key") or _normalize_section_key(section_heading)).strip(),
                "section_path": str(citation.get("section_path") or section_heading).strip(),
                "source_blob": source_blob,
                "container": container,
                "index_name": index_name,
                "chunk_index": chunk_index,
                "score": citation.get("score", 0.0),
                "resolution_status": "resolved" if source_blob or citation_type == "historical" else "unresolved",
                "unresolved_reason": "" if source_blob or citation_type == "historical" else "Missing source_blob",
            }
        )
        if not citation.get("url"):
            citation["url"] = _citation_url(
                citation_type=citation_type,
                document_id=document_id,
                container=container,
                source_blob=source_blob,
            )
        normalized.append(citation)
    return normalized


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
    if explicit:
        return explicit[:800]

    recommendation = str(result.get("recommendation") or "").strip()
    analysis = str(result.get("analysis") or "").strip()
    return (recommendation or analysis or "AI agent did not return an operator dialogue summary.")[:800]


def _get_latest_operator_question(operator_questions: list[dict]) -> str:
    if not operator_questions:
        return ""
    latest = operator_questions[-1]
    return str(latest.get("question") or "").strip()


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _shorten_text(text: str, limit: int) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    shortened = compact[: limit - 3].rsplit(" ", 1)[0].strip()
    return f"{shortened}..." if shortened else compact[: limit - 3] + "..."


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

    # Post-normalization: fix section-mismatch unresolved citations via targeted search
    _resolve_section_mismatch_citations(normalized)

    # Remove ghost citations that duplicate a real document citation for the same section
    normalized = _deduplicate_ghost_citations(normalized)

    return normalized


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
    source = (
        item.get("source")
        or item.get("document_id")
        or (match or {}).get("document_id")
        or (match or {}).get("document_title")
        or ""
    )
    reference = item.get("reference") or item.get("regulation") or ""
    document_title = (
        item.get("document_title")
        or item.get("title")
        or item.get("regulation")
        or (match or {}).get("document_title")
        or item.get("reference")
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
    index_name = str(item.get("index_name") or (match or {}).get("index_name", "")).strip()
    container = item.get("container") or (match or {}).get("container", "")
    if not container and index_name:
        container = INDEX_EVIDENCE_META.get(index_name, {}).get("container", "")
    if not container and citation_type in _TYPE_TO_INDEX:
        container = INDEX_EVIDENCE_META.get(_TYPE_TO_INDEX[citation_type], {}).get("container", "")
    if citation_type == "historical" and not document_id:
        document_id = _extract_historical_incident_id(source_blob or source or document_title)
    if citation_type == "historical" and document_id and document_title.lower() in {"incident", "details", "historical"}:
        document_title = f"Similar incident {document_id}"
    if not document_title:
        if citation_type == "historical" and document_id:
            document_title = f"Similar incident {document_id}"
        else:
            document_title = source or reference
    section_claim = str(
        item.get("section") or item.get("relevant_section") or item.get("section_heading") or ""
    ).strip()
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
        "index_name": index_name,
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
