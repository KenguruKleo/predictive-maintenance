"""
HTTP Trigger — GET /api/stats/summary (T-031)

Returns incident statistics for the QA Manager / IT Admin dashboard.
"""

import json
import logging

import azure.functions as func

from shared.cosmos_client import get_container
from utils.auth import AuthError, get_caller_roles, require_any_role

logger = logging.getLogger(__name__)

bp = func.Blueprint()

ALLOWED_ROLES = ["QAManager", "ITAdmin"]


@bp.route(route="stats/summary", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def get_stats_summary(req: func.HttpRequest) -> func.HttpResponse:
    """Return aggregate incident statistics for the dashboard."""
    try:
        roles = get_caller_roles(req)
        require_any_role(roles, ALLOWED_ROLES)
    except AuthError as exc:
        return _error(exc.status_code, exc.message)

    try:
        container = get_container("incidents")

        # Cosmos DB cross-partition queries only support VALUE <AggregateFunc> for aggregates,
        # so GROUP BY is not available. Fetch status/severity/risk_level and aggregate in Python.
        all_rows = list(container.query_items(
            query="SELECT c.status, c.severity, c.ai_analysis.risk_level AS risk_level FROM c",
            enable_cross_partition_query=True,
        ))

        by_status: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        pending = 0
        open_count = 0
        high_risk = 0
        closed_statuses = {"closed", "rejected", "completed"}
        high_risk_levels = {"high", "critical"}

        for row in all_rows:
            st = row.get("status") or ""
            sv = row.get("severity") or ""
            rl = row.get("risk_level") or ""

            by_status[st] = by_status.get(st, 0) + 1
            by_severity[sv] = by_severity.get(sv, 0) + 1
            if st == "pending_approval":
                pending += 1
            if st not in closed_statuses:
                open_count += 1
            if rl in high_risk_levels:
                high_risk += 1

        return _json({
            "by_status": by_status,
            "by_severity": by_severity,
            "pending_approval": pending,
            "open_incidents": open_count,
            "high_risk_incidents": high_risk,
        })

    except Exception as exc:  # noqa: BLE001
        logger.exception("get_stats_summary failed: %s", exc)
        return _error(500, "Internal server error")


def _json(data) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps(data, default=str),
        status_code=200,
        mimetype="application/json",
    )


def _error(status: int, message: str) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps({"error": message}),
        status_code=status,
        mimetype="application/json",
    )
