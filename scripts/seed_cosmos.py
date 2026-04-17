#!/usr/bin/env python3
"""
scripts/seed_cosmos.py
Seed Azure Cosmos DB with mock data from data/mock/*.json

Auth: DefaultAzureCredential (picks up `az login` locally, Managed Identity in Azure)
      Falls back to COSMOS_KEY env var if set (useful for quick local runs).

Usage:
    python scripts/seed_cosmos.py                           # upsert all collections
    python scripts/seed_cosmos.py --reset                   # delete all items first, then insert
    python scripts/seed_cosmos.py --collections equipment batches
    python scripts/seed_cosmos.py --dry-run                 # print what would be seeded, no writes
"""

import argparse
import json
import os
import sys
from pathlib import Path

from azure.cosmos import CosmosClient, exceptions
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data" / "mock"
DATABASE_NAME = "sentinel-intelligence"

# Maps collection name → (json file, partition key field in the document)
# NOTE: Cosmos partition keys are camelCase (/equipmentId, /incidentId, /id).
#       Our JSON uses snake_case (equipment_id). The loader normalises this.
COLLECTIONS = {
    "equipment": {
        "file": DATA_DIR / "equipment.json",
        "pk_field": "id",          # /id — already present as-is
    },
    "batches": {
        "file": DATA_DIR / "batches.json",
        "pk_field": "equipmentId", # /equipmentId — derived from equipment_id
    },
    "incidents": {
        "file": DATA_DIR / "incidents.json",
        "pk_field": "equipmentId", # /equipmentId — derived from equipment_id
    },
    "templates": {
        "file": DATA_DIR / "templates.json",
        "pk_field": "id",          # /id — already present
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_cosmos_client(endpoint: str) -> CosmosClient:
    """Return CosmosClient using DefaultAzureCredential or COSMOS_KEY fallback."""
    cosmos_key = os.getenv("COSMOS_KEY")
    if cosmos_key:
        print("  [auth] Using COSMOS_KEY from environment")
        return CosmosClient(endpoint, credential=cosmos_key)
    print("  [auth] Using DefaultAzureCredential (az login / Managed Identity)")
    return CosmosClient(endpoint, credential=DefaultAzureCredential())


def normalise_document(doc: dict, pk_field: str) -> dict:
    """
    Ensure Cosmos partition key field exists (camelCase) in the document.
    JSON files use snake_case; Cosmos containers were provisioned with camelCase.

    Mappings applied:
        equipment_id  → equipmentId   (incidents, batches)
        incident_id   → incidentId    (capa-plans, approval-tasks — future)
    """
    # equipment_id → equipmentId
    if pk_field == "equipmentId" and "equipmentId" not in doc:
        if "equipment_id" in doc:
            doc["equipmentId"] = doc["equipment_id"]

    # incident_id → incidentId (defensive — not seeded now but consistent)
    if pk_field == "incidentId" and "incidentId" not in doc:
        if "incident_id" in doc:
            doc["incidentId"] = doc["incident_id"]

    return doc


def load_json(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array, got {type(data)}")
    return data


def delete_all_items(container, collection_name: str) -> int:
    """Delete all items in a container. Returns count deleted."""
    count = 0
    try:
        items = list(container.read_all_items())
    except exceptions.CosmosHttpResponseError as e:
        print(f"  ⚠️  Could not read {collection_name}: {e.message}")
        return 0

    for item in items:
        pk = item.get("equipmentId") or item.get("incidentId") or item.get("id")
        container.delete_item(item=item["id"], partition_key=pk)
        count += 1
    return count


def upsert_items(container, documents: list[dict], pk_field: str, dry_run: bool) -> int:
    """Upsert all documents. Returns count upserted."""
    count = 0
    for doc in documents:
        doc = normalise_document(doc, pk_field)
        if dry_run:
            print(f"    [dry-run] would upsert id={doc.get('id')} pk={doc.get(pk_field)}")
        else:
            container.upsert_item(body=doc)
        count += 1
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    load_dotenv()  # load .env if present (local dev)

    parser = argparse.ArgumentParser(description="Seed Cosmos DB with mock data")
    parser.add_argument(
        "--collections",
        nargs="+",
        choices=list(COLLECTIONS.keys()),
        default=list(COLLECTIONS.keys()),
        metavar="COLLECTION",
        help="Which collections to seed (default: all)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all existing items before inserting",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without writing to Cosmos",
    )
    args = parser.parse_args()

    # Resolve endpoint
    endpoint = os.getenv(
        "COSMOS_ENDPOINT",
        "https://cosmos-sentinel-intel-dev-erzrpo.documents.azure.com:443/",
    )

    print(f"\n{'='*60}")
    print(f"  Sentinel Intelligence — Cosmos DB Seeder")
    print(f"{'='*60}")
    print(f"  Endpoint  : {endpoint}")
    print(f"  Database  : {DATABASE_NAME}")
    print(f"  Mode      : {'DRY RUN' if args.dry_run else 'RESET + INSERT' if args.reset else 'UPSERT'}")
    print(f"  Collections: {', '.join(args.collections)}")
    print(f"{'='*60}\n")

    client = get_cosmos_client(endpoint)

    try:
        db = client.get_database_client(DATABASE_NAME)
        # Verify connection
        db.read()
    except exceptions.CosmosResourceNotFoundError:
        print(f"❌  Database '{DATABASE_NAME}' not found. Has Bicep been deployed?")
        sys.exit(1)
    except Exception as e:
        print(f"❌  Cannot connect to Cosmos DB: {e}")
        sys.exit(1)

    total_upserted = 0
    total_deleted = 0
    results = []

    for name in args.collections:
        cfg = COLLECTIONS[name]
        print(f"📦  [{name}]")

        # Check file exists
        if not cfg["file"].exists():
            print(f"  ⚠️  File not found: {cfg['file']} — skipping\n")
            results.append((name, "SKIP", 0, 0))
            continue

        # Load data
        documents = load_json(cfg["file"])
        print(f"  Loaded {len(documents)} items from {cfg['file'].name}")

        # Get container — handle missing container gracefully
        try:
            container = db.get_container_client(name)
            container.read()  # verify container exists
        except exceptions.CosmosResourceNotFoundError:
            print(
                f"  ❌  Container '{name}' not found in Cosmos DB.\n"
                f"     → Run: az deployment group create ... to deploy updated cosmos.bicep\n"
            )
            results.append((name, "MISSING", 0, 0))
            continue
        except exceptions.CosmosHttpResponseError as e:
            print(f"  ❌  Error accessing container '{name}': {e.message}\n")
            results.append((name, "ERROR", 0, 0))
            continue

        # Reset if requested
        deleted = 0
        if args.reset and not args.dry_run:
            deleted = delete_all_items(container, name)
            print(f"  🗑️   Deleted {deleted} existing items")
            total_deleted += deleted

        # Upsert
        count = upsert_items(container, documents, cfg["pk_field"], dry_run=args.dry_run)
        total_upserted += count
        print(f"  {'[dry-run] ' if args.dry_run else ''}✅  {'Would upsert' if args.dry_run else 'Upserted'} {count} items\n")
        results.append((name, "OK", deleted, count))

    # Summary
    print(f"{'='*60}")
    print(f"  Summary")
    print(f"{'='*60}")
    for name, status, deleted, upserted in results:
        status_icon = {"OK": "✅", "SKIP": "⏭️ ", "MISSING": "❌", "ERROR": "❌"}[status]
        if args.reset and status == "OK" and not args.dry_run:
            print(f"  {status_icon}  {name:<16} deleted={deleted}  upserted={upserted}")
        else:
            print(f"  {status_icon}  {name:<16} {'would upsert' if args.dry_run else 'upserted'}={upserted}  status={status}")

    if not args.dry_run:
        if total_deleted:
            print(f"\n  Total deleted : {total_deleted}")
        print(f"  Total upserted: {total_upserted}")

    missing = [name for name, status, _, _ in results if status == "MISSING"]
    if missing:
        print(f"\n  ⚠️  Missing containers: {missing}")
        print(f"     Deploy updated cosmos.bicep:")
        print(f"     az deployment group create \\")
        print(f"       --resource-group ODL-GHAZ-2177134 \\")
        print(f"       --template-file infra/main.bicep \\")
        print(f"       --parameters infra/parameters/dev.bicepparam")

    print()


if __name__ == "__main__":
    main()
