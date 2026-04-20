import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from activities.notify_operator import _resolve_operator_assignee  # noqa: E402
from triggers.http_incidents import _build_count_query, _build_query, _operator_visibility_clause  # noqa: E402


def test_operator_visibility_clause_includes_unassigned_items() -> None:
    clause = _operator_visibility_clause()

    assert "NOT IS_DEFINED(c.workflow_state.assigned_to)" in clause
    assert "c.workflow_state.assigned_to = ''" in clause
    assert "c.workflow_state.assigned_to = @caller_id" in clause


def test_operator_incident_query_includes_unassigned_items() -> None:
    query, params = _build_query(["Operator"], "user@example.com", [], "", "", "", 1, 20)

    assert _operator_visibility_clause() in query
    assert params == [{"name": "@caller_id", "value": "user@example.com"}]


def test_operator_incident_count_query_includes_unassigned_items() -> None:
    query, params = _build_count_query(["Operator"], "user@example.com", [], "")

    assert _operator_visibility_clause() in query
    assert params == [{"name": "@caller_id", "value": "user@example.com"}]


def test_notify_operator_has_no_demo_default_assignee() -> None:
    assert _resolve_operator_assignee({}) == ""


def test_notify_operator_uses_explicit_assignee_when_present() -> None:
    assert _resolve_operator_assignee({"assigned_to": "operator.user@example.com"}) == "operator.user@example.com"