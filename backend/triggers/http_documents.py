"""
HTTP Trigger — GET /api/documents/{container}/{blob_path}

Read-only proxy for demo evidence links. Only document ingestion containers are
allowed, so the frontend can open cited SOP/BPR/GMP/manual blobs without storage
credentials or SAS URL handling.
"""

import logging
import os
from urllib.parse import unquote

import azure.functions as func
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)

ALLOWED_CONTAINERS = {
    "blob-sop",
    "blob-manuals",
    "blob-gmp",
    "blob-bpr",
    "blob-history",
}

bp = func.Blueprint()


@bp.route(
    route="documents/{container}/{*blob_path}",
    methods=["GET"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def get_document(req: func.HttpRequest) -> func.HttpResponse:
    container = req.route_params.get("container", "")
    blob_path = unquote(req.route_params.get("blob_path", "")).strip("/")

    if container not in ALLOWED_CONTAINERS:
        return _error(400, "Unsupported document container")
    if not blob_path or _has_unsafe_path_segment(blob_path):
        return _error(400, "Invalid document path")

    try:
        service = _get_blob_service_client()
        blob = service.get_blob_client(container=container, blob=blob_path)
        data = blob.download_blob().readall()
    except ResourceNotFoundError:
        return _error(404, "Document not found")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Document proxy failed for %s/%s: %s", container, blob_path, exc)
        return _error(500, "Unable to load document")

    return func.HttpResponse(
        body=data,
        status_code=200,
        headers={
            "Content-Type": _content_type(blob_path),
            "Cache-Control": "no-store",
        },
    )


def _get_blob_service_client() -> BlobServiceClient:
    connection_string = os.getenv("AzureWebJobsStorage", "")
    if not connection_string:
        raise RuntimeError("AzureWebJobsStorage app setting is required")
    return BlobServiceClient.from_connection_string(connection_string)


def _has_unsafe_path_segment(path: str) -> bool:
    return any(segment in {"", ".", ".."} for segment in path.split("/"))


def _content_type(path: str) -> str:
    if path.endswith(".md"):
        return "text/markdown; charset=utf-8"
    if path.endswith(".txt"):
        return "text/plain; charset=utf-8"
    return "application/octet-stream"


def _error(status: int, message: str) -> func.HttpResponse:
    return func.HttpResponse(
        body=message,
        status_code=status,
        mimetype="text/plain",
    )
