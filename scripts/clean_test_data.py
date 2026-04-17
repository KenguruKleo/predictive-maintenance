#!/usr/bin/env python3
"""
scripts/clean_test_data.py
Remove test incidents and all related records from Cosmos DB.

Deletes from:
  - incidents            — incident documents (by id prefix or specific ids)
  - incident_events      — all events for each incident
  - notifications        — all notifications for each incident

Usage:
    # Dry-run (show what would be deleted, no actual deletes)
    python scripts/clean_test_data.py --dry-run

    # Delete all INC-2026-* incidents
    python scripts/clean_test_data.py --all

    # Delete specific incidents
    python scripts/clean_test_data.py --ids INC-2026-0011 INC-2026-0012

    # Delete incidents created in the last N minutes
    python scripts/clean_test_data.py --last-minutes 30

    # Interactive: show list, confirm before deleting
    python scripts/clean_test_data.py
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

try:
    from azure.cosmos import CosmosClient
    from azure.cosmos.exceptions import CosmosResourceNotFoundError
except ImportError:
    print("❌  azure-cosmos not installed: pip install azure-cosmos")
    sys.exit(1)

# Load credentials from local.settings.json (Azure Functions JSON format)
_settings_path = os.path.join(os.path.dirname(__file__), "../backend/local.settings.json")
if os.path.exists(_settings_path):
    import json as _json
    with open(_settings_path) as _f:
        _settings = _json.load(_f)
    for _k, _v in _settings.get("Values", {}).items():
        os.environ.setdefault(_k, str(_v))

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT") or ""
COSMOS_KEY = os.getenv("COSMOS_KEY") or ""

if not COSMOS_ENDPOINT or not COSMOS_KEY:
    print("❌  COSMOS_ENDPOINT and COSMOS_KEY must be set (via env or backend/local.settings.json)")
    sys.exit(1)
DB_NAME = "sentinel-intelligence"

# Containers to clean (in order)
RELATED_CONTAINERS = [
    ("incident_events", "incident_id"),   # field name linking to incident
    ("notifications",   "incident_id"),
]
INCIDENTS_CONTAINER = "incidents"


def get_db():
    client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
    return client.get_database_client(DB_NAME)


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def list_incidents(db, ids: list[str] | None = None, last_minutes: int | None = None) -> list[dict]:
    container = db.get_container_client(INCIDENTS_CONTAINER)
    if ids:
        placeholders = ", ".join(f"@id{i}" for i in range(len(ids)))
        query = f"SELECT c.id, c.equipment_id, c.severity, c.status, c.reported_at FROM c WHERE c.id IN ({placeholders})"
        params = [{"name": f"@id{i}", "value": v} for i, v in enumerate(ids)]
        return list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    elif last_minutes:
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=last_minutes)).isoformat()
        query = "SELECT c.id, c.equipment_id, c.severity, c.status, c.reported_at FROM c WHERE c.reported_at >= @cutoff ORDER BY c.reported_at DESC"
        params = [{"name": "@cutoff", "value": cutoff}]
        return list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    else:
        query = "SELECT c.id, c.equipment_id, c.severity, c.status, c.reported_at FROM c ORDER BY c.reported_at DESC"
        return list(container.query_items(query=query, enable_cross_partition_query=True))


def list_related_batch(db, container_name: str, incident_ids: list[str], fk_field: str) -> dict[str, list[str]]:
    """Batch query: return {incident_id: [related_doc_ids]} for all incidents at once."""
    if not incident_ids:
        return {}
    try:
        container = db.get_container_client(container_name)
        placeholders = ", ".join(f"@id{i}" for i in range(len(incident_ids)))
        query = f"SELECT c.id, c.{fk_field} FROM c WHERE c.{fk_field} IN ({placeholders})"
        params = [{"name": f"@id{i}", "value": v} for i, v in enumerate(incident_ids)]
        items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
        result: dict[str, list[str]] = {iid: [] for iid in incident_ids}
        for item in items:
            parent = item.get(fk_field)
            if parent in result:
                result[parent].append(item["id"])
        return result
    except CosmosResourceNotFoundError:
        return {iid: [] for iid in incident_ids}  # container doesn't exist yet
    except Exception as exc:
        print(f"  ⚠️  Could not query {container_name}: {exc}")
        return {iid: [] for iid in incident_ids}


# ---------------------------------------------------------------------------
# Delete helpers
# ---------------------------------------------------------------------------

def delete_item(container, doc_id: str, dry_run: bool) -> bool:
    if dry_run:
        return True
    try:
        container.delete_item(item=doc_id, partition_key=doc_id)
        return True
    except CosmosResourceNotFoundError:
        return True  # already gone
    except Exception as exc:
        print(f"    ⚠️  Could not delete {doc_id}: {exc}")
        return False


def delete_incident_and_related(db, incident: dict, related_map: dict, dry_run: bool) -> dict:
    incident_id = incident["id"]
    stats = {"incident": 0, "events": 0, "notifications": 0}

    prefix = "  [DRY-RUN]" if dry_run else " "

    # Delete related records first (IDs already fetched in batch)
    for container_name, _fk in RELATED_CONTAINERS:
        related_ids = related_map.get(container_name, {}).get(incident_id, [])
        if related_ids:
            container = db.get_container_client(container_name)
            for rid in related_ids:
                if delete_item(container, rid, dry_run):
                    key = "events" if "events" in container_name else "notifications"
                    stats[key] += 1
                    print(f"{prefix}  Deleted {container_name}/{rid}")

    # Delete incident itself
    container = db.get_container_client(INCIDENTS_CONTAINER)
    if delete_item(container, incident_id, dry_run):
        stats["incident"] += 1
        print(f"{prefix}  Deleted incident/{incident_id}")

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Clean test incidents from Cosmos DB")
    parser.add_argument("--all", dest="all", action="store_true", help="Delete all incidents")
    parser.add_argument("--ids", nargs="+", metavar="ID", help="Delete specific incident IDs")
    parser.add_argument("--last-minutes", type=int, metavar="N", help="Delete incidents created in the last N minutes")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")
    args = parser.parse_args()

    db = get_db()

    # Determine which incidents to target
    if args.ids:
        incidents = list_incidents(db, ids=args.ids)
    elif args.last_minutes:
        incidents = list_incidents(db, last_minutes=args.last_minutes)
    elif args.all:
        incidents = list_incidents(db)
    else:
        # Interactive mode
        incidents = list_incidents(db)

    if not incidents:
        print("No incidents found.")
        return

    # Show what we found
    print(f"\n{'=' * 60}")
    mode = "DRY-RUN — " if args.dry_run else ""
    print(f"  {mode}Incidents to clean ({len(incidents)} found)")
    print(f"{'=' * 60}")
    for inc in incidents:
        created = (inc.get('reported_at') or 'unknown')[:19]
        print(f"  {inc['id']:20s}  {inc.get('equipment_id','?'):8s}  {inc.get('severity','?'):8s}  {inc.get('status','?'):16s}  {created}")

    if not args.all and not args.ids and not args.last_minutes:
        # Interactive confirmation
        print()
        choice = input(f"Delete all {len(incidents)} incidents and their related records? [y/N] ").strip().lower()
        if choice != "y":
            print("Aborted.")
            return

    if not args.dry_run:
        print()
        confirm = input(f"⚠️  This will permanently delete {len(incidents)} incidents. Type 'yes' to confirm: ").strip()
        if confirm != "yes":
            print("Aborted.")
            return

    # Batch-fetch related records for all incidents (2 queries instead of 2×N)
    incident_ids = [inc["id"] for inc in incidents]
    related_map: dict[str, dict[str, list[str]]] = {}
    for container_name, fk_field in RELATED_CONTAINERS:
        related_map[container_name] = list_related_batch(db, container_name, incident_ids, fk_field)

    print()
    total = {"incident": 0, "events": 0, "notifications": 0}
    for inc in incidents:
        print(f"  ── {inc['id']}")
        stats = delete_incident_and_related(db, inc, related_map, args.dry_run)
        for k, v in stats.items():
            total[k] += v

    print(f"\n{'=' * 60}")
    suffix = " (dry-run)" if args.dry_run else ""
    print(f"  Done{suffix}: {total['incident']} incidents, {total['events']} events, {total['notifications']} notifications")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
