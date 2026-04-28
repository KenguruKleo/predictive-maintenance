"""
HTTP Trigger — GET /api/stats/summary (T-031)

Returns incident statistics for the QA Manager / IT Admin dashboard.
"""

import json
import logging
from datetime import datetime

import azure.functions as func

from shared.cosmos_client import get_container
from utils.auth import AuthError, get_caller_roles, require_any_role

logger = logging.getLogger(__name__)

bp = func.Blueprint()

ALLOWED_ROLES = ["QAManager", "ITAdmin"]
DECISIONS_DEFAULT_PAGE_SIZE = 20


@bp.route(route="stats/decisions", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def get_decisions(req: func.HttpRequest) -> func.HttpResponse:
    """Return paginated closed decisions for the Manager Dashboard infinite scroll."""
    try:
        roles = get_caller_roles(req)
        require_any_role(roles, ALLOWED_ROLES)
    except AuthError as exc:
        return _error(exc.status_code, exc.message)

    try:
        page = max(1, int(req.params.get("page") or 1))
        page_size = min(100, max(1, int(req.params.get("page_size") or DECISIONS_DEFAULT_PAGE_SIZE)))
    except (TypeError, ValueError):
        return _error(400, "Invalid page or page_size parameter")

    try:
        container = get_container("incidents")
        all_rows = list(container.query_items(
            query=(
                "SELECT c.id, c.incident_number, c.status, "
                "c.ai_analysis.confidence AS confidence, "
                "c.createdAt, c.created_at, c.reported_at, c.closedAt, c.finalDecision, "
                "c.agentRecommendation, c.operatorAgreesWithAgent "
                "FROM c"
            ),
            enable_cross_partition_query=True,
        ))
        all_decisions = _build_all_decisions(all_rows)
        total = len(all_decisions)
        offset = (page - 1) * page_size
        items = all_decisions[offset: offset + page_size]
        return _json({
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        })
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_decisions failed: %s", exc)
        return _error(500, "Internal server error")


@bp.route(route="stats/summary", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
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
            query=(
                "SELECT c.id, c.incident_number, c.status, c.severity, "
                "c.ai_analysis.risk_level AS risk_level, c.ai_analysis.confidence AS confidence, "
                "c.createdAt, c.created_at, c.reported_at, c.closedAt, c.finalDecision, "
                "c.agentRecommendation, c.operatorAgreesWithAgent "
                "FROM c"
            ),
            enable_cross_partition_query=True,
        ))

        by_status: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        pending = 0
        open_count = 0
        high_risk = 0
        closed_statuses = {"closed", "rejected", "completed"}
        high_risk_levels = {"high", "critical"}
        recent_decisions = _build_all_decisions(all_rows)[:10]

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
            "recent_decisions": recent_decisions,
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


def _build_all_decisions(rows: list[dict]) -> list[dict]:
    items: list[dict] = []

    for row in rows:
        final_decision = row.get("finalDecision") or {}
        if not isinstance(final_decision, dict):
            continue

        action = str(final_decision.get("action") or "").strip().lower()
        if action not in {"approved", "rejected"}:
            continue

        decided_at = _coerce_iso_datetime(row.get("closedAt"))
        if not decided_at:
            continue

        created_at = (
            _coerce_iso_datetime(row.get("createdAt"))
            or _coerce_iso_datetime(row.get("created_at"))
            or _coerce_iso_datetime(row.get("reported_at"))
        )
        response_time_minutes = _minutes_between(created_at, decided_at)
        items.append({
            "incident_id": row.get("id") or "",
            "incident_number": row.get("incident_number") or row.get("id") or "",
            "operator": _format_decision_actor(final_decision),
            "decision": action,
            "ai_confidence": _coerce_float(row.get("confidence")),
            "human_override": row.get("operatorAgreesWithAgent") is False,
            "agent_recommendation": row.get("agentRecommendation"),
            "operator_agrees_with_agent": row.get("operatorAgreesWithAgent"),
            "decided_at": decided_at.isoformat(),
            "response_time_minutes": response_time_minutes,
        })

    items.sort(key=lambda item: item.get("decided_at") or "", reverse=True)
    return items


def _build_recent_decisions(rows: list[dict]) -> list[dict]:
    """Backward-compatible helper kept for unit tests and summary call sites."""
    return _build_all_decisions(rows)


def _coerce_float(value) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _coerce_iso_datetime(value) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _minutes_between(start: datetime | None, end: datetime | None) -> int:
    if not start or not end:
        return 0
    delta_seconds = (end - start).total_seconds()
    return max(0, int(round(delta_seconds / 60)))


def _normalize_decision_role(role: str | None) -> str:
    normalized = str(role or "").strip().lower().replace("_", "-")
    if normalized == "qamanager":
        return "qa-manager"
    return normalized


def _format_decision_actor(decision: dict) -> str:
    role = _normalize_decision_role(decision.get("role"))
    if role == "qa-manager":
        return "QA Manager"

    user_id = str(decision.get("user_id") or decision.get("userId") or "").strip()
    if not user_id:
        return "Unknown"

    short_id = user_id.split("#EXT#", 1)[0].split("@", 1)[0]
    tokens = [token for token in short_id.replace(".", " ").replace("_", " ").split() if token]
    if not tokens:
        return user_id
    return " ".join(token.capitalize() for token in tokens)
