#!/usr/bin/env python3
"""
Reset Azure dev incident data while preserving reference seed data.

What this script resets:
  - Cosmos DB incident containers:
      incidents
      incident_events
      notifications
      approval-tasks
      capa-plans
  - Azure AI Search incident history documents:
      idx-incident-history
  - Durable Functions terminal instance history:
      Completed / Failed / Terminated

What this script preserves:
  - Cosmos reference/seed containers:
      equipment
      batches
      templates

Usage:
    # Show what would be reset, but do not change anything
    python scripts/reset_dev_data.py --dry-run

    # Reset dev data with interactive confirmation
    python scripts/reset_dev_data.py

    # Reset dev data without interactive confirmation
    python scripts/reset_dev_data.py --yes
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.search.documents import SearchClient

ROOT = Path(__file__).resolve().parents[1]
LOCAL_SETTINGS_PATH = ROOT / "backend" / "local.settings.json"

DEFAULT_RESOURCE_GROUP = "ODL-GHAZ-2177134"
DEFAULT_FUNCTION_APP = "func-sentinel-intel-dev-erzrpo"
DEFAULT_COSMOS_ACCOUNT = "cosmos-sentinel-intel-dev-erzrpo"
DEFAULT_SEARCH_SERVICE = "srch-sentinel-intel-dev-erzrpo"
DEFAULT_COSMOS_DATABASE = "sentinel-intelligence"
DEFAULT_SEARCH_INDEX = "idx-incident-history"

INCIDENT_CONTAINERS: list[tuple[str, str]] = [
    ("incident_events", "/incidentId"),
    ("notifications", "/incidentId"),
    ("approval-tasks", "/incidentId"),
    ("capa-plans", "/incidentId"),
    ("incidents", "/equipmentId"),
]
REFERENCE_CONTAINERS = ["equipment", "batches", "templates"]
TERMINAL_DURABLE_STATUSES = {"Completed", "Failed", "Terminated"}
SEARCH_DELETE_BATCH_SIZE = 500
DURABLE_TERMINATE_MAX_ATTEMPTS = 10
DURABLE_TERMINATE_POLL_SECONDS = 2


def load_local_settings() -> None:
    if not LOCAL_SETTINGS_PATH.exists():
        return

    with LOCAL_SETTINGS_PATH.open(encoding="utf-8") as handle:
        settings = json.load(handle)

    for key, value in settings.get("Values", {}).items():
        os.environ.setdefault(key, str(value))


def derive_service_name(endpoint: str | None, expected_suffix: str) -> str | None:
    if not endpoint:
        return None

    parsed = urllib.parse.urlparse(endpoint)
    host = parsed.hostname
    if not host or not host.endswith(expected_suffix):
        return None
    return host.removesuffix(expected_suffix)


def resolve_defaults() -> dict[str, str]:
    cosmos_endpoint = os.getenv("COSMOS_ENDPOINT", "")
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    return {
        "resource_group": os.getenv("AZURE_RESOURCE_GROUP", DEFAULT_RESOURCE_GROUP),
        "function_app": os.getenv("AZURE_FUNCTION_APP_NAME", DEFAULT_FUNCTION_APP),
        "cosmos_account": os.getenv("COSMOS_ACCOUNT_NAME")
        or derive_service_name(cosmos_endpoint, ".documents.azure.com")
        or DEFAULT_COSMOS_ACCOUNT,
        "search_service": os.getenv("AZURE_SEARCH_SERVICE")
        or derive_service_name(search_endpoint, ".search.windows.net")
        or DEFAULT_SEARCH_SERVICE,
        "cosmos_database": os.getenv("COSMOS_DATABASE", DEFAULT_COSMOS_DATABASE),
        "search_index": os.getenv("AZURE_INCIDENT_HISTORY_INDEX", DEFAULT_SEARCH_INDEX),
        "cosmos_endpoint": cosmos_endpoint or f"https://{DEFAULT_COSMOS_ACCOUNT}.documents.azure.com:443/",
        "search_endpoint": search_endpoint or f"https://{DEFAULT_SEARCH_SERVICE}.search.windows.net",
    }


def run_az(args: list[str]) -> str:
    command = ["az", *args]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{stderr}")
    return result.stdout.strip()


def ensure_az_ready() -> None:
    run_az(["account", "show", "-o", "json"])


def get_cosmos_endpoint(args: argparse.Namespace) -> str:
    endpoint = args.cosmos_endpoint or os.getenv("COSMOS_ENDPOINT")
    if endpoint:
        return endpoint
    return f"https://{args.cosmos_account}.documents.azure.com:443/"


def get_search_endpoint(args: argparse.Namespace) -> str:
    endpoint = args.search_endpoint or os.getenv("AZURE_SEARCH_ENDPOINT")
    if endpoint:
        return endpoint.rstrip("/")
    return f"https://{args.search_service}.search.windows.net"


def get_cosmos_key(args: argparse.Namespace) -> str:
    key = os.getenv("COSMOS_KEY")
    if key:
        return key
    return run_az([
        "cosmosdb",
        "keys",
        "list",
        "--name",
        args.cosmos_account,
        "--resource-group",
        args.resource_group,
        "--query",
        "primaryMasterKey",
        "-o",
        "tsv",
    ])


def get_search_key(args: argparse.Namespace) -> str:
    key = os.getenv("AZURE_SEARCH_ADMIN_KEY") or os.getenv("AZURE_SEARCH_KEY")
    if key:
        return key
    return run_az([
        "search",
        "admin-key",
        "show",
        "--service-name",
        args.search_service,
        "--resource-group",
        args.resource_group,
        "--query",
        "primaryKey",
        "-o",
        "tsv",
    ])


def get_function_master_key(args: argparse.Namespace) -> str:
    return run_az([
        "functionapp",
        "keys",
        "list",
        "--name",
        args.function_app,
        "--resource-group",
        args.resource_group,
        "--query",
        "masterKey",
        "-o",
        "tsv",
    ])


def get_cosmos_client(args: argparse.Namespace) -> CosmosClient:
    return CosmosClient(get_cosmos_endpoint(args), get_cosmos_key(args))


def get_search_client(args: argparse.Namespace) -> SearchClient:
    return SearchClient(
        endpoint=get_search_endpoint(args),
        index_name=args.search_index,
        credential=AzureKeyCredential(get_search_key(args)),
    )


def count_container_items(db, container_name: str) -> int | None:
    try:
        container = db.get_container_client(container_name)
        return list(container.query_items(
            "SELECT VALUE COUNT(1) FROM c",
            enable_cross_partition_query=True,
        ))[0]
    except CosmosResourceNotFoundError:
        return None


def count_search_documents(client: SearchClient) -> int | None:
    try:
        result = client.search(search_text="*", include_total_count=True, top=0)
        return result.get_count() or 0
    except HttpResponseError:
        return None


def durable_base_url(args: argparse.Namespace) -> str:
    return f"https://{args.function_app}.azurewebsites.net"


def list_durable_instances(args: argparse.Namespace, master_key: str) -> list[dict]:
    query = urllib.parse.urlencode({
        "showInput": "false",
        "top": "500",
        "code": master_key,
    })
    url = f"{durable_base_url(args)}/runtime/webhooks/durabletask/instances?{query}"
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode())


def collect_state(args: argparse.Namespace) -> dict:
    db = get_cosmos_client(args).get_database_client(args.cosmos_database)
    search_client = get_search_client(args)
    master_key = get_function_master_key(args)

    cosmos_counts = {
        name: count_container_items(db, name)
        for name, _pk in INCIDENT_CONTAINERS
    }
    reference_counts = {
        name: count_container_items(db, name)
        for name in REFERENCE_CONTAINERS
    }
    search_count = count_search_documents(search_client)
    durable_instances = list_durable_instances(args, master_key)
    durable_status_counts = dict(Counter(item.get("runtimeStatus", "Unknown") for item in durable_instances))

    return {
        "cosmos": cosmos_counts,
        "reference": reference_counts,
        "search_count": search_count,
        "durable_total": len(durable_instances),
        "durable_status_counts": durable_status_counts,
    }


def print_state(title: str, state: dict) -> None:
    print(f"\n{'=' * 68}")
    print(f"  {title}")
    print(f"{'=' * 68}")
    print("  Cosmos incident containers:")
    for name, count in state["cosmos"].items():
        rendered = "missing" if count is None else str(count)
        print(f"    {name:16s} {rendered}")

    print("  Cosmos reference containers:")
    for name, count in state["reference"].items():
        rendered = "missing" if count is None else str(count)
        print(f"    {name:16s} {rendered}")

    search_rendered = "missing" if state["search_count"] is None else str(state["search_count"])
    print(f"  AI Search {DEFAULT_SEARCH_INDEX}: {search_rendered}")
    print(f"  Durable instances: {state['durable_total']}")
    if state["durable_status_counts"]:
        for status, count in sorted(state["durable_status_counts"].items()):
            print(f"    {status:16s} {count}")


def confirm_reset(args: argparse.Namespace) -> bool:
    if args.yes:
        return True

    print("\nThis will permanently reset dev incident data in Azure.")
    print("It preserves equipment, batches, and templates.")
    phrase = input("Type RESET DEV DATA to continue: ").strip()
    if phrase != "RESET DEV DATA":
        print("Aborted.")
        return False
    return True


def recreate_incident_containers(args: argparse.Namespace) -> None:
    existing = set(filter(None, run_az([
        "cosmosdb",
        "sql",
        "container",
        "list",
        "--account-name",
        args.cosmos_account,
        "--resource-group",
        args.resource_group,
        "--database-name",
        args.cosmos_database,
        "--query",
        "[].name",
        "-o",
        "tsv",
    ]).splitlines()))

    for container_name, partition_key in INCIDENT_CONTAINERS:
        if container_name in existing:
            print(f"  Recreating Cosmos container: {container_name}")
            run_az([
                "cosmosdb",
                "sql",
                "container",
                "delete",
                "--account-name",
                args.cosmos_account,
                "--resource-group",
                args.resource_group,
                "--database-name",
                args.cosmos_database,
                "--name",
                container_name,
                "--yes",
                "--output",
                "none",
            ])
        else:
            print(f"  Creating missing Cosmos container: {container_name}")

        run_az([
            "cosmosdb",
            "sql",
            "container",
            "create",
            "--account-name",
            args.cosmos_account,
            "--resource-group",
            args.resource_group,
            "--database-name",
            args.cosmos_database,
            "--name",
            container_name,
            "--partition-key-path",
            partition_key,
            "--output",
            "none",
        ])


def clear_incident_history_index(args: argparse.Namespace) -> int:
    search_client = get_search_client(args)
    deleted = 0

    while True:
        batch = list(search_client.search(
            search_text="*",
            select=["id"],
            top=SEARCH_DELETE_BATCH_SIZE,
        ))
        if not batch:
            break

        search_client.delete_documents(documents=[{"id": item["id"]} for item in batch])
        deleted += len(batch)
        if len(batch) < SEARCH_DELETE_BATCH_SIZE:
            break

    print(f"  Cleared AI Search index documents: {deleted}")
    return deleted


def purge_durable_history(args: argparse.Namespace) -> int:
    master_key = get_function_master_key(args)
    terminated = terminate_active_durable_instances(args, master_key)
    instances = list_durable_instances(args, master_key)
    terminal = [
        item for item in instances
        if item.get("runtimeStatus") in TERMINAL_DURABLE_STATUSES and item.get("instanceId")
    ]

    purged = 0
    if terminated:
        print(f"  Terminated active Durable instances: {terminated}")

    for item in terminal:
        instance_id = item["instanceId"]
        encoded_id = urllib.parse.quote(instance_id, safe="")
        encoded_key = urllib.parse.quote(master_key, safe="")
        url = f"{durable_base_url(args)}/runtime/webhooks/durabletask/instances/{encoded_id}?code={encoded_key}"
        request = urllib.request.Request(url, method="DELETE")
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status == 200:
                purged += 1

    print(f"  Purged Durable instance histories: {purged}")
    return purged


def terminate_active_durable_instances(args: argparse.Namespace, master_key: str) -> int:
    instances = list_durable_instances(args, master_key)
    active = [
        item for item in instances
        if item.get("runtimeStatus") not in TERMINAL_DURABLE_STATUSES and item.get("instanceId")
    ]
    if not active:
        return 0

    terminated = 0
    for item in active:
        instance_id = item["instanceId"]
        encoded_id = urllib.parse.quote(instance_id, safe="")
        query = urllib.parse.urlencode({
            "reason": "reset dev data",
            "code": master_key,
        })
        url = f"{durable_base_url(args)}/runtime/webhooks/durabletask/instances/{encoded_id}/terminate?{query}"
        request = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status in (200, 202):
                terminated += 1

    for _attempt in range(DURABLE_TERMINATE_MAX_ATTEMPTS):
        remaining = [
            item for item in list_durable_instances(args, master_key)
            if item.get("runtimeStatus") not in TERMINAL_DURABLE_STATUSES and item.get("instanceId")
        ]
        if not remaining:
            return terminated
        time.sleep(DURABLE_TERMINATE_POLL_SECONDS)

    remaining_ids = ", ".join(item["instanceId"] for item in remaining)
    raise RuntimeError(f"Timed out waiting for Durable instances to terminate: {remaining_ids}")


def validate_post_reset(state: dict) -> list[str]:
    problems: list[str] = []
    for name, count in state["cosmos"].items():
        if count not in (0, None):
            problems.append(f"Cosmos container {name} still has {count} item(s)")

    if state["search_count"] not in (0, None):
        problems.append(f"AI Search history index still has {state['search_count']} document(s)")

    if state["durable_total"] != 0:
        problems.append(f"Durable instance history still has {state['durable_total']} instance(s)")

    return problems


def build_parser() -> argparse.ArgumentParser:
    defaults = resolve_defaults()
    parser = argparse.ArgumentParser(description="Safely reset dev incident data in Azure")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be reset without making changes")
    parser.add_argument("--yes", action="store_true", help="Skip the interactive confirmation prompt")
    parser.add_argument("--resource-group", default=defaults["resource_group"], help="Azure resource group containing the dev resources")
    parser.add_argument("--function-app", default=defaults["function_app"], help="Azure Function App name used for Durable history purge")
    parser.add_argument("--cosmos-account", default=defaults["cosmos_account"], help="Cosmos DB account name")
    parser.add_argument("--cosmos-database", default=defaults["cosmos_database"], help="Cosmos DB database name")
    parser.add_argument("--cosmos-endpoint", default=defaults["cosmos_endpoint"], help="Cosmos DB endpoint URL")
    parser.add_argument("--search-service", default=defaults["search_service"], help="Azure AI Search service name")
    parser.add_argument("--search-endpoint", default=defaults["search_endpoint"], help="Azure AI Search endpoint URL")
    parser.add_argument("--search-index", default=defaults["search_index"], help="Azure AI Search index to clear")
    return parser


def main() -> int:
    load_local_settings()
    parser = build_parser()
    args = parser.parse_args()

    try:
        ensure_az_ready()
        pre_state = collect_state(args)
        print_state("Dev Reset Preview", pre_state)

        if args.dry_run:
            print("\nDry-run only. No Azure resources were modified.")
            return 0

        if not confirm_reset(args):
            return 1

        print("\nResetting Azure dev incident data...")
        recreate_incident_containers(args)
        clear_incident_history_index(args)
        purge_durable_history(args)

        post_state = collect_state(args)
        print_state("Post-Reset Verification", post_state)

        problems = validate_post_reset(post_state)
        if problems:
            print("\nReset finished with remaining issues:")
            for problem in problems:
                print(f"  - {problem}")
            return 1

        print("\nReset completed successfully.")
        return 0
    except KeyboardInterrupt:
        print("\nAborted.")
        return 130
    except Exception as exc:
        print(f"\nReset failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())