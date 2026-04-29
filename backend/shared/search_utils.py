"""
search_utils.py — Azure AI Search hybrid (vector + keyword) search helpers.

Used by:
  - backend/mcp_sentinel_search/server.py  (MCP server tools)
  - backend/activities/run_foundry_agents.py (pre-fetch RAG context)

All 5 indexes share the same field schema:
  id, document_id, document_title, document_type, chunk_index,
    section_heading, section_key, section_path,
    text, embedding, equipment_ids, keywords, source_blob
"""

import os
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

# ── Config ────────────────────────────────────────────────────────────────

SEARCH_ENDPOINT = os.getenv(
    "AZURE_SEARCH_ENDPOINT",
    "https://srch-sentinel-intel-dev-erzrpo.search.windows.net",
)
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY", "") or os.getenv("AZURE_SEARCH_ADMIN_KEY", "")

OPENAI_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT",
    "https://oai-sentinel-intel-dev-erzrpo.openai.azure.com/",
)
OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = int(os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSIONS", "1536"))
RAG_ENFORCE_SAFETY_FILTER = os.getenv("RAG_ENFORCE_SAFETY_FILTER", "true").lower() == "true"

DEFAULT_TOP_K = 5

# Index names
IDX_SOP = "idx-sop-documents"
IDX_MANUALS = "idx-equipment-manuals"
IDX_BPR = "idx-bpr-documents"
IDX_GMP = "idx-gmp-policies"
IDX_INCIDENTS = "idx-incident-history"

ALL_INDEXES = [IDX_SOP, IDX_MANUALS, IDX_BPR, IDX_GMP, IDX_INCIDENTS]

# ── Clients ───────────────────────────────────────────────────────────────

_oai_client: AzureOpenAI | None = None


def _get_oai_client() -> AzureOpenAI:
    global _oai_client
    if _oai_client is None:
        _oai_client = AzureOpenAI(
            azure_endpoint=OPENAI_ENDPOINT,
            api_key=OPENAI_API_KEY or None,
            api_version="2024-02-01",
        )
    return _oai_client


def _get_search_client(index_name: str) -> SearchClient:
    credential = (
        AzureKeyCredential(SEARCH_KEY) if SEARCH_KEY else DefaultAzureCredential()
    )
    return SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=index_name,
        credential=credential,
    )


def embed(text: str) -> list[float]:
    """Generate embedding vector for the given text."""
    response = _get_oai_client().embeddings.create(
        model=EMBEDDING_DEPLOYMENT,
        input=text,
        dimensions=EMBEDDING_DIMENSIONS,
    )
    return response.data[0].embedding


def _build_effective_filter(filter_expr: str | None) -> str | None:
    if not RAG_ENFORCE_SAFETY_FILTER:
        return filter_expr
    safety_filter = "allowed_for_rag eq true"
    if filter_expr:
        return f"({filter_expr}) and ({safety_filter})"
    return safety_filter


def search_index(
    index_name: str,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    filter_expr: str | None = None,
) -> list[dict[str, Any]]:
    """
    Hybrid search (keyword + vector) on a single AI Search index.

    Returns list of result dicts: document_id, document_title, document_type,
    chunk_index, section metadata, text, keywords, source, score.
    """
    vector = embed(query)
    vector_query = VectorizedQuery(
        vector=vector,
        k_nearest_neighbors=top_k,
        fields="embedding",
    )

    client = _get_search_client(index_name)
    effective_filter = _build_effective_filter(filter_expr)

    try:
        results = client.search(
            search_text=query,
            vector_queries=[vector_query],
            filter=effective_filter,
            top=top_k,
            select=[
                "id", "document_id", "document_title", "document_type",
                "chunk_index", "section_heading", "section_key", "section_path",
                "text", "keywords", "equipment_ids", "source_blob",
            ],
        )
    except Exception:
        # Backward compatibility for environments where indexes were not yet migrated
        # with the `allowed_for_rag` field.
        if effective_filter == filter_expr:
            raise
        results = client.search(
            search_text=query,
            vector_queries=[vector_query],
            filter=filter_expr,
            top=top_k,
            select=[
                "id", "document_id", "document_title", "document_type",
                "chunk_index", "section_heading", "section_key", "section_path",
                "text", "keywords", "equipment_ids", "source_blob",
            ],
        )

    return [
        {
            "document_id": r.get("document_id", ""),
            "document_title": r.get("document_title", ""),
            "document_type": r.get("document_type", ""),
            "chunk_index": r.get("chunk_index", 0),
            "section_heading": r.get("section_heading", ""),
            "section_key": r.get("section_key", ""),
            "section_path": r.get("section_path", ""),
            "text": r.get("text", ""),
            "keywords": r.get("keywords", []),
            "equipment_ids": r.get("equipment_ids", []),
            "source": r.get("source_blob", ""),
            "score": r.get("@search.score", 0.0),
        }
        for r in results
    ]


def search_all_indexes(
    query: str,
    equipment_id: str | None = None,
    top_k: int = 3,
) -> dict[str, list[dict[str, Any]]]:
    """
    Search all 5 indexes in parallel and return a dict keyed by index name.

    Used by run_foundry_agents.py to pre-fetch RAG context before calling
    the Foundry Orchestrator Agent.

    Args:
        query:        Free-text query derived from the incident alert.
        equipment_id: Optional — used to filter equipment-specific indexes.
        top_k:        Results per index (default 3, yields ≤15 total chunks).
    """
    eq_filter = (
        f"equipment_ids/any(e: e eq '{equipment_id}')" if equipment_id else None
    )

    # For SOPs: prefer equipment-specific results (filtered), fall back to
    # unfiltered so generic SOPs (e.g. SOP-DEV-001) are still returned when
    # no equipment-tagged SOPs exist in the index.
    sop_results = search_index(IDX_SOP, query, top_k, eq_filter) if eq_filter else []
    if not sop_results:
        sop_results = search_index(IDX_SOP, query, top_k)

    return {
        IDX_SOP: sop_results,
        IDX_MANUALS: search_index(IDX_MANUALS, query, top_k, eq_filter),
        IDX_BPR: search_index(IDX_BPR, query, top_k, eq_filter),
        IDX_GMP: search_index(IDX_GMP, query, top_k),
        IDX_INCIDENTS: search_index(IDX_INCIDENTS, query, top_k, eq_filter),
    }
