"""
create_agents.py — Provision Foundry agents for Sentinel Intelligence (T-025, T-026, T-024)

Run once (or with --update) to create/update Research, Evidence Synthesizer,
Document, and Orchestrator agents
in Azure AI Foundry Agent Service.

Uses OpenApiTool so Foundry calls our read-only REST endpoints server-side (no client-side
approval needed — works natively in Foundry Playground, unlike McpTool which always requires
approval and the Playground has no UI for that). Write-side QMS/CMMS persistence remains in the
post-approval backend execution path.

Usage:
    cd /workspace/predictive-maintenance
    AZURE_AI_FOUNDRY_AGENTS_ENDPOINT='swedencentral.api.azureml.ms;d16bb0b5-b7b2-4c3b-805b-f7ccb9ce3550;ODL-GHAZ-2177134;aip-sentinel-intel-dev-erzrpo' \

    python agents/create_agents.py [--update]

After running, copy the printed IDs into local.settings.json / Azure App Settings:
    ORCHESTRATOR_AGENT_ID=...
    EVIDENCE_SYNTHESIZER_AGENT_ID=...
    RESEARCH_AGENT_ID=...
    DOCUMENT_AGENT_ID=...
"""

import argparse
import os
import sys
import time
from pathlib import Path

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    OpenApiAnonymousAuthDetails,
    OpenApiTool,
    ResponseFormatJsonSchema,
    ResponseFormatJsonSchemaType,
    ToolDefinition,
)
from azure.core.exceptions import HttpResponseError
from azure.identity import AzureCliCredential, DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

# ── Prompt files (created during T-025 / T-026) ───────────────────────────
PROMPTS_DIR = Path(__file__).parent / "prompts"
RESEARCH_PROMPT = (PROMPTS_DIR / "research_system.md").read_text(encoding="utf-8")
EVIDENCE_SYNTHESIZER_PROMPT = (PROMPTS_DIR / "evidence_synthesizer_system.md").read_text(encoding="utf-8")
DOCUMENT_PROMPT = (PROMPTS_DIR / "document_system.md").read_text(encoding="utf-8")
ORCHESTRATOR_PROMPT = (PROMPTS_DIR / "orchestrator_system.md").read_text(encoding="utf-8")

DEFAULT_RESEARCH_AGENT_MODEL = "gpt-4o"
DEFAULT_EVIDENCE_SYNTHESIZER_AGENT_MODEL = "gpt-4o"
DEFAULT_DOCUMENT_AGENT_MODEL = "gpt-4o"
DEFAULT_ORCHESTRATOR_AGENT_MODEL = "gpt-4o"


def _resolve_agent_model(env_var: str, default_model: str) -> str:
    override = os.getenv(env_var, "").strip()
    if override:
        return override

    global_override = os.getenv("FOUNDRY_AGENT_MODEL", "").strip()
    if global_override:
        return global_override

    return default_model


RESEARCH_MODEL = _resolve_agent_model(
    "FOUNDRY_RESEARCH_AGENT_MODEL", DEFAULT_RESEARCH_AGENT_MODEL
)
EVIDENCE_SYNTHESIZER_MODEL = _resolve_agent_model(
    "FOUNDRY_EVIDENCE_SYNTHESIZER_AGENT_MODEL",
    DEFAULT_EVIDENCE_SYNTHESIZER_AGENT_MODEL,
)
DOCUMENT_MODEL = _resolve_agent_model(
    "FOUNDRY_DOCUMENT_AGENT_MODEL",
    DEFAULT_DOCUMENT_AGENT_MODEL,
)
ORCHESTRATOR_MODEL = _resolve_agent_model(
    "FOUNDRY_ORCHESTRATOR_AGENT_MODEL",
    DEFAULT_ORCHESTRATOR_AGENT_MODEL,
)
TEMPERATURE = 0.2  # Low temp for deterministic structured JSON output
TOP_P = 0.9         # Slightly constrained nucleus sampling
_TRANSIENT_FOUNDRY_STATUS_CODES = frozenset({408, 409, 429, 500, 502, 503, 504})
_FOUNDRY_RETRY_ATTEMPTS = max(1, int(os.getenv("FOUNDRY_AGENT_RETRY_ATTEMPTS", "4")))
_FOUNDRY_RETRY_BASE_SECONDS = max(
    0.0,
    float(os.getenv("FOUNDRY_AGENT_RETRY_BASE_SECONDS", "2")),
)

CANONICAL_EVIDENCE_CITATION_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["sop", "gmp", "bpr", "manual", "historical"],
        },
        "document_id": {"type": "string", "minLength": 1},
        "document_title": {"type": "string", "minLength": 1},
        "section_heading": {"type": "string", "minLength": 1},
        "text_excerpt": {"type": "string", "minLength": 20},
        "source_blob": {"type": "string", "pattern": r"^.+\.(md|txt)$"},
        "index_name": {
            "type": "string",
            "enum": [
                "idx-sop-documents",
                "idx-gmp-policies",
                "idx-bpr-documents",
                "idx-equipment-manuals",
                "idx-incident-history",
            ],
        },
        "chunk_index": {"type": "integer", "minimum": 0},
        "score": {"type": "number"},
        "source": {"type": "string"},
        "section": {"type": "string"},
        "section_key": {"type": "string"},
        "section_path": {"type": "string"},
        "url": {"type": "string"},
        "similarity_reason": {"type": "string"},
    },
    "required": [
        "type",
        "document_id",
        "document_title",
        "section_heading",
        "text_excerpt",
        "source_blob",
        "index_name",
        "chunk_index",
        "score",
    ],
    "additionalProperties": False,
}

TOOL_CALL_LOG_ENTRY_SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {"type": "string"},
        "args": {"type": "object"},
        "status": {"type": "string"},
        "error": {"type": ["string", "null"]},
    },
    "required": ["tool", "args", "status"],
    "additionalProperties": False,
}

RESEARCH_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_calls_log": {
            "type": "array",
            "items": TOOL_CALL_LOG_ENTRY_SCHEMA,
        },
        "incident_facts": {"type": "object", "additionalProperties": True},
        "equipment_facts": {"type": "object", "additionalProperties": True},
        "batch_facts": {"type": "object", "additionalProperties": True},
        "bpr_constraints": {"type": ["object", "null"], "additionalProperties": True},
        "historical_incidents": {
            "type": "array",
            "items": {"type": "object", "additionalProperties": True},
        },
        "historical_pattern_summary": {"type": "string"},
        "evidence_citations": {
            "type": "array",
            "items": CANONICAL_EVIDENCE_CITATION_SCHEMA,
        },
        "evidence_gaps": {
            "type": "array",
            "items": {"type": "string"},
        },
        "context_summary": {"type": "string"},
    },
    "required": [
        "tool_calls_log",
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
    "additionalProperties": False,
}

EVIDENCE_SYNTHESIS_SCHEMA = {
    "type": "object",
    "properties": {
        "latest_question": {"type": "string"},
        "question_focus": {"type": "string"},
        "answerability": {
            "type": "string",
            "enum": ["answered", "partially_answered", "not_determinable", "not_applicable"],
        },
        "direct_answer": {"type": "string"},
        "operator_dialogue": {"type": "string"},
        "checked_evidence_count": {"type": "integer", "minimum": 0},
        "explicit_support_count": {"type": "integer", "minimum": 0},
        "contradiction_count": {"type": "integer", "minimum": 0},
        "unknown_count": {"type": "integer", "minimum": 0},
        "supporting_evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_id": {"type": "string"},
                    "source_type": {"type": "string"},
                    "fact": {"type": "string"},
                },
                "required": ["source_id", "source_type", "fact"],
                "additionalProperties": False,
            },
        },
        "evidence_gaps": {
            "type": "array",
            "items": {"type": "string"},
        },
        "decision_impact_hint": {"type": "string"},
        "reasoning_summary": {"type": "string"},
    },
    "required": [
        "latest_question",
        "question_focus",
        "answerability",
        "direct_answer",
        "operator_dialogue",
        "checked_evidence_count",
        "explicit_support_count",
        "contradiction_count",
        "unknown_count",
        "supporting_evidence",
        "evidence_gaps",
        "decision_impact_hint",
        "reasoning_summary",
    ],
    "additionalProperties": False,
}

EVIDENCE_SYNTHESIS_RESPONSE_FORMAT = ResponseFormatJsonSchemaType(
    json_schema=ResponseFormatJsonSchema(
        name="gmp_evidence_synthesis",
        description="Compact explicit-evidence brief for Orchestrator and operator follow-up answers",
        schema=EVIDENCE_SYNTHESIS_SCHEMA,
    )
)

# ── Strict JSON schema for final Orchestrator response_format ──────────
# Enforces exact field names, types, and structure at API level.
FINAL_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "incident_id": {"type": "string"},
        "title": {"type": "string"},
        "classification": {
            "type": "string",
            "enum": [
                "process_parameter_excursion",
                "equipment_malfunction",
                "contamination",
                "documentation_gap",
                "other",
            ],
        },
        "risk_level": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"],
        },
        "confidence": {"type": "number"},
        "confidence_flag": {"type": ["string", "null"]},
        "root_cause": {"type": "string"},
        "analysis": {"type": "string"},
        "recommendation": {"type": "string"},
        "agent_recommendation": {
            "type": "string",
            "enum": ["APPROVE", "REJECT"],
        },
        "agent_recommendation_rationale": {"type": "string"},
        "operator_dialogue": {"type": "string"},
        "capa_suggestion": {"type": "string"},
        "regulatory_reference": {"type": "string"},
        "batch_disposition": {
            "type": "string",
            "enum": [
                "conditional_release_pending_testing",
                "rejected",
                "release",
                "hold_pending_review",
            ],
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "priority": {"type": "string"},
                    "owner": {"type": "string"},
                    "deadline_days": {"type": "integer"},
                },
                "required": ["action", "priority", "owner", "deadline_days"],
                "additionalProperties": False,
            },
        },
        "regulatory_refs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "regulation": {"type": "string"},
                    "section": {"type": "string"},
                    "text_excerpt": {"type": "string"},
                },
                "required": ["regulation", "section", "text_excerpt"],
                "additionalProperties": False,
            },
        },
        "sop_refs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "relevant_section": {"type": "string"},
                    "text_excerpt": {"type": "string"},
                },
                "required": ["id", "title", "relevant_section", "text_excerpt"],
                "additionalProperties": False,
            },
        },
        "evidence_citations": {
            "type": "array",
            "items": CANONICAL_EVIDENCE_CITATION_SCHEMA,
        },
        "work_order_draft": {
            "type": ["object", "null"],
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "priority": {"type": "string"},
                "estimated_hours": {"type": "integer"},
            },
            "required": ["title", "description", "priority", "estimated_hours"],
            "additionalProperties": False,
        },
        "audit_entry_draft": {
            "type": "object",
            "properties": {
                "deviation_type": {"type": "string"},
                "description": {"type": "string"},
                "root_cause": {"type": "string"},
                "capa_actions": {"type": "string"},
            },
            "required": ["deviation_type", "description", "root_cause", "capa_actions"],
            "additionalProperties": False,
        },
        "tool_calls_log": {
            "type": "array",
            "items": TOOL_CALL_LOG_ENTRY_SCHEMA,
        },
        "work_order_id": {"type": ["string", "null"]},
        "audit_entry_id": {"type": ["string", "null"]},
        "execution_error": {"type": ["string", "null"]},
    },
    "required": [
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
        "regulatory_refs",
        "sop_refs",
        "evidence_citations",
        "work_order_draft",
        "audit_entry_draft",
        "tool_calls_log",
        "work_order_id",
        "audit_entry_id",
    ],
    "additionalProperties": False,
}

FINAL_ANALYSIS_RESPONSE_FORMAT = ResponseFormatJsonSchemaType(
    json_schema=ResponseFormatJsonSchema(
        name="gmp_deviation_analysis",
        description="Structured GMP deviation analysis with CAPA, regulatory refs, and audit trail",
        schema=FINAL_ANALYSIS_SCHEMA,
    )
)


DOCUMENT_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "incident_id": {"type": "string"},
        "work_order_draft": {
            "type": ["object", "null"],
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "priority": {"type": "string"},
                "estimated_hours": {"type": "integer"},
            },
            "required": ["title", "description", "priority", "estimated_hours"],
            "additionalProperties": False,
        },
        "audit_entry_draft": {
            "type": "object",
            "properties": {
                "deviation_type": {"type": "string"},
                "description": {"type": "string"},
                "root_cause": {"type": "string"},
                "capa_actions": {"type": "string"},
            },
            "required": ["deviation_type", "description", "root_cause", "capa_actions"],
            "additionalProperties": False,
        },
        "work_order_id": {"type": ["string", "null"]},
        "audit_entry_id": {"type": ["string", "null"]},
        "execution_error": {"type": ["string", "null"]},
    },
    "required": [
        "incident_id",
        "work_order_draft",
        "audit_entry_draft",
        "work_order_id",
        "audit_entry_id",
        "execution_error",
    ],
    "additionalProperties": False,
}

DOCUMENT_OUTPUT_RESPONSE_FORMAT = ResponseFormatJsonSchemaType(
    json_schema=ResponseFormatJsonSchema(
        name="gmp_document_outputs",
        description="Prepared QMS/CMMS document payloads and persisted record ids",
        schema=DOCUMENT_OUTPUT_SCHEMA,
    )
)


# ── OpenAPI spec builders ─────────────────────────────────────────────────

def _build_sentinel_db_spec(base_url: str) -> dict:
    """OpenAPI 3.0 spec for Sentinel DB REST endpoints (4 read operations)."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Sentinel DB API", "version": "1.0.0"},
        "servers": [{"url": base_url}],
        "paths": {
            "/api/equipment/{equipment_id}": {
                "get": {
                    "operationId": "get_equipment",
                    "summary": "Get equipment master data by equipment_id (e.g. GR-204). Returns validated_parameters (PAR ranges), calibration dates, PM schedule, associated SOPs, criticality, location.",
                    "parameters": [
                        {"name": "equipment_id", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Equipment ID, e.g. GR-204"}
                    ],
                    "responses": {"200": {"description": "Equipment document"}, "404": {"description": "Not found"}},
                }
            },
            "/api/batches/{batch_id}": {
                "get": {
                    "operationId": "get_batch",
                    "summary": "Get batch context by batch_id (e.g. BATCH-2026-0416-GR204). Returns product name, batch number, BPR reference, current stage/step, process parameters, operator/supervisor IDs.",
                    "parameters": [
                        {"name": "batch_id", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Batch ID, e.g. BATCH-2026-0416-GR204"}
                    ],
                    "responses": {"200": {"description": "Batch document"}, "404": {"description": "Not found"}},
                }
            },
            "/api/incidents/{incident_id}": {
                "get": {
                    "operationId": "get_incident",
                    "summary": "Get incident document by incident_id (e.g. INC-2026-0001). Returns deviation details, AI analysis (risk_level, recommendation, confidence), workflow state.",
                    "parameters": [
                        {"name": "incident_id", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Incident ID, e.g. INC-2026-0001"}
                    ],
                    "responses": {"200": {"description": "Incident document"}, "404": {"description": "Not found"}},
                }
            },
            "/api/equipment/{equipment_id}/incidents": {
                "get": {
                    "operationId": "search_incidents",
                    "summary": "Find recent incidents for a given equipment_id, sorted newest first. Use to find historical cases and patterns.",
                    "parameters": [
                        {"name": "equipment_id", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Equipment ID"},
                        {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer", "default": 5}, "description": "Max results"},
                    ],
                    "responses": {"200": {"description": "List of incidents"}},
                }
            },
        },
    }


def _build_sentinel_search_spec(base_url: str) -> dict:
    """OpenAPI 3.0 spec for Sentinel Search REST endpoints (5 search operations)."""
    search_result_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "required": [
                "document_id",
                "document_title",
                "document_type",
                "chunk_index",
                "text",
                "source",
                "score",
            ],
            "properties": {
                "document_id": {"type": "string"},
                "document_title": {"type": "string"},
                "document_type": {"type": "string"},
                "chunk_index": {"type": "integer"},
                "section_heading": {"type": "string"},
                "section_key": {"type": "string"},
                "section_path": {"type": "string"},
                "text": {"type": "string"},
                "keywords": {},
                "source": {
                    "type": "string",
                    "description": "Exact blob file name. Copy this value to citation source_blob.",
                },
                "score": {"type": "number"},
            },
            "additionalProperties": True,
        },
    }

    def _search_path(path: str, op_id: str, summary: str, has_equipment: bool = False) -> dict:
        params = [
            {"name": "query", "in": "query", "required": True, "schema": {"type": "string"}, "description": "Natural language search query"},
            {"name": "top_k", "in": "query", "required": False, "schema": {"type": "integer", "default": 5}, "description": "Number of results"},
        ]
        if has_equipment:
            params.append({"name": "equipment_id", "in": "query", "required": False, "schema": {"type": "string"}, "description": "Filter by equipment ID"})
        return {
            path: {
                "get": {
                    "operationId": op_id,
                    "summary": summary,
                    "parameters": params,
                    "responses": {
                        "200": {
                            "description": "Search results with canonical document metadata. The `source` field is the exact blob file name and must be copied to citation `source_blob`.",
                            "content": {"application/json": {"schema": search_result_schema}},
                        }
                    },
                }
            }
        }

    paths = {}
    for p in [
        _search_path("/api/search/sop", "search_sop_documents",
                      "Semantic + vector search in Standard Operating Procedures (SOPs). Find relevant SOP sections for GMP deviation investigation."),
        _search_path("/api/search/manuals", "search_equipment_manuals",
                      "Semantic + vector search in equipment technical manuals. Find maintenance procedures, alarm codes, troubleshooting guides.", has_equipment=True),
        _search_path("/api/search/bpr", "search_bpr_documents",
                      "Semantic + vector search in Batch Production Records (BPR) and product process specs. BPR ranges (NOR/PAR) are product-specific.", has_equipment=True),
        _search_path("/api/search/gmp", "search_gmp_policies",
                      "Semantic + vector search in GMP regulations and internal quality policies. Cite applicable regulatory requirements."),
        _search_path("/api/search/incidents", "search_incident_history",
                      "Semantic + vector search in historical GMP deviation incidents. Find similar past cases, same equipment, same deviation type.", has_equipment=True),
    ]:
        paths.update(p)

    return {
        "openapi": "3.0.0",
        "info": {"title": "Sentinel Search API", "version": "1.0.0"},
        "servers": [{"url": base_url}],
        "paths": paths,
    }


def _build_qms_spec(base_url: str) -> dict:
    """OpenAPI 3.0 spec for QMS REST endpoint (create audit entry)."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Sentinel QMS API", "version": "1.0.0"},
        "servers": [{"url": base_url}],
        "paths": {
            "/api/audit-entries": {
                "post": {
                    "operationId": "create_audit_entry",
                    "summary": "Create a GMP-compliant deviation audit entry in the Quality Management System. Records deviation investigation, root cause, CAPA, and batch disposition.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["incident_id", "equipment_id", "deviation_type", "description", "root_cause", "capa_actions", "batch_disposition", "prepared_by"],
                                    "properties": {
                                        "incident_id": {"type": "string", "description": "Source incident ID (e.g. INC-2026-0001)"},
                                        "equipment_id": {"type": "string", "description": "Equipment where deviation occurred (e.g. GR-204)"},
                                        "deviation_type": {"type": "string", "description": "Classification: process_parameter_excursion | equipment_malfunction"},
                                        "description": {"type": "string", "description": "Factual description of the deviation event"},
                                        "root_cause": {"type": "string", "description": "Root cause investigation summary"},
                                        "capa_actions": {"type": "string", "description": "Numbered CAPA actions (immediate + short-term + long-term)"},
                                        "batch_disposition": {"type": "string", "description": "conditional_release_pending_testing | rejected | release"},
                                        "prepared_by": {"type": "string", "description": "User ID of QA person preparing the entry"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {"201": {"description": "Audit entry created"}, "400": {"description": "Validation error"}},
                }
            }
        },
    }


def _build_cmms_spec(base_url: str) -> dict:
    """OpenAPI 3.0 spec for CMMS REST endpoint (create work order)."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Sentinel CMMS API", "version": "1.0.0"},
        "servers": [{"url": base_url}],
        "paths": {
            "/api/work-orders": {
                "post": {
                    "operationId": "create_work_order",
                    "summary": "Create a corrective maintenance work order in the CMMS. Schedules equipment inspection or repair following a GMP deviation.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["incident_id", "equipment_id", "title", "description", "priority", "assigned_to", "due_date", "work_type"],
                                    "properties": {
                                        "incident_id": {"type": "string", "description": "Source incident ID for traceability (e.g. INC-2026-0001)"},
                                        "equipment_id": {"type": "string", "description": "Equipment to be serviced (e.g. GR-204)"},
                                        "title": {"type": "string", "description": "Short work order title (max 120 chars)"},
                                        "description": {"type": "string", "description": "Detailed description of required maintenance/inspection work"},
                                        "priority": {"type": "string", "enum": ["urgent", "high", "medium", "low"], "description": "Priority level"},
                                        "assigned_to": {"type": "string", "description": "Technician username or team name"},
                                        "due_date": {"type": "string", "description": "Completion deadline in ISO 8601 format (e.g. 2026-04-25)"},
                                        "work_type": {"type": "string", "enum": ["corrective", "preventive", "inspection"], "description": "Type of work"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {"201": {"description": "Work order created"}, "400": {"description": "Validation error"}},
                }
            }
        },
    }


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
    credential_mode = os.environ.get("FOUNDRY_AGENT_CREDENTIAL", "azurecli").strip().lower()
    if credential_mode == "default":
        credential = DefaultAzureCredential()
    else:
        credential = AzureCliCredential()
    return AgentsClient(endpoint=endpoint, credential=credential)


def _http_status_code(exc: HttpResponseError) -> int | None:
    status = getattr(exc, "status_code", None)
    if status is not None:
        return int(status)
    response = getattr(exc, "response", None)
    if response is None:
        return None
    response_status = getattr(response, "status_code", None)
    if response_status is None:
        return None
    return int(response_status)


def _is_transient_foundry_error(exc: HttpResponseError) -> bool:
    status = _http_status_code(exc)
    if status in _TRANSIENT_FOUNDRY_STATUS_CODES:
        return True
    message = str(exc).lower()
    return status is None and "server had an error processing your request" in message


def _call_foundry_with_retry(operation_name: str, func, *args, **kwargs):
    last_error: HttpResponseError | None = None
    for attempt in range(1, _FOUNDRY_RETRY_ATTEMPTS + 1):
        try:
            return func(*args, **kwargs)
        except HttpResponseError as exc:
            last_error = exc
            if not _is_transient_foundry_error(exc) or attempt >= _FOUNDRY_RETRY_ATTEMPTS:
                raise

            delay_seconds = _FOUNDRY_RETRY_BASE_SECONDS * (2 ** (attempt - 1))
            status = _http_status_code(exc)
            print(
                f"  WARN: transient Foundry error during {operation_name} "
                f"(status={status or 'unknown'}, attempt {attempt}/{_FOUNDRY_RETRY_ATTEMPTS}). "
                f"Retrying in {delay_seconds:.1f}s...",
                file=sys.stderr,
            )
            if delay_seconds > 0:
                time.sleep(delay_seconds)

    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Foundry operation {operation_name} did not return a result")


def _find_existing(client: AgentsClient, name: str):
    for agent in _call_foundry_with_retry("list_agents", client.list_agents):
        if agent.name == name:
            return agent
    return None


def _create_or_update(
    client: AgentsClient,
    name: str,
    model: str,
    instructions: str,
    tools: list[ToolDefinition],
    tool_resources=None,
    update: bool = False,
    response_format=None,
):
    existing = _find_existing(client, name)
    if existing and not update:
        print(f"  '{name}' already exists (id={existing.id}) — use --update to overwrite")
        return existing

    kwargs: dict = dict(
        model=model, name=name, instructions=instructions, tools=tools,
        temperature=TEMPERATURE, top_p=TOP_P,
    )
    if tool_resources is not None:
        kwargs["tool_resources"] = tool_resources
    if response_format is not None:
        kwargs["response_format"] = response_format

    if existing and update:
        agent = _call_foundry_with_retry(
            f"update_agent:{name}",
            client.update_agent,
            agent_id=existing.id,
            **kwargs,
        )
        print(f"  Updated '{name}' (id={agent.id})")
    else:
        agent = _call_foundry_with_retry(
            f"create_agent:{name}",
            client.create_agent,
            **kwargs,
        )
        print(f"  Created '{name}' (id={agent.id})")
    return agent


def main(update: bool = False) -> dict:
    # Container App base URLs (strip /mcp suffix if present)
    def _base_url(env_var: str) -> str:
        url = os.environ.get(env_var, "").strip()
        return url.removesuffix("/mcp").removesuffix("/mcp/")

    print("Using Foundry agent model deployments:")
    print(f"  research: {RESEARCH_MODEL}")
    print(f"  evidence_synthesizer: {EVIDENCE_SYNTHESIZER_MODEL}")
    print(f"  document: {DOCUMENT_MODEL}")
    print(f"  orchestrator: {ORCHESTRATOR_MODEL}")

    mcp_db_url = _base_url("MCP_SENTINEL_DB_URL")
    mcp_search_url = _base_url("MCP_SENTINEL_SEARCH_URL")
    mcp_qms_url = _base_url("MCP_QMS_URL")
    mcp_cmms_url = _base_url("MCP_CMMS_URL")

    if not any([mcp_db_url, mcp_search_url, mcp_qms_url, mcp_cmms_url]):
        print(
            "  INFO: No MCP_*_URL env vars set — OpenAPI tools disabled.\n"
            "  Build and deploy MCP Container Apps first:\n"
            "    bash backend/scripts/deploy-mcp.sh --acr-build\n"
            "  Then set MCP_SENTINEL_DB_URL, MCP_SENTINEL_SEARCH_URL, "
            "MCP_QMS_URL, MCP_CMMS_URL."
        )

    anon_auth = OpenApiAnonymousAuthDetails()
    client = _build_client()

    # ── 1. Research Agent (T-025) ─────────────────────────────────────────
    print("\n[1/3] Research Agent...")

    research_tools: list[ToolDefinition] = []

    # OpenApiTool: sentinel-db (equipment / batch / incident context)
    if mcp_db_url:
        db_spec = _build_sentinel_db_spec(mcp_db_url)
        db_tool = OpenApiTool(
            name="sentinel_db",
            description=(
                "Read-only access to Sentinel Cosmos DB: equipment master data, "
                "batch context, incident documents, and historical incidents."
            ),
            spec=db_spec,
            auth=anon_auth,
        )
        research_tools = research_tools + db_tool.definitions  # type: ignore[operator]
        print(f"  + OpenAPI sentinel-db: {mcp_db_url}")

    # OpenApiTool: sentinel-search (5-index RAG: SOP, manuals, BPR, GMP, incidents)
    if mcp_search_url:
        search_spec = _build_sentinel_search_spec(mcp_search_url)
        search_openapi = OpenApiTool(
            name="sentinel_search",
            description=(
                "Semantic + vector search across 5 Azure AI Search indexes: "
                "SOPs, equipment manuals, BPR documents, GMP policies, incident history."
            ),
            spec=search_spec,
            auth=anon_auth,
        )
        research_tools = research_tools + search_openapi.definitions  # type: ignore[operator]
        print(f"  + OpenAPI sentinel-search: {mcp_search_url}")

    research_agent = _create_or_update(
        client, "sentinel-research-agent", RESEARCH_MODEL, RESEARCH_PROMPT,
        research_tools, None, update,
    )

    # ── 2. Evidence Synthesizer Agent ─────────────────────────────────────
    print("\n[2/4] Evidence Synthesizer Agent...")
    evidence_synthesizer_agent = _create_or_update(
        client,
        "sentinel-evidence-synthesizer-agent",
        EVIDENCE_SYNTHESIZER_MODEL,
        EVIDENCE_SYNTHESIZER_PROMPT,
        [],
        None,
        update,
        response_format=EVIDENCE_SYNTHESIS_RESPONSE_FORMAT,
    )

    # ── 3. Document Agent (T-026) ─────────────────────────────────────────
    print("\n[3/4] Document Agent...")

    document_tools: list[ToolDefinition] = []

    if mcp_qms_url or mcp_cmms_url:
        print(
            "  + Write-side QMS/CMMS tools remain detached from the Document Agent; "
            "backend persists audit/work-order records only after human approval."
        )

    document_agent = _create_or_update(
        client, "sentinel-document-agent", DOCUMENT_MODEL, DOCUMENT_PROMPT,
        document_tools, None, update,
        response_format=DOCUMENT_OUTPUT_RESPONSE_FORMAT,
    )

    # ── 4. Orchestrator Agent (T-024, ADR-002) ────────────────────────────
    print("\n[4/4] Orchestrator Agent...")
    orchestrator_agent = _create_or_update(
        client, "sentinel-orchestrator-agent", ORCHESTRATOR_MODEL, ORCHESTRATOR_PROMPT,
        [],
        None,
        update,
        response_format=FINAL_ANALYSIS_RESPONSE_FORMAT,
    )

    print("\n" + "=" * 60)
    print("Agents provisioned. Add to local.settings.json / Azure App Settings:\n")
    print(f"  RESEARCH_AGENT_ID={research_agent.id}")
    print(f"  EVIDENCE_SYNTHESIZER_AGENT_ID={evidence_synthesizer_agent.id}")
    print(f"  DOCUMENT_AGENT_ID={document_agent.id}")
    print(f"  ORCHESTRATOR_AGENT_ID={orchestrator_agent.id}")
    print("=" * 60)

    return {
        "research_agent_id": research_agent.id,
        "evidence_synthesizer_agent_id": evidence_synthesizer_agent.id,
        "document_agent_id": document_agent.id,
        "orchestrator_agent_id": orchestrator_agent.id,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provision Sentinel Foundry agents")
    parser.add_argument("--update", action="store_true", help="Update existing agents")
    args = parser.parse_args()
    main(update=args.update)
