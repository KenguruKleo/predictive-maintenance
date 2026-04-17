#!/usr/bin/env python3
"""
scripts/test_mcp_servers.py
Functional test for all 3 MCP servers.

Tests tool functions directly by importing server modules —
no stdio transport required, but DOES require a live seeded Cosmos DB.

Prerequisites:
    - Cosmos DB seeded: python scripts/seed_cosmos.py
    - .env with COSMOS_ENDPOINT (and optionally COSMOS_KEY)

Usage:
    python scripts/test_mcp_servers.py
    python scripts/test_mcp_servers.py --server sentinel-db   # single server
    python scripts/test_mcp_servers.py --server qms
    python scripts/test_mcp_servers.py --server cmms
"""

import argparse
import importlib.util
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).parent.parent
MCP_DIR = ROOT / "backend"

# Add backend/ to path so mcp_sentinel_db, mcp_qms, mcp_cmms are importable
sys.path.insert(0, str(MCP_DIR))

# Load .env before importing server modules
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# ── helpers ───────────────────────────────────────────────────────────────

_passed = 0
_failed = 0


def ok(label: str, detail: str = ""):
    global _passed
    _passed += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  ✅  {label}{suffix}")


def fail(label: str, e: Exception):
    global _failed
    _failed += 1
    print(f"  ❌  {label}")
    traceback.print_exc()


def load_server(pkg: str) -> object:
    """Import a server module from mcp-servers/<pkg>/server.py."""
    spec = importlib.util.spec_from_file_location(
        f"{pkg}_server",
        MCP_DIR / pkg / "server.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── mcp-sentinel-db ───────────────────────────────────────────────────────

def test_sentinel_db():
    print("\n── mcp-sentinel-db ──────────────────────────────────────────")
    mod = load_server("mcp_sentinel_db")

    # get_equipment
    try:
        result = mod.get_equipment("GR-204")
        assert result["id"] == "GR-204", "id mismatch"
        assert "validated_parameters" in result, "validated_parameters missing"
        ok("get_equipment(GR-204)", result["name"])
    except Exception as e:
        fail("get_equipment", e)

    # get_batch
    try:
        result = mod.get_batch("BATCH-2026-0416-GR204")
        assert result["id"] == "BATCH-2026-0416-GR204", "id mismatch"
        ok("get_batch(BATCH-2026-0416-GR204)", result.get("product_name", ""))
    except Exception as e:
        fail("get_batch", e)

    # get_incident
    try:
        result = mod.get_incident("INC-2026-0001")
        assert result["id"] == "INC-2026-0001", "id mismatch"
        ok("get_incident(INC-2026-0001)", f"severity={result.get('severity')}")
    except Exception as e:
        fail("get_incident", e)

    # search_incidents
    try:
        results = mod.search_incidents("GR-204", limit=3)
        assert isinstance(results, list), "expected list"
        ok("search_incidents(GR-204, limit=3)", f"{len(results)} incident(s)")
    except Exception as e:
        fail("search_incidents", e)

    # get_template — work_order
    try:
        result = mod.get_template("work_order")
        assert result["type"] == "work_order", "type mismatch"
        ok("get_template(work_order)", result.get("name", ""))
    except Exception as e:
        fail("get_template(work_order)", e)

    # get_template — audit_entry
    try:
        result = mod.get_template("audit_entry")
        assert result["type"] == "audit_entry", "type mismatch"
        ok("get_template(audit_entry)", result.get("name", ""))
    except Exception as e:
        fail("get_template(audit_entry)", e)


# ── mcp-qms ───────────────────────────────────────────────────────────────

def test_qms():
    print("\n── mcp-qms ──────────────────────────────────────────────────")
    mod = load_server("mcp_qms")

    try:
        result = mod.create_audit_entry(
            incident_id="INC-2026-0001",
            equipment_id="GR-204",
            deviation_type="process_parameter_excursion",
            description=(
                "Impeller speed dropped to 580 RPM (validated range: 600–800 RPM) "
                "during binder addition phase. Duration: ~4 minutes."
            ),
            root_cause=(
                "Motor load fluctuation during high-viscosity binder phase. "
                "No equipment malfunction detected."
            ),
            capa_actions=(
                "1. Perform immediate in-process moisture check (target 8–12%).\n"
                "2. Increase sampling frequency for this batch.\n"
                "3. Schedule preventive calibration of impeller motor load cell within 30 days."
            ),
            batch_disposition="conditional_release_pending_testing",
            prepared_by="qa.test.user",
        )
        ae_id = result.get("audit_entry_id", "")
        assert ae_id.startswith("AE-"), f"unexpected audit_entry_id: {ae_id}"
        assert "qms_url" in result, "qms_url missing"
        assert "created_at" in result, "created_at missing"
        ok("create_audit_entry", f"{ae_id} | {result['qms_url']}")
    except Exception as e:
        fail("create_audit_entry", e)


# ── mcp-cmms ──────────────────────────────────────────────────────────────

def test_cmms():
    print("\n── mcp-cmms ─────────────────────────────────────────────────")
    mod = load_server("mcp_cmms")

    try:
        result = mod.create_work_order(
            incident_id="INC-2026-0001",
            equipment_id="GR-204",
            title="GR-204 — Impeller motor load calibration — INC-2026-0001",
            description=(
                "Corrective maintenance following impeller speed deviation (INC-2026-0001). "
                "Inspect motor load cell, verify calibration, check drive belt tension."
            ),
            priority="high",
            assigned_to="maintenance_tech",
            due_date="2026-04-24",
            work_type="corrective",
        )
        wo_id = result.get("work_order_id", "")
        assert wo_id.startswith("WO-"), f"unexpected work_order_id: {wo_id}"
        assert "cmms_url" in result, "cmms_url missing"
        assert "created_at" in result, "created_at missing"
        ok("create_work_order", f"{wo_id} | {result['cmms_url']}")
    except Exception as e:
        fail("create_work_order", e)


# ── main ──────────────────────────────────────────────────────────────────

SERVERS = {
    "sentinel-db": test_sentinel_db,
    "qms": test_qms,
    "cmms": test_cmms,
}


def main():
    parser = argparse.ArgumentParser(description="Test Sentinel Intelligence MCP servers")
    parser.add_argument(
        "--server",
        choices=list(SERVERS.keys()),
        help="Test a single server only. Default: run all.",
    )
    args = parser.parse_args()

    print("=" * 65)
    print("Sentinel Intelligence — MCP Servers Test")
    print("=" * 65)

    if args.server:
        SERVERS[args.server]()
    else:
        for fn in SERVERS.values():
            fn()

    print(f"\n{'=' * 65}")
    print(f"Results: {_passed} passed, {_failed} failed")
    if _failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
