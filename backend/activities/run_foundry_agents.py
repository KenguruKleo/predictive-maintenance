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
from datetime import datetime, timezone
from difflib import SequenceMatcher
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

from shared.cosmos_client import get_container
from shared.foundry_run import (
    FoundryRunTimeoutError,
    create_thread_and_process_run_with_approval,
)
from shared.search_utils import search_all_indexes

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))
SEARCH_ENABLED = bool(os.getenv("AZURE_SEARCH_ENDPOINT", ""))
try:
    FOUNDRY_ACTIVITY_TIMEOUT_SECS = max(
        240.0,
        float(os.getenv("FOUNDRY_ACTIVITY_TIMEOUT_SECS", "240")),
    )
except ValueError:
    FOUNDRY_ACTIVITY_TIMEOUT_SECS = 240.0

INDEX_EVIDENCE_META = {
    "idx-sop-documents": {"type": "sop", "container": "blob-sop"},
    "idx-equipment-manuals": {"type": "manual", "container": "blob-manuals"},
    "idx-bpr-documents": {"type": "bpr", "container": "blob-bpr"},
    "idx-gmp-policies": {"type": "gmp", "container": "blob-gmp"},
    "idx-incident-history": {"type": "historical", "container": "blob-history"},
}

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

    # Write analysis_started event on the first (non-more_info) run
    if more_info_round == 0:
        _write_analysis_started_event(incident_id)

    orchestrator_agent_id = os.environ.get("ORCHESTRATOR_AGENT_ID", "") or "asst_CNYK3TZIaOCH4OPKcP4N9B2r"
    if not orchestrator_agent_id:
        raise EnvironmentError(
            "ORCHESTRATOR_AGENT_ID env var is not set. "
            "Run agents/create_agents.py first to provision Foundry agents."
        )

    # ── Pre-fetch RAG context from all 5 AI Search indexes ─────────────────
    rag_context: dict = {}
    if SEARCH_ENABLED:
        equipment_id = context_data.get("equipment_id") or (
            context_data.get("equipment", {}).get("id")
        )
        alert = context_data.get("alert_payload", {})
        search_query = (
            f"{alert.get('alert_type', '')} {alert.get('deviation_description', '')} "
            f"{alert.get('parameter', '')} {alert.get('equipment_id', '')}"
        ).strip() or f"GMP deviation incident {incident_id}"
        try:
            rag_context = search_all_indexes(
                query=search_query,
                equipment_id=equipment_id,
                top_k=3,
            )
            logger.info(
                "RAG pre-fetch: %d total chunks for incident %s",
                sum(len(v) for v in rag_context.values()),
                incident_id,
            )
        except Exception as exc:
            logger.warning("RAG pre-fetch failed (non-fatal): %s", exc)

    # Startup stagger: deterministically spread concurrent incidents to avoid
    # thundering-herd on the Foundry rate limit.  Uses the numeric suffix of the
    # incident ID to derive a 0-60 s offset (e.g. INC-2026-0048 → 48*17 % 60 = 36 s).
    try:
        suffix = int(incident_id.rsplit("-", 1)[-1])
        stagger = (suffix * 17) % 60
    except ValueError:
        stagger = random.randint(0, 59)
    if stagger > 0:
        logger.info(
            "Startup stagger %.0fs for %s (thundering-herd prevention)",
            stagger, incident_id,
        )
        time.sleep(stagger)

    prompt = _build_prompt(
        incident_id,
        context_data,
        more_info_round,
        rag_context,
        previous_ai_result,
    )
    try:
        result = _call_orchestrator_agent(prompt, orchestrator_agent_id)
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

    return result


# ── Internal helpers ──────────────────────────────────────────────────────


_RATE_LIMIT_MAX_RETRIES = 5
# Base backoff in seconds; actual wait = base + random jitter (0..base/2)
# This prevents thundering herd when multiple incidents retry simultaneously.
_RATE_LIMIT_BACKOFF_SECS = [30, 60, 90, 120, 180]


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


def _call_orchestrator_agent(prompt: str, agent_id: str) -> dict:
    """Create a Foundry thread, run the Orchestrator Agent, return parsed result.

    Uses ``create_thread_and_process_run_with_approval`` to handle MCP tool
    approval automatically — the Foundry API (2025-05-15-preview) does not
    persist ``require_approval="never"`` for MCP tools, so every MCP call
    triggers a ``submit_tool_approval`` action that must be approved client-side.

    Rate-limit errors are retried up to _RATE_LIMIT_MAX_RETRIES times with
    exponential back-off.
    """
    endpoint = os.environ.get(
        "AZURE_AI_FOUNDRY_AGENTS_ENDPOINT",
        os.environ.get("AZURE_AI_FOUNDRY_PROJECT_CONNECTION_STRING", ""),
    )
    os.environ.setdefault("AZURE_AI_AGENTS_TESTS_IS_TEST_RUN", "True")
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
            client = AgentsClient(endpoint=endpoint, credential=DefaultAzureCredential())
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

                messages = client.messages.list(thread_id=run.thread_id)

                # list_messages returns newest-first; first AGENT message is the answer.
                # NOTE: azure-ai-agents SDK uses MessageRole.AGENT (value="assistant"),
                # but str(MessageRole.AGENT) == "MessageRole.AGENT", NOT "assistant".
                raw_text = ""
                for msg in messages:
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
                return _parse_response(raw_text)

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
        recommendation = str(previous.get("recommendation") or "").strip()
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
    rag_context: dict | None = None,
    previous_ai_result: dict | None = None,
) -> str:
    """Build the user message that drives the Orchestrator Agent."""
    equipment = context_data.get("equipment", {})
    batch = context_data.get("batch", {})
    recent_incidents = context_data.get("recent_incidents", [])
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
        "### Equipment Context",
        "```json",
        json.dumps(equipment, indent=2, default=str),
        "```",
        "",
        "### Active Batch",
        "```json",
        json.dumps(batch, indent=2, default=str),
        "```",
        "",
        f"### Recent Incidents (last {len(recent_incidents)} on this equipment)",
        "```json",
        json.dumps(recent_incidents, indent=2, default=str),
        "```",
    ]

    # ── RAG pre-fetched context (from all 5 AI Search indexes) ────────────
    if rag_context:
        _INDEX_LABELS = {
            "idx-sop-documents": "Relevant SOP Sections",
            "idx-equipment-manuals": "Equipment Manual Sections",
            "idx-bpr-documents": "BPR / Product Process Specs (NOR/PAR)",
            "idx-gmp-policies": "Applicable GMP Regulations & Policies",
            "idx-incident-history": "Similar Historical Incidents",
        }
        lines.append("")
        lines.append("### Pre-fetched RAG Context (AI Search — all 5 indexes)")
        lines.append(
            "> Use these excerpts as primary evidence. Cite document_title and section in your analysis."
        )
        for idx_name, hits in rag_context.items():
            if not hits:
                continue
            label = _INDEX_LABELS.get(idx_name, idx_name)
            lines.append(f"\n#### {label}")
            for hit in hits:
                lines.append(
                    f"**[{hit['document_title']}]** "
                    f"(index={idx_name}; source_blob={hit.get('source', '')}; "
                    f"chunk={hit.get('chunk_index', '')}; score={hit['score']:.3f}):\n"
                    f"{hit['text'][:600]}"
                )

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
            "The Pre-fetched RAG Context above contains relevant excerpts from SOPs, "
            "equipment manuals, BPR product specs, GMP regulations, and similar historical incidents "
            "retrieved via semantic search. Use these as your primary evidence base — cite them explicitly. "
            "Use your Research sub-agent to retrieve any additional context not covered above. "
            "Then use your Document sub-agent to produce the final structured analysis."
        ),
        "",
        "Return your response as a **single JSON block** using this exact schema:",
        "```json",
        json.dumps(
            {
                "incident_id": incident_id,
                "title": "Short operator-facing incident title in under 8 words",
                "classification": "process_parameter_excursion | equipment_malfunction | ...",
                "risk_level": "low | medium | high | critical",
                "confidence": 0.85,
                "root_cause": "Primary root cause in one sentence",
                "analysis": "Detailed root cause analysis with evidence.",
                "recommendation": "Recommended immediate action.",
                "operator_dialogue": (
                    "Round 0: concise summary for operator. "
                    "Round >0: start by saying what follow-up question you reviewed, "
                    "then state clearly whether recommendation/root cause changed or stayed the same, and why. "
                    "Do not simply repeat the recommendation text."
                ),
                "capa_suggestion": "1. ...\n2. ...",
                "regulatory_reference": "SOP-DEV-001 §4.2; GMP Annex 15 §6.3",
                "batch_disposition": "conditional_release_pending_testing | rejected | release",
                "recommendations": [
                    {
                        "action": "...",
                        "priority": "critical|high|medium|low",
                        "owner": "...",
                        "deadline_days": 0,
                    }
                ],
                "regulatory_refs": [
                    {
                        "regulation": "EU GMP Annex 15",
                        "section": "§6.3",
                        "text_excerpt": "...",
                    }
                ],
                "sop_refs": [
                    {
                        "id": "SOP-DEV-001",
                        "title": "Deviation Management",
                        "relevant_section": "§4.2",
                        "text_excerpt": "...",
                    }
                ],
                "evidence_citations": [
                    {
                        "type": "sop|manual|bpr|gmp|historical|incident",
                        "document_id": "SOP-DEV-001",
                        "document_title": "Deviation Management",
                        "section": "§4.2",
                        "text_excerpt": "...",
                        "source_blob": "SOP-DEV-001-Deviation-Management.md",
                        "index_name": "idx-sop-documents",
                        "chunk_index": 0,
                        "score": 0.82,
                    }
                ],
                "work_order_draft": {
                    "title": "...",
                    "description": "...",
                    "priority": "high",
                    "estimated_hours": 4,
                },
                "audit_entry_draft": {
                    "deviation_type": "...",
                    "description": "...",
                    "root_cause": "...",
                    "capa_actions": "...",
                },
            },
            indent=2,
        ),
        "```",
        "",
        "Never fabricate data. Cite all sources. If confidence is below 0.75, "
        "set risk_level to 'LOW_CONFIDENCE' and explain what additional information "
        "would raise confidence.",
        "Always include operator_dialogue: plain language, under 120 words. "
        "For follow-up rounds, explicitly say what question you checked, what changed or why no change was needed, "
        "and never just repeat the recommendation or analysis verbatim.",
    ]

    return "\n".join(lines)


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
    result["evidence_citations"] = _normalize_evidence_citations(result, rag_context or {})
    result["operator_dialogue"] = _normalize_operator_dialogue(
        result,
        more_info_round,
        previous_ai_result=previous_ai_result or {},
        operator_questions=operator_questions or [],
    )
    return result


def _normalize_operator_dialogue(
    result: dict,
    more_info_round: int,
    previous_ai_result: dict | None = None,
    operator_questions: list[dict] | None = None,
) -> str:
    explicit = str(result.get("operator_dialogue") or "").strip()
    previous_ai_result = previous_ai_result or {}
    operator_questions = operator_questions or []

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
    if latest_question and not _mentions_change_or_reason(normalized_explicit):
        return True

    return False


def _build_followup_operator_dialogue(
    result: dict,
    previous_ai_result: dict,
    operator_questions: list[dict],
) -> str:
    latest_question = _get_latest_operator_question(operator_questions)
    recommendation = str(result.get("recommendation") or "").strip()
    root_cause = str(result.get("root_cause") or "").strip()
    changed_fields = _get_changed_followup_fields(result, previous_ai_result)

    if latest_question:
        intro = f'I reviewed your follow-up question: "{_shorten_text(latest_question, 180)}".'
    else:
        intro = "I reviewed your follow-up question and re-checked the available evidence."

    if changed_fields:
        field_summary = _human_join(changed_fields)
        details: list[str] = [
            f"I updated {field_summary} based on the available evidence."
        ]
        if root_cause:
            details.append(f"Updated root cause hypothesis: {root_cause}")
        if recommendation:
            details.append(f"Updated recommendation: {recommendation}")
        return " ".join([intro, *details]).strip()

    no_change_parts = [
        intro,
        "I did not find enough new evidence to change the current recommendation or root-cause hypothesis.",
    ]
    if recommendation:
        no_change_parts.append(f"Recommendation remains: {recommendation}")
    return " ".join(no_change_parts).strip()


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


def _normalize_evidence_citations(result: dict, rag_context: dict) -> list[dict]:
    flat_hits = _flatten_rag_hits(rag_context)
    raw_items: list[dict] = []

    for item in result.get("evidence_citations", []) or []:
        if isinstance(item, dict):
            raw_items.append(item)
        elif isinstance(item, str):
            raw_items.append({"source": item})

    for item in result.get("sop_refs", []) or []:
        if isinstance(item, dict):
            raw_items.append({"type": "sop", **item})
        elif isinstance(item, str):
            raw_items.append({"type": "sop", "source": item, "document_id": item})

    for item in result.get("regulatory_refs", []) or []:
        if isinstance(item, dict):
            raw_items.append({"type": "gmp", **item})
        elif isinstance(item, str):
            raw_items.append({"type": "gmp", "source": item, "document_title": item})

    normalized: list[dict] = []
    seen: set[tuple] = set()
    for item in raw_items:
        citation = _normalize_single_citation(item, flat_hits)
        key = (
            citation.get("type", ""),
            citation.get("document_title", ""),
            citation.get("section", ""),
            citation.get("source_blob", ""),
            citation.get("text_excerpt", "")[:80],
        )
        if key in seen:
            continue
        seen.add(key)
        normalized.append(citation)

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
    match = _find_matching_hit(item, flat_hits)
    citation_type = item.get("type") or _infer_citation_type(item, match)
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
    known_doc = _infer_known_document(item)
    if not source_blob and known_doc:
        source_blob = known_doc["source_blob"]
    if not container and known_doc:
        container = known_doc["container"]
    if known_doc and (
        not document_title or document_title in {"equipment_manual_notes", "incident", "details"}
    ):
        document_title = known_doc["document_title"]
    if not document_title:
        section_fallback = item.get("section") or item.get("relevant_section") or ""
        if citation_type and section_fallback:
            document_title = f"{citation_type.upper()} reference"
        elif citation_type:
            document_title = f"{citation_type.upper()} evidence"
    section = item.get("section") or item.get("relevant_section") or ""
    text_excerpt = item.get("text_excerpt") or item.get("quote") or item.get("relevance") or ""

    citation = {
        "type": citation_type,
        "document_id": document_id,
        "document_title": document_title,
        "section": section,
        "text_excerpt": text_excerpt,
        "source_blob": source_blob,
        "container": container,
        "index_name": item.get("index_name") or (match or {}).get("index_name", ""),
        "chunk_index": item.get("chunk_index", (match or {}).get("chunk_index")),
        "score": item.get("score", (match or {}).get("score")),
    }
    citation["url"] = item.get("url") or _document_url(container, source_blob)
    return citation


def _find_matching_hit(item: dict, flat_hits: list[dict]) -> dict | None:
    candidates = [
        item.get("document_id"),
        item.get("id"),
        item.get("document_title"),
        item.get("title"),
        item.get("regulation"),
        item.get("reference"),
        item.get("source"),
        item.get("source_blob"),
    ]
    candidate_text = " ".join(str(c) for c in candidates if c).lower()
    excerpt = str(item.get("text_excerpt") or item.get("quote") or "").lower()

    for hit in flat_hits:
        hit_identifiers = " ".join(
            str(hit.get(k, ""))
            for k in ("document_id", "document_title", "source", "document_type")
        ).lower()
        if candidate_text and (
            candidate_text in hit_identifiers or hit_identifiers in candidate_text
        ):
            return hit
        if excerpt and (excerpt[:80] in str(hit.get("text", "")).lower()):
            return hit
    return None


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
    return "incident"


def _document_url(container: str, source_blob: str) -> str:
    if not container or not source_blob:
        return ""
    return f"/api/documents/{container}/{quote(source_blob, safe='/')}"


def _infer_known_document(item: dict) -> dict | None:
    text = " ".join(
        str(item.get(k, ""))
        for k in ("document_id", "document_title", "reference", "source", "text_excerpt")
    ).lower()
    if "sop-dev-001" in text:
        return {
            "container": "blob-sop",
            "source_blob": "SOP-DEV-001-Deviation-Management.md",
            "document_title": "Deviation Management (SOP-DEV-001)",
        }
    if "sop-man-gr-001" in text or "granulator operation" in text:
        return {
            "container": "blob-sop",
            "source_blob": "SOP-MAN-GR-001-Granulator-Operation.md",
            "document_title": "Granulator Operation (SOP-MAN-GR-001)",
        }
    if "annex 15" in text or "eu gmp" in text:
        return {
            "container": "blob-gmp",
            "source_blob": "GMP-Annex15-Excerpt.md",
            "document_title": "EU GMP Annex 15",
        }
    if "metformin" in text or "b26041701" in text:
        return {
            "container": "blob-bpr",
            "source_blob": "BPR-MET-500-v3.2-Process-Specification.md",
            "document_title": "BPR Metformin 500mg Process Specification",
        }
    return None


def _write_analysis_started_event(incident_id: str) -> None:
    """Write an analysis_started audit event when the AI agent begins processing."""
    from azure.cosmos.exceptions import CosmosResourceExistsError
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    event = {
        "id": f"{incident_id}-analysis-started-{int(datetime.now(timezone.utc).timestamp())}",
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
