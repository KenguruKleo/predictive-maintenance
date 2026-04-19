#!/usr/bin/env python3
"""
Recover a stuck live incident in one command.

Recovery flow:
  1. Read the current incident document from Cosmos DB.
  2. Terminate the matching Durable instance if it is still active.
  3. Purge Durable history for that incident instance.
  4. Requeue the original alert payload to Service Bus.
  5. Wait for a fresh initial response to return the incident to pending_approval.
  6. Optionally replay the latest stored more_info question (or a supplied one).
  7. Wait for the follow-up response and print the final summary.

Usage:
    python scripts/recover_live_incident.py --incident-id INC-2026-0001 --dry-run

    python scripts/recover_live_incident.py --incident-id INC-2026-0001 --yes

    python scripts/recover_live_incident.py \
      --incident-id INC-2026-0001 \
      --question "Re-check the sensor calibration hypothesis." \
      --yes
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str((ROOT / "backend").resolve()))

from reset_dev_data import (  # noqa: E402
    DURABLE_TERMINATE_MAX_ATTEMPTS,
    DURABLE_TERMINATE_POLL_SECONDS,
    ensure_az_ready,
    get_cosmos_client,
    get_function_master_key,
    load_local_settings,
    resolve_defaults,
)

TERMINAL_DURABLE_STATUSES = {"Completed", "Failed", "Terminated"}
DEFAULT_WAIT_TIMEOUT = 480
DEFAULT_POLL_INTERVAL = 10
DEFAULT_RECOVERY_USER = "ivan.petrenko"


def build_parser() -> argparse.ArgumentParser:
    defaults = resolve_defaults()
    parser = argparse.ArgumentParser(description="Recover a stuck live incident in Azure")
    parser.add_argument("--incident-id", required=True, help="Incident ID to recover, e.g. INC-2026-0001")
    parser.add_argument("--dry-run", action="store_true", help="Preview the recovery plan without changing Azure state")
    parser.add_argument("--yes", action="store_true", help="Skip the interactive confirmation prompt")
    parser.add_argument(
        "--skip-more-info-replay",
        action="store_true",
        help="Stop after the fresh initial round reaches pending_approval instead of replaying more_info",
    )
    parser.add_argument(
        "--question",
        help="Override the stored more_info question that should be replayed after the initial round",
    )
    parser.add_argument(
        "--user-id",
        default="",
        help="User ID to attach to the replayed more_info decision (defaults to the latest stored actor)",
    )
    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=DEFAULT_WAIT_TIMEOUT,
        help=f"Seconds to wait for each recovery phase (default: {DEFAULT_WAIT_TIMEOUT})",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=DEFAULT_POLL_INTERVAL,
        help=f"Seconds between status polls (default: {DEFAULT_POLL_INTERVAL})",
    )
    parser.add_argument("--resource-group", default=defaults["resource_group"], help="Azure resource group")
    parser.add_argument("--function-app", default=defaults["function_app"], help="Azure Function App name")
    parser.add_argument("--cosmos-account", default=defaults["cosmos_account"], help="Cosmos DB account name")
    parser.add_argument("--cosmos-database", default=defaults["cosmos_database"], help="Cosmos DB database name")
    parser.add_argument("--cosmos-endpoint", default=defaults["cosmos_endpoint"], help="Cosmos DB endpoint URL")
    return parser


def durable_base_url(args: argparse.Namespace) -> str:
    return f"https://{args.function_app}.azurewebsites.net"


def request_json(url: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    headers = {} if body is None else {"Content-Type": "application/json"}
    request = urllib.request.Request(url, data=payload, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read().decode()
    return json.loads(raw) if raw else {}


def durable_instance_url(args: argparse.Namespace, master_key: str, incident_id: str) -> str:
    encoded_key = urllib.parse.quote(master_key, safe="")
    return f"{durable_base_url(args)}/runtime/webhooks/durabletask/instances/durable-{incident_id}?code={encoded_key}"


def get_durable_status(args: argparse.Namespace, master_key: str, incident_id: str) -> dict[str, Any] | None:
    try:
        status = request_json(durable_instance_url(args, master_key, incident_id))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    if isinstance(status, dict):
        return status
    return None


def terminate_instance(args: argparse.Namespace, master_key: str, incident_id: str) -> str:
    status = get_durable_status(args, master_key, incident_id)
    if status is None:
        return "not_found"

    runtime_status = str(status.get("runtimeStatus") or "Unknown")
    if runtime_status in TERMINAL_DURABLE_STATUSES:
        return runtime_status

    encoded_key = urllib.parse.quote(master_key, safe="")
    reason = urllib.parse.quote("recover_live_incident.py", safe="")
    terminate_url = (
        f"{durable_base_url(args)}/runtime/webhooks/durabletask/instances/"
        f"durable-{incident_id}/terminate?code={encoded_key}&reason={reason}"
    )
    request_json(terminate_url, method="POST")

    deadline = time.time() + DURABLE_TERMINATE_MAX_ATTEMPTS * DURABLE_TERMINATE_POLL_SECONDS + 30
    while time.time() < deadline:
        current = get_durable_status(args, master_key, incident_id)
        current_status = (current or {}).get("runtimeStatus", "not_found")
        if current is None or current_status in TERMINAL_DURABLE_STATUSES:
            return str(current_status)
        time.sleep(DURABLE_TERMINATE_POLL_SECONDS)

    raise RuntimeError(f"Timed out waiting for durable-{incident_id} to terminate")


def purge_instance_history(args: argparse.Namespace, master_key: str, incident_id: str) -> str:
    url = durable_instance_url(args, master_key, incident_id)
    request = urllib.request.Request(url, method="DELETE")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return str(response.status)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return "404"
        raise


def get_database(args: argparse.Namespace):
    return get_cosmos_client(args).get_database_client(args.cosmos_database)


def query_single_incident(db, incident_id: str) -> dict[str, Any]:
    rows = list(
        db.get_container_client("incidents").query_items(
            "SELECT * FROM c WHERE c.id = @incident_id",
            parameters=[{"name": "@incident_id", "value": incident_id}],
            enable_cross_partition_query=True,
        )
    )
    if not rows:
        raise RuntimeError(f"Incident {incident_id} was not found in Cosmos DB")
    return rows[0]


def query_events(db, incident_id: str, *, action: str | None = None, newest_first: bool = True) -> list[dict[str, Any]]:
    order = "DESC" if newest_first else "ASC"
    if action:
        query = (
            "SELECT * FROM c WHERE c.incidentId = @incident_id AND c.action = @action "
            f"ORDER BY c.timestamp {order}"
        )
        params = [
            {"name": "@incident_id", "value": incident_id},
            {"name": "@action", "value": action},
        ]
    else:
        query = f"SELECT * FROM c WHERE c.incidentId = @incident_id ORDER BY c.timestamp {order}"
        params = [{"name": "@incident_id", "value": incident_id}]
    return list(
        db.get_container_client("incident_events").query_items(
            query,
            parameters=params,
            enable_cross_partition_query=True,
        )
    )


def reconstruct_alert_payload(incident: dict[str, Any]) -> dict[str, Any]:
    incident_id = str(incident.get("id") or incident.get("incident_id") or incident.get("incidentId") or "")
    equipment_id = str(incident.get("equipment_id") or incident.get("equipmentId") or "")
    batch_id = str(incident.get("batch_id") or incident.get("batchId") or "")
    alert_id = incident.get("alert_id") or incident.get("source_alert_id")
    payload: dict[str, Any] = {
        "id": incident_id,
        "incident_id": incident_id,
        "incidentId": incident_id,
        "equipment_id": equipment_id,
        "equipmentId": equipment_id,
        "severity": incident.get("severity", "critical"),
        "status": "open",
        "reported_at": incident.get("reported_at") or incident.get("createdAt") or incident.get("created_at"),
        "createdAt": incident.get("createdAt") or incident.get("created_at") or incident.get("reported_at"),
        "updatedAt": incident.get("createdAt") or incident.get("created_at") or incident.get("reported_at"),
        "equipment_name": incident.get("equipment_name") or incident.get("title") or equipment_id,
        "equipment_criticality": incident.get("equipment_criticality") or "unknown",
        "equipment_type": incident.get("equipment_type") or "unknown",
        "location": incident.get("location") or "unknown",
        "title": incident.get("title") or incident_id,
    }

    for key in (
        "deviation_type",
        "parameter",
        "measured_value",
        "lower_limit",
        "upper_limit",
        "unit",
        "duration_seconds",
        "detected_by",
        "detected_at",
    ):
        if key in incident and incident[key] is not None:
            payload[key] = incident[key]

    if alert_id:
        payload["alert_id"] = alert_id
        payload["source_alert_id"] = alert_id
    if batch_id:
        payload["batch_id"] = batch_id
    if incident.get("parameter_excursion") is not None:
        payload["parameter_excursion"] = incident["parameter_excursion"]

    return payload


def build_replay_question(args: argparse.Namespace, more_info_events: list[dict[str, Any]]) -> tuple[str | None, str]:
    if args.skip_more_info_replay:
        return None, args.user_id or DEFAULT_RECOVERY_USER

    if args.question:
        return args.question.strip(), args.user_id or DEFAULT_RECOVERY_USER

    latest = more_info_events[0] if more_info_events else None
    if not latest:
        return None, args.user_id or DEFAULT_RECOVERY_USER

    question = str(latest.get("details") or latest.get("question") or "").strip()
    user_id = args.user_id or str(latest.get("actor") or latest.get("userId") or DEFAULT_RECOVERY_USER)
    return question or None, user_id


def existing_agent_response_ids(db, incident_id: str) -> set[str]:
    rows = query_events(db, incident_id, action="agent_response", newest_first=True)
    return {str(row.get("id")) for row in rows if row.get("id")}


def wait_for_initial_round(
    db,
    incident_id: str,
    known_response_ids: set[str],
    *,
    timeout: int,
    poll_interval: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        incident = query_single_incident(db, incident_id)
        rows = query_events(db, incident_id, action="agent_response", newest_first=True)
        new_row = next(
            (
                row
                for row in rows
                if str(row.get("id")) not in known_response_ids and int(row.get("round", 0) or 0) == 0
            ),
            None,
        )
        if incident.get("status") == "pending_approval" and new_row:
            return incident, new_row
        time.sleep(poll_interval)

    raise RuntimeError(f"Fresh initial round for {incident_id} did not reach pending_approval in time")


def replay_more_info(args: argparse.Namespace, incident_id: str, question: str, user_id: str) -> dict[str, Any] | list[Any]:
    url = f"{durable_base_url(args)}/api/incidents/{incident_id}/decision"
    return request_json(
        url,
        method="POST",
        body={
            "action": "more_info",
            "user_id": user_id,
            "role": "operator",
            "question": question,
        },
    )


def wait_for_follow_up_round(
    db,
    incident_id: str,
    known_response_ids: set[str],
    *,
    timeout: int,
    poll_interval: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        incident = query_single_incident(db, incident_id)
        rows = query_events(db, incident_id, action="agent_response", newest_first=True)
        new_row = next(
            (
                row
                for row in rows
                if str(row.get("id")) not in known_response_ids and int(row.get("round", 0) or 0) > 0
            ),
            None,
        )
        if incident.get("status") == "pending_approval" and new_row:
            return incident, new_row
        time.sleep(poll_interval)

    raise RuntimeError(f"Follow-up round for {incident_id} did not return to pending_approval in time")


def print_preview(
    incident: dict[str, Any],
    durable_status: dict[str, Any] | None,
    payload: dict[str, Any],
    replay_question: str | None,
) -> None:
    summary = {
        "incident_id": incident.get("id"),
        "status": incident.get("status"),
        "durable_runtime_status": None if durable_status is None else durable_status.get("runtimeStatus"),
        "detected_at": payload.get("detected_at"),
        "equipment_id": payload.get("equipment_id"),
        "parameter": payload.get("parameter"),
        "measured_value": payload.get("measured_value"),
        "replay_more_info": replay_question,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def confirm_recovery(args: argparse.Namespace, replay_question: str | None) -> bool:
    if args.yes:
        return True

    print("\nThis will terminate and purge the Durable instance history for the incident, then requeue it.")
    if replay_question:
        print("The script will also replay one more_info question after the fresh initial round is ready.")
    phrase = input(f"Type RECOVER {args.incident_id} to continue: ").strip()
    return phrase == f"RECOVER {args.incident_id}"


def publish_original_alert(payload: dict[str, Any]) -> None:
    from shared.servicebus_client import publish_alert

    publish_alert(payload)


def main() -> int:
    load_local_settings()
    parser = build_parser()
    args = parser.parse_args()

    try:
        ensure_az_ready()
        db = get_database(args)
        incident = query_single_incident(db, args.incident_id)
        more_info_events = query_events(db, args.incident_id, action="more_info", newest_first=True)
        replay_question, replay_user = build_replay_question(args, more_info_events)
        master_key = get_function_master_key(args)
        durable_status = get_durable_status(args, master_key, args.incident_id)
        payload = reconstruct_alert_payload(incident)
        known_response_ids = existing_agent_response_ids(db, args.incident_id)

        if args.dry_run:
            print_preview(incident, durable_status, payload, replay_question)
            print("\nDry-run only. No Azure resources were modified.")
            return 0

        if not confirm_recovery(args, replay_question):
            print("Aborted.")
            return 1

        termination_result = terminate_instance(args, master_key, args.incident_id)
        print(f"Terminated durable instance status: {termination_result}")

        purge_result = purge_instance_history(args, master_key, args.incident_id)
        print(f"Purged durable history response: {purge_result}")

        publish_original_alert(payload)
        print(f"Requeued original alert payload for {args.incident_id}")

        incident_after_initial, initial_response = wait_for_initial_round(
            db,
            args.incident_id,
            known_response_ids,
            timeout=args.wait_timeout,
            poll_interval=args.poll_interval,
        )
        print(
            json.dumps(
                {
                    "phase": "initial_round_ready",
                    "status": incident_after_initial.get("status"),
                    "response_round": initial_response.get("round"),
                    "response": initial_response.get("details"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        if not replay_question:
            print("\nNo more_info replay requested. Recovery completed after the fresh initial round.")
            return 0

        replay_result = replay_more_info(args, args.incident_id, replay_question, replay_user)
        print(json.dumps({"phase": "more_info_replayed", "result": replay_result}, ensure_ascii=False, indent=2))

        known_response_ids.add(str(initial_response.get("id")))
        incident_after_follow_up, follow_up_response = wait_for_follow_up_round(
            db,
            args.incident_id,
            known_response_ids,
            timeout=args.wait_timeout,
            poll_interval=args.poll_interval,
        )
        ai_analysis = incident_after_follow_up.get("ai_analysis") or {}
        print(
            json.dumps(
                {
                    "phase": "follow_up_ready",
                    "status": incident_after_follow_up.get("status"),
                    "response_round": follow_up_response.get("round"),
                    "response": follow_up_response.get("details"),
                    "risk_level": ai_analysis.get("risk_level"),
                    "confidence_flag": ai_analysis.get("confidence_flag"),
                    "recommendation": ai_analysis.get("recommendation"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except KeyboardInterrupt:
        print("\nAborted.")
        return 130
    except Exception as exc:
        print(f"\nRecovery failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())