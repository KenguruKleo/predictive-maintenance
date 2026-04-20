"""Helpers for Azure AI Search incident-history indexing."""

from __future__ import annotations

import json
import os
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient

from shared.search_utils import SEARCH_ENDPOINT, embed

HISTORY_INDEX_NAME = os.getenv("AZURE_INCIDENT_HISTORY_INDEX", "idx-incident-history")
SEARCH_WRITE_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY") or os.getenv("AZURE_SEARCH_KEY", "")


def is_historical_incident_eligible(incident: dict) -> bool:
    status = str(incident.get("status") or "").strip().lower()
    if status not in {"closed", "completed"}:
        return False

    if incident.get("approvedAt") or incident.get("approvedBy") or incident.get("approved_by"):
        return True

    final_decision = incident.get("finalDecision")
    if isinstance(final_decision, dict) and str(final_decision.get("action") or "").lower() == "approved":
        return True

    return False


def incident_to_history_source_doc(incident: dict) -> dict | None:
    incident_id = str(incident.get("id") or "").strip()
    if not incident_id or not is_historical_incident_eligible(incident):
        return None

    ai = incident.get("ai_analysis") or {}
    equipment_id = _first_non_empty(incident.get("equipment_id"), incident.get("equipmentId"))
    title = _first_non_empty(incident.get("title"), incident_id)
    severity = _first_non_empty(incident.get("severity"), "unknown")
    reported_at = _first_non_empty(incident.get("reported_at"), incident.get("reportedAt"))
    deviation_type = _first_non_empty(incident.get("deviation_type"), incident.get("deviationType"))
    description = _stringify_text(_first_non_empty(incident.get("description"), incident.get("summary")))
    root_cause = _stringify_text(_first_non_empty(ai.get("root_cause_hypothesis"), ai.get("root_cause")))
    classification = _stringify_text(ai.get("classification"))
    risk_level = _stringify_text(ai.get("risk_level"))
    recommendation = _stringify_text(_first_non_empty(ai.get("recommendation"), ai.get("recommendations")))
    capa = _stringify_text(_first_non_empty(ai.get("capa_suggestion"), ai.get("capa_plan"), ai.get("work_order_draft")))
    regulatory_reference = _stringify_text(_first_non_empty(ai.get("regulatory_reference"), ai.get("regulatory_refs")))
    batch_disposition = _stringify_text(ai.get("batch_disposition"))

    text = "\n".join(
        [
            f"Incident ID: {incident_id}",
            f"Equipment: {equipment_id} — {title}" if equipment_id else f"Equipment: {title}",
            f"Status: {incident.get('status')} | Severity: {severity} | Date: {reported_at[:10]}",
            f"Deviation type: {deviation_type}",
            f"Description: {description}",
            f"Root cause: {root_cause}",
            f"Classification: {classification}",
            f"Risk level: {risk_level}",
            f"Recommendation: {recommendation}",
            f"CAPA: {capa}",
            f"Regulatory reference: {regulatory_reference}",
            f"Batch disposition: {batch_disposition}",
        ]
    ).strip()

    return {
        "filename": f"{incident_id}.txt",
        "text": text,
        "document_title": title,
        "equipment_ids": [equipment_id] if equipment_id else [],
    }


def build_history_source_documents(incidents: list[dict]) -> list[dict]:
    docs: list[dict] = []
    for incident in incidents:
        doc = incident_to_history_source_doc(incident)
        if doc:
            docs.append(doc)
    return docs


def build_history_index_documents(incident: dict) -> list[dict[str, Any]]:
    source_doc = incident_to_history_source_doc(incident)
    if not source_doc:
        return []

    incident_id = str(incident.get("id") or "").strip()
    text = source_doc["text"]
    return [
        {
            "id": f"{incident_id}-chunk-000",
            "document_id": incident_id,
            "document_title": source_doc["document_title"],
            "document_type": "incident_history",
            "chunk_index": 0,
            "section_heading": "Incident summary",
            "section_key": "incident-summary",
            "section_path": "Incident summary",
            "text": text,
            "embedding": embed(text),
            "equipment_ids": source_doc["equipment_ids"],
            "keywords": "",
            "source_blob": source_doc["filename"],
        }
    ]


def sync_historical_incident(incident: dict) -> dict:
    incident_id = str(incident.get("id") or "").strip()
    if not incident_id:
        return {"action": "skipped", "reason": "missing incident id"}

    client = _get_search_client()
    if is_historical_incident_eligible(incident):
        documents = build_history_index_documents(incident)
        if not documents:
            return {"action": "skipped", "reason": "incident not eligible"}
        client.upload_documents(documents=documents)
        return {"action": "upserted", "count": len(documents), "incident_id": incident_id}

    deleted = delete_historical_incident(incident_id, client=client)
    return {"action": "deleted", "count": deleted, "incident_id": incident_id}


def delete_historical_incident(incident_id: str, *, client: SearchClient | None = None) -> int:
    search_client = client or _get_search_client()
    results = search_client.search(
        search_text="*",
        filter=f"document_id eq '{_escape_filter_value(incident_id)}'",
        top=100,
        select=["id"],
    )
    doc_ids = [{"id": item["id"]} for item in results if item.get("id")]
    if not doc_ids:
        return 0
    search_client.delete_documents(documents=doc_ids)
    return len(doc_ids)


def _get_search_client() -> SearchClient:
    credential = AzureKeyCredential(SEARCH_WRITE_KEY) if SEARCH_WRITE_KEY else DefaultAzureCredential()
    return SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=HISTORY_INDEX_NAME,
        credential=credential,
    )


def _escape_filter_value(value: str) -> str:
    return str(value).replace("'", "''")


def _first_non_empty(*values: object) -> str:
    for value in values:
        text = _stringify_text(value)
        if text:
            return text
    return ""


def _stringify_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        parts = [_stringify_text(item) for item in value]
        return "\n".join(part for part in parts if part)
    if isinstance(value, dict):
        preferred = _first_non_empty(
            value.get("summary"),
            value.get("action"),
            value.get("title"),
            value.get("description"),
            value.get("text"),
        )
        if preferred:
            return preferred
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).strip()