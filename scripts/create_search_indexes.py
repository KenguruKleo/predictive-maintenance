#!/usr/bin/env python3
"""
scripts/create_search_indexes.py
Create 5 Azure AI Search indexes, chunk & embed documents from Blob Storage,
and upsert chunks into the correct index.

Indexes created:
    idx-sop-documents     ← blob-sop/
    idx-equipment-manuals ← blob-manuals/
    idx-gmp-policies      ← blob-gmp/
    idx-bpr-documents     ← blob-bpr/   (table-aware chunking)
    idx-incident-history  ← generated from Cosmos DB closed incidents

Usage:
    python scripts/create_search_indexes.py                      # full run
    python scripts/create_search_indexes.py --skip-index-create  # only chunk+embed
    python scripts/create_search_indexes.py --indexes idx-sop-documents idx-bpr-documents
    python scripts/create_search_indexes.py --dry-run            # no writes
"""

import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from openai import AzureOpenAI

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from shared.history_index import build_history_source_documents
from shared.history_index import is_historical_incident_eligible

SEARCH_ENDPOINT = os.getenv(
    "AZURE_SEARCH_ENDPOINT",
    "https://srch-sentinel-intel-dev-erzrpo.search.windows.net",
)
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")

STORAGE_ACCOUNT = "stsentinelintelerzrpo"
COSMOS_ENDPOINT = "https://cosmos-sentinel-intel-dev-erzrpo.documents.azure.com:443/"
COSMOS_DB = "sentinel-intelligence"

EMBEDDING_DIMENSIONS = 1536

# index → blob container (or special source)
INDEX_SOURCES = {
    "idx-sop-documents": {"container": "blob-sop", "chunking": "standard"},
    "idx-equipment-manuals": {"container": "blob-manuals", "chunking": "standard"},
    "idx-gmp-policies": {"container": "blob-gmp", "chunking": "standard"},
    "idx-bpr-documents": {"container": "blob-bpr", "chunking": "table_aware"},
    "idx-incident-history": {"container": None, "chunking": "incidents"},
}

CHUNK_SIZE = 500       # tokens (approx chars/4)
CHUNK_OVERLAP = 50
BPR_MAX_CHUNK = 1200   # allow larger chunks to keep tables intact

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
SECTION_KEY_RE = re.compile(r"(?<!\w)§?\s*(\d+(?:\.\d+)*)(?!\w)")


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def get_search_credential():
    key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
    if key:
        return AzureKeyCredential(key)
    return DefaultAzureCredential()


def get_blob_client() -> BlobServiceClient:
    conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING") or os.getenv("AzureWebJobsStorage")
    if conn:
        return BlobServiceClient.from_connection_string(conn)
    key = os.getenv("AZURE_STORAGE_KEY")
    if key:
        return BlobServiceClient(
            f"https://{STORAGE_ACCOUNT}.blob.core.windows.net", credential=key
        )
    return BlobServiceClient(
        f"https://{STORAGE_ACCOUNT}.blob.core.windows.net",
        credential=DefaultAzureCredential(),
    )


def get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=OPENAI_ENDPOINT,
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-10-21",
    )


def get_cosmos_client() -> CosmosClient:
    key = os.getenv("COSMOS_KEY")
    if key:
        return CosmosClient(COSMOS_ENDPOINT, credential=key)
    return CosmosClient(COSMOS_ENDPOINT, credential=DefaultAzureCredential())


# ---------------------------------------------------------------------------
# Index schema
# ---------------------------------------------------------------------------

def build_index(name: str) -> SearchIndex:
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="document_title", type=SearchFieldDataType.String),
        SimpleField(
            name="document_type",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, filterable=True),
        SimpleField(name="section_heading", type=SearchFieldDataType.String),
        SimpleField(name="section_key", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="section_path", type=SearchFieldDataType.String),
        SearchableField(name="text", type=SearchFieldDataType.String),
        SearchField(
            name="embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIMENSIONS,
            vector_search_profile_name="hnsw-profile",
        ),
        SimpleField(
            name="equipment_ids",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
        ),
        SearchableField(name="keywords", type=SearchFieldDataType.String),
        SimpleField(name="source_blob", type=SearchFieldDataType.String),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-algo")],
        profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw-algo")],
    )

    return SearchIndex(name=name, fields=fields, vector_search=vector_search)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _approx_tokens(text: str) -> int:
    """Rough token estimate: chars / 4."""
    return len(text) // 4


def normalize_section_key(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    match = SECTION_KEY_RE.search(text)
    if match:
        return match.group(1).lower()

    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:80]


def _build_section_path(headings: list[str]) -> str:
    return " > ".join(heading for heading in headings if heading)


def _clean_heading_text(value: str) -> str:
    text = str(value or "").strip()
    return re.sub(r"\s+", " ", text)


def split_markdown_sections(text: str, *, default_heading: str = "") -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    current_lines: list[str] = []

    default_heading = _clean_heading_text(default_heading)
    heading_stack: list[str] = [default_heading] if default_heading else []
    current_heading = default_heading
    current_key = normalize_section_key(default_heading)
    current_path = _build_section_path(heading_stack)

    def flush_current_section() -> None:
        nonlocal current_lines
        section_text = "\n".join(current_lines).strip()
        if section_text:
            sections.append(
                {
                    "text": section_text,
                    "section_heading": current_heading,
                    "section_key": current_key,
                    "section_path": current_path or current_heading,
                }
            )
        current_lines = []

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        heading_match = HEADING_RE.match(stripped)
        if heading_match:
            flush_current_section()

            heading_level = len(heading_match.group(1))
            heading_text = _clean_heading_text(heading_match.group(2))

            if heading_level <= 1:
                heading_stack = [heading_text]
            else:
                base_stack = heading_stack[: heading_level - 1]
                if not base_stack and default_heading:
                    base_stack = [default_heading]
                heading_stack = base_stack + [heading_text]

            current_heading = heading_text
            current_key = normalize_section_key(heading_text)
            current_path = _build_section_path(heading_stack)
            current_lines = [stripped]
            continue

        current_lines.append(raw_line)

    flush_current_section()

    if sections:
        return sections

    fallback_text = text.strip()
    if not fallback_text:
        return []

    fallback_heading = default_heading or "Document"
    return [
        {
            "text": fallback_text,
            "section_heading": fallback_heading,
            "section_key": normalize_section_key(fallback_heading),
            "section_path": fallback_heading,
        }
    ]


def chunk_standard(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by approximate token count."""
    paragraphs = text.split("\n\n")
    chunks = []
    current = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = _approx_tokens(para)
        if current_tokens + para_tokens > chunk_size and current:
            chunks.append("\n\n".join(current))
            # keep overlap: last paragraph(s) summing to ~overlap tokens
            overlap_paras = []
            overlap_tokens = 0
            for p in reversed(current):
                if overlap_tokens + _approx_tokens(p) <= overlap:
                    overlap_paras.insert(0, p)
                    overlap_tokens += _approx_tokens(p)
                else:
                    break
            current = overlap_paras
            current_tokens = overlap_tokens
        current.append(para)
        current_tokens += para_tokens

    if current:
        chunks.append("\n\n".join(current))

    return [c.strip() for c in chunks if c.strip()]


def chunk_table_aware(text: str) -> list[str]:
    """
    Split Markdown text keeping tables intact.
    Tables are detected by lines starting with '|'.
    A table block is never split across chunks.
    Max chunk size is BPR_MAX_CHUNK; non-table text uses CHUNK_SIZE.
    """
    lines = text.split("\n")
    segments = []
    current_lines = []
    in_table = False

    for line in lines:
        is_table_line = line.strip().startswith("|")
        if is_table_line:
            if not in_table and current_lines:
                # flush non-table text as a segment
                segments.append(("text", "\n".join(current_lines)))
                current_lines = []
            in_table = True
            current_lines.append(line)
        else:
            if in_table:
                # flush table as a single segment
                segments.append(("table", "\n".join(current_lines)))
                current_lines = []
                in_table = False
            current_lines.append(line)

    if current_lines:
        seg_type = "table" if in_table else "text"
        segments.append((seg_type, "\n".join(current_lines)))

    # Now build chunks: text segments get standard chunking,
    # table segments are kept whole (up to BPR_MAX_CHUNK)
    chunks = []
    pending_text = []

    def flush_text():
        if pending_text:
            combined = "\n\n".join(pending_text)
            chunks.extend(chunk_standard(combined, CHUNK_SIZE, CHUNK_OVERLAP))
            pending_text.clear()

    for seg_type, seg_text in segments:
        if seg_type == "table":
            flush_text()
            # Keep table as single chunk; split only if over BPR_MAX_CHUNK
            if _approx_tokens(seg_text) <= BPR_MAX_CHUNK:
                chunks.append(seg_text.strip())
            else:
                # Really large table: split at row boundaries (each row ~1 chunk)
                rows = [r for r in seg_text.split("\n") if r.strip()]
                header = rows[:2] if len(rows) >= 2 else rows[:1]
                data_rows = rows[2:]
                for row in data_rows:
                    chunks.append("\n".join(header + [row]).strip())
        else:
            pending_text.append(seg_text)

    flush_text()
    return [c for c in chunks if c.strip()]


def chunk_text(text: str, strategy: str) -> list[str]:
    if strategy == "table_aware":
        return chunk_table_aware(text)
    return chunk_standard(text)


def chunk_document(
    text: str,
    strategy: str,
    *,
    default_section_heading: str = "",
) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    sections = split_markdown_sections(text, default_heading=default_section_heading)

    for section in sections:
        if strategy == "table_aware":
            section_chunks = chunk_table_aware(section["text"])
        elif strategy == "incidents":
            section_chunks = [section["text"]]
        else:
            section_chunks = chunk_standard(section["text"])

        for chunk_text_str in section_chunks:
            normalized_chunk = chunk_text_str.strip()
            if not normalized_chunk:
                continue
            chunks.append(
                {
                    "text": normalized_chunk,
                    "section_heading": section["section_heading"],
                    "section_key": section["section_key"],
                    "section_path": section["section_path"],
                }
            )

    return chunks


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def get_embedding(openai_client: AzureOpenAI, text: str) -> list[float]:
    text = text.replace("\n", " ").strip()
    if not text:
        return [0.0] * EMBEDDING_DIMENSIONS
    response = openai_client.embeddings.create(
        input=text,
        model=OPENAI_EMBEDDING_DEPLOYMENT,
    )
    return response.data[0].embedding


# ---------------------------------------------------------------------------
# Document sources
# ---------------------------------------------------------------------------

def documents_from_blob(
    blob_service: BlobServiceClient, container_name: str
) -> list[dict]:
    """Download all blobs from a container and return as {filename, text} dicts."""
    container_client = blob_service.get_container_client(container_name)
    docs = []
    try:
        for blob in container_client.list_blobs():
            blob_client = container_client.get_blob_client(blob.name)
            text = blob_client.download_blob().readall().decode("utf-8", errors="replace")
            docs.append({"filename": blob.name, "text": text})
    except Exception as e:
        print(f"  ⚠️  Error reading container {container_name}: {e}")
    return docs


def documents_from_incidents(cosmos_client: CosmosClient) -> list[dict]:
    """
    Generate text documents from approved closed/completed Cosmos DB incidents for historical RAG.
    Each incident → one document with key fields as readable text.
    """
    db = cosmos_client.get_database_client(COSMOS_DB)
    container = db.get_container_client("incidents")
    approved_closed = [i for i in container.read_all_items() if _is_valid_historical_incident(i)]
    return build_history_source_documents(approved_closed)


def _is_valid_historical_incident(incident: dict) -> bool:
    return is_historical_incident_eligible(incident)


# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------

def extract_document_id(filename: str) -> str:
    """Strip extension, use filename as document_id. Replace dots with underscores for safe AI Search keys."""
    stem = Path(filename).stem
    # AI Search keys allow only: letters, digits, underscore (_), dash (-), equal (=)
    return re.sub(r"[^a-zA-Z0-9_\-=]", "_", stem)


def extract_equipment_ids(text: str) -> list[str]:
    """Scan text for known equipment IDs."""
    known = ["GR-204", "MIX-102", "DRY-303"]
    return [eq for eq in known if eq in text]


def extract_document_type(index_name: str) -> str:
    return {
        "idx-sop-documents": "sop",
        "idx-equipment-manuals": "manual",
        "idx-gmp-policies": "gmp_policy",
        "idx-bpr-documents": "bpr",
        "idx-incident-history": "incident_history",
    }.get(index_name, "document")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def process_index(
    index_name: str,
    source_cfg: dict,
    index_client: SearchIndexClient,
    blob_service: BlobServiceClient,
    cosmos_client: CosmosClient,
    openai_client: AzureOpenAI,
    search_credential,
    skip_index_create: bool,
    dry_run: bool,
) -> int:
    print(f"\n📑  [{index_name}]")
    chunking_strategy = source_cfg["chunking"]
    doc_type = extract_document_type(index_name)

    # 1. Create/update index
    if not skip_index_create:
        index = build_index(index_name)
        if dry_run:
            print(f"  [dry-run] would create/update index schema")
        else:
            index_client.create_or_update_index(index)
            print(f"  ✅  Index schema created/updated")

    # 2. Load source documents
    if chunking_strategy == "incidents":
        docs = documents_from_incidents(cosmos_client)
    else:
        docs = documents_from_blob(blob_service, source_cfg["container"])

    if not docs:
        print(f"  ⚠️  No source documents found — skipping")
        return 0

    print(f"  Found {len(docs)} source document(s)")

    # 3. Chunk + embed + upsert
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=index_name,
        credential=search_credential,
    )

    total_chunks = 0
    batch = []

    for doc in docs:
        filename = doc["filename"]
        text = doc["text"]
        doc_id = extract_document_id(filename)
        equipment_ids = doc.get("equipment_ids") or extract_equipment_ids(text)

        # Derive title from first non-empty heading or filename
        title = doc.get("document_title") or doc_id
        if not doc.get("document_title"):
            for line in text.split("\n"):
                line = line.strip().lstrip("#").strip()
                if line:
                    title = line[:120]
                    break

        default_section_heading = "Incident summary" if chunking_strategy == "incidents" else title
        chunks = chunk_document(
            text,
            chunking_strategy,
            default_section_heading=default_section_heading,
        )
        print(f"  {filename}: {len(chunks)} chunk(s)")

        for i, chunk in enumerate(chunks):
            if dry_run:
                total_chunks += 1
                continue

            chunk_text_str = chunk["text"]
            embedding = get_embedding(openai_client, chunk_text_str)

            batch.append({
                "id": f"{doc_id}-chunk-{i:03d}",
                "document_id": doc_id,
                "document_title": title,
                "document_type": doc_type,
                "chunk_index": i,
                "section_heading": chunk["section_heading"],
                "section_key": chunk["section_key"],
                "section_path": chunk["section_path"],
                "text": chunk_text_str,
                "embedding": embedding,
                "equipment_ids": equipment_ids,
                "keywords": "",
                "source_blob": filename,
            })
            total_chunks += 1

            # Upload in batches of 50
            if len(batch) >= 50:
                search_client.upload_documents(documents=batch)
                batch.clear()

    if batch and not dry_run:
        search_client.upload_documents(documents=batch)

    action = "Would create" if dry_run else "Indexed"
    print(f"  {'[dry-run] ' if dry_run else ''}✅  {action} {total_chunks} chunk(s)")
    return total_chunks


def main():
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--indexes", nargs="+", choices=list(INDEX_SOURCES.keys()),
                        default=list(INDEX_SOURCES.keys()), metavar="INDEX")
    parser.add_argument("--skip-index-create", action="store_true",
                        help="Skip index schema creation (just re-index documents)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Validate required env vars
    missing = []
    if not OPENAI_ENDPOINT and not args.dry_run:
        missing.append("AZURE_OPENAI_ENDPOINT")
    if missing:
        print(f"❌  Missing required environment variables: {', '.join(missing)}")
        print(f"     Set them in .env or as shell env vars before running.")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Sentinel Intelligence — Search Index Builder")
    print(f"{'='*60}")
    print(f"  Search  : {SEARCH_ENDPOINT}")
    print(f"  OpenAI  : {OPENAI_ENDPOINT or '(dry-run, not needed)'}")
    print(f"  Mode    : {'DRY RUN' if args.dry_run else 'FULL (create indexes + embed + upload)'}")
    print(f"{'='*60}")

    search_credential = get_search_credential()
    index_client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=search_credential)
    blob_service = get_blob_client()
    cosmos_client = get_cosmos_client()
    openai_client = get_openai_client() if not args.dry_run else None

    grand_total = 0
    for index_name in args.indexes:
        source_cfg = INDEX_SOURCES[index_name]
        count = process_index(
            index_name=index_name,
            source_cfg=source_cfg,
            index_client=index_client,
            blob_service=blob_service,
            cosmos_client=cosmos_client,
            openai_client=openai_client,
            search_credential=search_credential,
            skip_index_create=args.skip_index_create,
            dry_run=args.dry_run,
        )
        grand_total += count

    print(f"\n{'='*60}")
    print(f"  Grand total: {grand_total} chunk(s) {'would be ' if args.dry_run else ''}indexed")
    print()


if __name__ == "__main__":
    main()
