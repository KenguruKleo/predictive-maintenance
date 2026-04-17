#!/usr/bin/env python3
"""
scripts/upload_documents.py
Upload local document files to Azure Blob Storage containers.

Mapping  data/documents/{subdir}/ → blob container:
  sop/      → blob-sop
  manuals/  → blob-manuals
  gmp/      → blob-gmp
  bpr/      → blob-bpr

Usage:
    python scripts/upload_documents.py
    python scripts/upload_documents.py --containers blob-sop blob-bpr
    python scripts/upload_documents.py --dry-run
"""

import argparse
import os
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
DOCS_DIR = ROOT / "data" / "documents"

STORAGE_ACCOUNT = "stsentinelintelerzrpo"

# local subdir → blob container
CONTAINER_MAP = {
    "sop": "blob-sop",
    "manuals": "blob-manuals",
    "gmp": "blob-gmp",
    "bpr": "blob-bpr",
}


def get_blob_client(account_name: str) -> BlobServiceClient:
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if conn_str:
        print("  [auth] Using AZURE_STORAGE_CONNECTION_STRING")
        return BlobServiceClient.from_connection_string(conn_str)
    key = os.getenv("AZURE_STORAGE_KEY")
    if key:
        print("  [auth] Using AZURE_STORAGE_KEY")
        return BlobServiceClient(
            account_url=f"https://{account_name}.blob.core.windows.net",
            credential=key,
        )
    print("  [auth] Using DefaultAzureCredential")
    return BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=DefaultAzureCredential(),
    )


def upload_directory(
    blob_service: BlobServiceClient,
    local_dir: Path,
    container_name: str,
    dry_run: bool,
) -> int:
    files = sorted(local_dir.glob("*"))
    files = [f for f in files if f.is_file()]
    if not files:
        print(f"  ⚠️  No files found in {local_dir}")
        return 0

    container_client = blob_service.get_container_client(container_name)

    count = 0
    for file_path in files:
        blob_name = file_path.name
        if dry_run:
            print(f"    [dry-run] {file_path.name} → {container_name}/{blob_name}")
        else:
            with open(file_path, "rb") as f:
                container_client.upload_blob(
                    name=blob_name,
                    data=f,
                    overwrite=True,
                    content_settings=_content_settings(file_path),
                )
            print(f"    ✅  {file_path.name} → {container_name}/{blob_name}")
        count += 1
    return count


def _content_settings(path: Path):
    from azure.storage.blob import ContentSettings
    ext = path.suffix.lower()
    mime = {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }.get(ext, "application/octet-stream")
    return ContentSettings(content_type=mime)


def main():
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--containers", nargs="+", choices=list(CONTAINER_MAP.values()),
                        default=list(CONTAINER_MAP.values()))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Document Upload — Azure Blob Storage")
    print(f"{'='*60}")
    print(f"  Account : {STORAGE_ACCOUNT}")
    print(f"  Mode    : {'DRY RUN' if args.dry_run else 'UPLOAD (overwrite)'}")
    print(f"{'='*60}\n")

    blob_service = get_blob_client(STORAGE_ACCOUNT)

    total = 0
    for local_subdir, container_name in CONTAINER_MAP.items():
        if container_name not in args.containers:
            continue
        local_dir = DOCS_DIR / local_subdir
        if not local_dir.exists():
            print(f"📁  [{container_name}] ⚠️  source dir not found: {local_dir}\n")
            continue
        print(f"📁  [{container_name}] ← {local_dir.relative_to(ROOT)}")
        count = upload_directory(blob_service, local_dir, container_name, args.dry_run)
        total += count
        print(f"  {'Would upload' if args.dry_run else 'Uploaded'} {count} file(s)\n")

    print(f"{'='*60}")
    print(f"  Total: {total} file(s) {'would be ' if args.dry_run else ''}uploaded")
    print()


if __name__ == "__main__":
    main()
