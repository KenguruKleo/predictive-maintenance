"""App Insights telemetry query + normalization helpers for T-043.

This module keeps the HTTP trigger thin and provides pure functions that can be
unit tested without Azure dependencies.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import timedelta
from typing import Any

from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus

logger = logging.getLogger(__name__)

TRACE_MARKER = "FOUNDRY_PROMPT_TRACE"
RESOURCE_ID_ENV = "APPLICATIONINSIGHTS_RESOURCE_ID"
DEFAULT_QUERY_DAYS = 14
ALLOWED_AGENT_NAMES = {"orchestrator", "research", "document", "execution", "tool"}
ALLOWED_STATUSES = {"started", "completed", "failed"}

TRACE_TITLES = {
    "prompt_context": "Prompt Context",
    "orchestrator_user_prompt": "User Prompt",
    "thread_messages": "Thread Messages",
    "raw_response": "Raw Response",
    "parsed_response": "Parsed Response",
    "normalized_result": "Normalized Result",
}

TRACE_STATUS = {
    "prompt_context": "started",
    "orchestrator_user_prompt": "started",
    "thread_messages": "completed",
    "raw_response": "completed",
    "parsed_response": "completed",
    "normalized_result": "completed",
}

_SAFE_INCIDENT_ID = re.compile(r"^[A-Za-z0-9._:-]+$")
_client: LogsQueryClient | None = None


class TelemetryConfigError(RuntimeError):
    """Raised when telemetry query configuration is missing or invalid."""


def query_incident_agent_telemetry(
    incident_id: str,
    *,
    agent_name: str | None = None,
    status: str | None = None,
    round_number: int | None = None,
) -> dict[str, Any]:
    """Query App Insights traces and return a normalized incident response."""
    validated_incident_id = validate_incident_id(incident_id)
    rows = _query_trace_rows(validated_incident_id)
    items = normalize_trace_rows(rows)
    filtered = filter_telemetry_items(
        items,
        agent_name=agent_name,
        status=status,
        round_number=round_number,
    )

    return {
        "incident_id": validated_incident_id,
        "summary": build_telemetry_summary(filtered),
        "items": filtered,
        "query": {
            "agent_name": agent_name,
            "status": status,
            "round": round_number,
        },
        "scope": {
            "source": "app_insights",
            "view": "backend_visible_foundry_trace",
            "limitations": [
                "Current SDK traces cover the backend-visible Foundry path only.",
                "Connected sub-agent internal steps are not fully exposed by the SDK.",
            ],
        },
    }


def validate_incident_id(incident_id: str) -> str:
    """Reject unsafe incident identifiers before embedding in KQL."""
    value = incident_id.strip()
    if not value:
        raise ValueError("incident_id is required")
    if not _SAFE_INCIDENT_ID.fullmatch(value):
        raise ValueError("incident_id contains unsupported characters")
    return value


def validate_agent_name(agent_name: str | None) -> str | None:
    """Validate optional agent_name filter."""
    if agent_name is None or not str(agent_name).strip():
        return None
    value = str(agent_name).strip().lower()
    if value not in ALLOWED_AGENT_NAMES:
        raise ValueError(f"agent_name must be one of: {sorted(ALLOWED_AGENT_NAMES)}")
    return value


def validate_status(status: str | None) -> str | None:
    """Validate optional status filter."""
    if status is None or not str(status).strip():
        return None
    value = str(status).strip().lower()
    if value not in ALLOWED_STATUSES:
        raise ValueError(f"status must be one of: {sorted(ALLOWED_STATUSES)}")
    return value


def normalize_trace_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge chunked App Insights trace rows into timeline items."""
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            int(row.get("round") or 0),
            str(row.get("trace_kind") or ""),
            str(row.get("metadata") or "{}"),
            int(row.get("chunk_index") or 0),
            str(row.get("timestamp") or ""),
        ),
    )

    groups: dict[tuple[int, str, str], dict[str, Any]] = {}
    for row in sorted_rows:
        round_number = int(row.get("round") or 0)
        trace_kind = str(row.get("trace_kind") or "unknown").strip() or "unknown"
        metadata_text = str(row.get("metadata") or "{}")
        key = (round_number, trace_kind, metadata_text)

        if key not in groups:
            groups[key] = {
                "timestamp": row.get("timestamp") or "",
                "round": round_number,
                "trace_kind": trace_kind,
                "content_type": row.get("content_type") or "text",
                "metadata_text": metadata_text,
                "chunk_count": int(row.get("chunk_count") or 1),
                "chunks": [],
            }

        groups[key]["chunks"].append(
            (int(row.get("chunk_index") or 1), str(row.get("content") or ""))
        )
        groups[key]["chunk_count"] = max(
            groups[key]["chunk_count"],
            int(row.get("chunk_count") or 1),
        )

        timestamp = str(row.get("timestamp") or "")
        if timestamp and (not groups[key]["timestamp"] or timestamp < groups[key]["timestamp"]):
            groups[key]["timestamp"] = timestamp

    items: list[dict[str, Any]] = []
    for payload in groups.values():
        metadata = _parse_json_object(payload["metadata_text"])
        content = "".join(
            chunk for _, chunk in sorted(payload["chunks"], key=lambda item: item[0])
        )
        agent_name = _normalize_agent_name(metadata, payload["trace_kind"])
        status = str(metadata.get("status") or TRACE_STATUS.get(payload["trace_kind"], "completed"))
        item_id = _make_item_id(
            round_number=payload["round"],
            trace_kind=payload["trace_kind"],
            metadata_text=payload["metadata_text"],
        )
        items.append({
            "id": item_id,
            "timestamp": payload["timestamp"],
            "round": payload["round"],
            "trace_kind": payload["trace_kind"],
            "title": TRACE_TITLES.get(payload["trace_kind"], payload["trace_kind"].replace("_", " ").title()),
            "status": status,
            "agent_name": agent_name,
            "source": "app_insights",
            "content_type": payload["content_type"],
            "content": content,
            "preview": _build_preview(content),
            "metadata": metadata,
            "chunk_count": payload["chunk_count"],
            "content_length": len(content),
            "run_id": metadata.get("run_id"),
            "thread_id": metadata.get("thread_id"),
        })

    return sorted(items, key=lambda item: (item.get("timestamp") or "", int(item.get("round") or 0), str(item.get("trace_kind") or "")))


def filter_telemetry_items(
    items: list[dict[str, Any]],
    *,
    agent_name: str | None = None,
    status: str | None = None,
    round_number: int | None = None,
) -> list[dict[str, Any]]:
    """Apply optional filters to normalized telemetry items."""
    filtered = items
    if agent_name:
        filtered = [item for item in filtered if item.get("agent_name") == agent_name]
    if status:
        filtered = [item for item in filtered if item.get("status") == status]
    if round_number is not None:
        filtered = [item for item in filtered if int(item.get("round") or 0) == round_number]
    return filtered


def build_telemetry_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute summary metrics for the frontend KPI strip."""
    rounds = sorted({int(item.get("round") or 0) for item in items})
    trace_kinds = sorted({str(item.get("trace_kind") or "") for item in items})
    agent_names = sorted({str(item.get("agent_name") or "") for item in items if item.get("agent_name")})
    total_duration_ms = sum(
        int(item.get("metadata", {}).get("duration_ms") or 0)
        for item in items
        if isinstance(item.get("metadata"), dict)
    )

    return {
        "total_items": len(items),
        "started_items": sum(1 for item in items if item.get("status") == "started"),
        "completed_items": sum(1 for item in items if item.get("status") == "completed"),
        "failed_items": sum(1 for item in items if item.get("status") == "failed"),
        "rounds": rounds,
        "agent_names": agent_names,
        "trace_kinds": trace_kinds,
        "total_content_chars": sum(int(item.get("content_length") or 0) for item in items),
        "total_duration_ms": total_duration_ms or None,
        "last_timestamp": items[-1]["timestamp"] if items else None,
        "view_scope": "backend_visible_foundry_trace",
    }


def _query_trace_rows(incident_id: str) -> list[dict[str, Any]]:
    """Query App Insights resource logs for all trace rows of a given incident."""
    resource_id = os.getenv(RESOURCE_ID_ENV, "").strip()
    if not resource_id:
        raise TelemetryConfigError(
            f"{RESOURCE_ID_ENV} is not configured for telemetry queries"
        )

    query_days = _coerce_positive_int(os.getenv("AGENT_TELEMETRY_QUERY_DAYS", str(DEFAULT_QUERY_DAYS)), DEFAULT_QUERY_DAYS)
    client = _get_logs_query_client()
    query = _build_trace_query(incident_id)

    try:
        result = client.query_resource(
            resource_id,
            query,
            timespan=timedelta(days=query_days),
            server_timeout=30,
        )
    except HttpResponseError as exc:
        logger.exception("Agent telemetry App Insights query failed for %s: %s", incident_id, exc)
        raise RuntimeError("Failed to query App Insights telemetry") from exc

    tables = result.tables if result.status == LogsQueryStatus.SUCCESS else result.partial_data
    if result.status == LogsQueryStatus.PARTIAL:
        logger.warning("Agent telemetry query returned partial data for %s: %s", incident_id, result.partial_error)

    rows: list[dict[str, Any]] = []
    for table in tables or []:
        columns = [column.name for column in table.columns]
        for raw_row in table.rows:
            rows.append(dict(zip(columns, raw_row)))
    return rows


def _get_logs_query_client() -> LogsQueryClient:
    global _client
    if _client is None:
        _client = LogsQueryClient(DefaultAzureCredential())
    return _client


def _build_trace_query(incident_id: str) -> str:
    safe_incident_id = incident_id.replace('"', '\\"')
    return f"""
traces
| where message has \"{TRACE_MARKER}\"
| extend payload = parse_json(substring(message, indexof(message, \"{{\")))
| where tostring(payload.incident_id) == \"{safe_incident_id}\"
| project timestamp,
          trace_kind = tostring(payload.trace_kind),
          content_type = tostring(payload.content_type),
          round = toint(payload.round),
          chunk_index = toint(payload.chunk_index),
          chunk_count = toint(payload.chunk_count),
          metadata = tostring(payload.metadata),
          content = tostring(payload.content)
| order by timestamp asc, round asc, trace_kind asc, chunk_index asc
""".strip()


def _normalize_agent_name(metadata: dict[str, Any], trace_kind: str) -> str:
    if isinstance(metadata.get("agent_name"), str) and metadata["agent_name"].strip():
        return str(metadata["agent_name"]).strip().lower()
    return "orchestrator" if trace_kind else "tool"


def _parse_json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _build_preview(content: str, limit: int = 220) -> str:
    preview = " ".join((content or "").split())
    if len(preview) <= limit:
        return preview
    return preview[: limit - 1].rstrip() + "…"


def _make_item_id(*, round_number: int, trace_kind: str, metadata_text: str) -> str:
    digest = hashlib.sha1(f"{round_number}|{trace_kind}|{metadata_text}".encode("utf-8")).hexdigest()[:12]
    return f"telemetry-{round_number}-{trace_kind}-{digest}"


def _coerce_positive_int(raw_value: str, default: int) -> int:
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default