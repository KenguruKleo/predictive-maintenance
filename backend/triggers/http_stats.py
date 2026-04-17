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

        # Total by status
        by_status_results = list(container.query_items(
            query="SELECT c.status, COUNT(1) AS cnt FROM c GROUP BY c.status",
            enable_cross_partition_query=True,
        ))
        by_status = {r["status"]: r["cnt"] for r in by_status_results}

        # Total by severity
        by_severity_results = list(container.query_items(
            query="SELECT c.severity, COUNT(1) AS cnt FROM c GROUP BY c.severity",
            enable_cross_partition_query=True,
        ))
        by_severity = {r["severity"]: r["cnt"] for r in by_severity_results}

        # Pending approval count
        pending_results = list(container.query_items(
            query="SELECT VALUE COUNT(1) FROM c WHERE c.status = 'pending_approval'",
            enable_cross_partition_query=True,
        ))
        pending = pending_results[0] if pending_results else 0

        # Open (not closed/rejected) count
        open_results = list(container.query_items(
            query="SELECT VALUE COUNT(1) FROM c WHERE c.status NOT IN ('closed', 'rejected', 'completed')",
            enable_cross_partition_query=True,
        ))
        open_count = open_results[0] if open_results else 0

        # Critical/high risk count
        high_risk_results = list(container.query_items(
            query="SELECT VALUE COUNT(1) FROM c WHERE c.ai_analysis.risk_level IN ('high', 'critical')",
            enable_cross_partition_query=True,
        ))
        high_risk = high_risk_results[0] if high_risk_results else 0

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
