"""
Activity: run_foundry_agents — call Foundry Orchestrator Agent (T-024, ADR-002)

Orchestrator Agent manages the Research → Document pipeline natively via
Connected Agents (AgentTool). This activity creates a thread, sends the full
incident context as a user message, and waits for the agent to produce a
structured JSON analysis.

Returns:
    {
        "analysis": str,
        "root_cause": str,
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
import re
from datetime import datetime, timezone
from urllib.parse import quote

import azure.durable_functions as df
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    AgentThreadCreationOptions,
    MessageRole,
    ThreadMessageOptions,
)
from azure.identity import DefaultAzureCredential

from shared.foundry_run import create_thread_and_process_run_with_approval
from shared.search_utils import search_all_indexes

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))
SEARCH_ENABLED = bool(os.getenv("AZURE_SEARCH_ENDPOINT", ""))

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
    more_info_round: int = input_data.get("more_info_round", 0)

    logger.info(
        "run_foundry_agents: incident=%s round=%d", incident_id, more_info_round
    )

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

    prompt = _build_prompt(incident_id, context_data, more_info_round, rag_context)
    result = _call_orchestrator_agent(prompt, orchestrator_agent_id)
    result = _normalize_agent_result(result, rag_context)

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


def _call_orchestrator_agent(prompt: str, agent_id: str) -> dict:
    """Create a Foundry thread, run the Orchestrator Agent, return parsed result.

    Uses ``create_thread_and_process_run_with_approval`` to handle MCP tool
    approval automatically — the Foundry API (2025-05-15-preview) does not
    persist ``require_approval="never"`` for MCP tools, so every MCP call
    triggers a ``submit_tool_approval`` action that must be approved client-side.
    """
    endpoint = os.environ.get(
        "AZURE_AI_FOUNDRY_AGENTS_ENDPOINT",
        os.environ.get("AZURE_AI_FOUNDRY_PROJECT_CONNECTION_STRING", ""),
    )
    os.environ.setdefault("AZURE_AI_AGENTS_TESTS_IS_TEST_RUN", "True")
    client = AgentsClient(endpoint=endpoint, credential=DefaultAzureCredential())

    with client:
        run = create_thread_and_process_run_with_approval(
            client,
            agent_id=agent_id,
            thread=AgentThreadCreationOptions(
                messages=[
                    ThreadMessageOptions(role=MessageRole.USER, content=prompt)
                ]
            ),
        )

        if run.status == "failed":
            raise RuntimeError(
                f"Foundry Orchestrator run failed: {getattr(run, 'last_error', run.status)}"
            )

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
                    if hasattr(block, "text"):
                        raw_text += block.text.value
                break

        logger.info(
            "Foundry raw response length=%d first 500 chars: %s",
            len(raw_text), raw_text[:500],
        )
        return _parse_response(raw_text)


def _build_prompt(
    incident_id: str,
    context_data: dict,
    more_info_round: int,
    rag_context: dict | None = None,
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
                "classification": "process_parameter_excursion | equipment_malfunction | ...",
                "risk_level": "low | medium | high | critical",
                "confidence": 0.85,
                "root_cause": "Primary root cause in one sentence",
                "analysis": "Detailed root cause analysis with evidence.",
                "recommendation": "Recommended immediate action.",
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
        "analysis": raw_text[:2000] if raw_text else "Analysis not available.",
        "root_cause": "Could not determine root cause automatically.",
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


def _normalize_agent_result(result: dict, rag_context: dict | None) -> dict:
    """Make citation output stable for the operator UI."""
    result["evidence_citations"] = _normalize_evidence_citations(result, rag_context or {})
    return result


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
