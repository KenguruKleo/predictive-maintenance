#!/usr/bin/env python3
"""
scripts/simulate_alerts.py
Send mock SCADA/MES alerts to the POST /api/alerts endpoint.

This is how we simulate alerts in absence of a real SCADA system:
  - Local dev  : func start → http://localhost:7071/api/alerts
  - Azure      : https://<func>.azurewebsites.net/api/alerts?code=<key>

Usage:
    # Local (Azure Functions Core Tools running in backend/)
    python scripts/simulate_alerts.py --local

    # Azure deployed endpoint
    FUNCTION_URL="https://func-sentinel-intel-dev-erzrpo.azurewebsites.net/api/alerts" \\
    FUNCTION_KEY="<key>" \\
    python scripts/simulate_alerts.py

    # Run a specific scenario
    python scripts/simulate_alerts.py --local --scenario 1

    # List available scenarios
    python scripts/simulate_alerts.py --list

    # Run all scenarios in sequence
    python scripts/simulate_alerts.py --local --all

Environment variables:
    FUNCTION_URL   Full URL to the /api/alerts endpoint (default: local)
    FUNCTION_KEY   Function auth key (appended as ?code=<key> if not in URL)
    FUNCTION_CODE  Alias for FUNCTION_KEY
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("❌  requests not installed: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Demo scenarios — realistic GMP deviations for the demo
# ---------------------------------------------------------------------------

NOW = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

SCENARIOS = [
    {
        "id": 1,
        "name": "GR-204 Impeller Speed LOW (major) — primary demo scenario",
        "description": "Granulator impeller speed dropped 20 RPM below lower limit for ~4 min",
        "payload": {
            "alert_id": "SCADA-2026-0417-001",
            "equipment_id": "GR-204",
            "deviation_type": "process_parameter_excursion",
            "parameter": "impeller_speed_rpm",
            "measured_value": 580,
            "lower_limit": 600,
            "upper_limit": 800,
            "unit": "RPM",
            "duration_seconds": 247,
            "detected_by": "scada_monitor",
            "detected_at": NOW,
            "batch_id": "BATCH-2026-0416-GR204",
        },
    },
    {
        "id": 2,
        "name": "GR-204 Spray Rate HIGH (critical) — 35 min excursion",
        "description": "Binder spray rate 25% above PAR for 35 min → risk of over-granulation",
        "payload": {
            "alert_id": "SCADA-2026-0417-002",
            "equipment_id": "GR-204",
            "deviation_type": "process_parameter_excursion",
            "parameter": "spray_rate_g_min",
            "measured_value": 138,
            "lower_limit": 70,
            "upper_limit": 110,
            "unit": "g/min",
            "duration_seconds": 2100,
            "detected_by": "scada_monitor",
            "detected_at": NOW,
            "batch_id": "BATCH-2026-0417-GR204",
        },
    },
    {
        "id": 3,
        "name": "MIX-102 Motor current SPIKE (minor) — brief anomaly",
        "description": "Mixer motor current 3% above limit for 45 seconds — minor alert",
        "payload": {
            "alert_id": "SCADA-2026-0417-003",
            "equipment_id": "MIX-102",
            "deviation_type": "process_parameter_excursion",
            "parameter": "motor_current_amp",
            "measured_value": 41.5,
            "lower_limit": 0,
            "upper_limit": 40,
            "unit": "A",
            "duration_seconds": 45,
            "detected_by": "plc_monitor",
            "detected_at": NOW,
        },
    },
    {
        "id": 4,
        "name": "DRY-303 Inlet Temperature LOW (major) — spray dryer",
        "description": "Inlet air temperature fell below lower limit during drying phase",
        "payload": {
            "alert_id": "SCADA-2026-0417-004",
            "equipment_id": "DRY-303",
            "deviation_type": "process_parameter_excursion",
            "parameter": "inlet_air_temperature_c",
            "measured_value": 42,
            "lower_limit": 48,
            "upper_limit": 62,
            "unit": "°C",
            "duration_seconds": 480,
            "detected_by": "scada_monitor",
            "detected_at": NOW,
            "batch_id": "BATCH-2026-0417-DRY303",
        },
    },
    {
        "id": 5,
        "name": "GR-204 Impeller Speed LOW — DUPLICATE (idempotency test)",
        "description": "Same alert_id as scenario 1 — should return 200 already_exists",
        "payload": {
            "alert_id": "SCADA-2026-0417-001",   # ← same as scenario 1
            "equipment_id": "GR-204",
            "deviation_type": "process_parameter_excursion",
            "parameter": "impeller_speed_rpm",
            "measured_value": 580,
            "lower_limit": 600,
            "upper_limit": 800,
            "unit": "RPM",
            "duration_seconds": 247,
            "detected_by": "scada_monitor",
            "detected_at": NOW,
        },
    },
    {
        "id": 6,
        "name": "Invalid payload — validation test",
        "description": "Missing required field 'unit' → expect 400",
        "payload": {
            "equipment_id": "GR-204",
            "deviation_type": "process_parameter_excursion",
            "parameter": "impeller_speed_rpm",
            "measured_value": 580,
            "lower_limit": 600,
            "upper_limit": 800,
            # 'unit' intentionally omitted
        },
    },
    {
        "id": 7,
        "name": "MIX-102 Motor Current — borderline transient (REJECT expected)",
        "description": (
            "Motor current 1.2% above upper limit for only 8 seconds during mixer start-up. "
            "Transient spike well within equipment tolerance; no batch impact; "
            "no historical pattern. Agent should recommend REJECT / no action required."
        ),
        "payload": {
            "alert_id": "SCADA-2026-0417-007",
            "equipment_id": "MIX-102",
            "deviation_type": "process_parameter_excursion",
            "parameter": "motor_current_amp",
            "measured_value": 40.5,
            "lower_limit": 0,
            "upper_limit": 40,
            "unit": "A",
            "duration_seconds": 8,
            "detected_by": "plc_monitor",
            "detected_at": NOW,
            "batch_id": "BATCH-2026-0417-MIX102",
            "notes": (
                "Start-up transient. Equipment log shows identical spikes on 3 prior "
                "start-up events this week, all auto-cleared. No product exposure risk. "
                "Maintenance confirmed no mechanical fault."
            ),
        },
    },
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_url(base_url: str, key: str | None) -> str:
    if key and "code=" not in base_url:
        sep = "&" if "?" in base_url else "?"
        return f"{base_url}{sep}code={key}"
    return base_url


def send_alert(url: str, payload: dict, scenario_name: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  Scenario: {scenario_name}")
    print(f"  URL     : {url.split('?')[0]}...")
    print(f"  Payload :")
    print(json.dumps(payload, indent=4))

    try:
        resp = requests.post(url, json=payload, timeout=15)
    except requests.exceptions.ConnectionError:
        print("  ❌  Connection refused — is the function running?")
        print("       Local: cd backend && func start")
        return
    except requests.exceptions.Timeout:
        print("  ❌  Request timed out")
        return

    status_icon = "✅" if resp.status_code in (200, 202) else "⚠️ " if resp.status_code == 400 else "❌"
    print(f"\n  {status_icon}  HTTP {resp.status_code}")
    try:
        print(f"  Response: {json.dumps(resp.json(), indent=4)}")
    except Exception:
        print(f"  Response: {resp.text[:300]}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate SCADA/MES alerts → POST /api/alerts"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Target local Azure Functions (http://localhost:7071)",
    )
    parser.add_argument(
        "--scenario",
        type=int,
        metavar="N",
        help="Run a single scenario by number (see --list)",
    )
    parser.add_argument(
        "--all",
        dest="run_all",
        action="store_true",
        help="Run all scenarios in sequence",
    )
    parser.add_argument(
        "--list",
        dest="list_scenarios",
        action="store_true",
        help="List available scenarios and exit",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Append a timestamp suffix to alert_ids (allows re-running without idempotency dedup)",
    )
    args = parser.parse_args()

    # List mode
    if args.list_scenarios:
        print("\nAvailable scenarios:")
        for s in SCENARIOS:
            print(f"  [{s['id']}] {s['name']}")
            print(f"       {s['description']}")
        return

    # Resolve URL
    if args.local:
        base_url = "http://localhost:7071/api/alerts"
        func_key = None
    else:
        base_url = os.getenv("FUNCTION_URL", "")
        func_key = os.getenv("FUNCTION_KEY") or os.getenv("FUNCTION_CODE")
        if not base_url:
            print("❌  Set FUNCTION_URL env var or use --local flag")
            print("     export FUNCTION_URL=https://<func>.azurewebsites.net/api/alerts")
            sys.exit(1)

    url = build_url(base_url, func_key)

    print(f"\n{'='*60}")
    print(f"  Sentinel Intelligence — Alert Simulator")
    print(f"{'='*60}")
    print(f"  Target: {'LOCAL (func start)' if args.local else base_url.split('?')[0]}")

    if args.scenario:
        scenarios = [s for s in SCENARIOS if s["id"] == args.scenario]
        if not scenarios:
            print(f"\n❌  Scenario {args.scenario} not found. Run --list to see options.")
            sys.exit(1)
    elif args.run_all:
        scenarios = SCENARIOS
    else:
        # Interactive: show menu
        print("\nSelect a scenario:")
        for s in SCENARIOS:
            print(f"  [{s['id']}] {s['name']}")
        choice = input("\nEnter scenario number (or 'a' for all): ").strip()
        if choice.lower() == "a":
            scenarios = SCENARIOS
        else:
            try:
                num = int(choice)
                scenarios = [s for s in SCENARIOS if s["id"] == num]
                if not scenarios:
                    print(f"❌  Invalid choice: {choice}")
                    sys.exit(1)
            except ValueError:
                print(f"❌  Invalid input: {choice}")
                sys.exit(1)

    import time
    fresh_suffix = str(int(time.time()))[-6:] if args.fresh else None

    for s in scenarios:
        payload = dict(s["payload"])
        if fresh_suffix and "alert_id" in payload:
            orig_id = payload["alert_id"]
            payload["alert_id"] = f"{orig_id}-{fresh_suffix}"
        send_alert(url, payload, s["name"])

    print(f"\n{'='*60}")
    print(f"  Done. Check Service Bus queue or Function logs for results.")
    print()


if __name__ == "__main__":
    main()
