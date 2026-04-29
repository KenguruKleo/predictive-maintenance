import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from orchestrators.incident_orchestrator import (  # noqa: E402
    _build_more_info_limit_notice,
    _can_run_more_info,
    _get_followup_review_role,
)


def test_operator_more_info_stays_operator_owned() -> None:
    assert _get_followup_review_role(
        "operator",
        {"action": "more_info", "role": "operator", "user_id": "ivan.petrenko"},
    ) == "operator"


def test_qamanager_more_info_stays_qamanager_owned() -> None:
    assert _get_followup_review_role(
        "qa-manager",
        {"action": "more_info", "role": "qa-manager", "user_id": "qa.manager"},
    ) == "qa-manager"


def test_qamanager_decision_promotes_followup_to_qamanager() -> None:
    assert _get_followup_review_role(
        "operator",
        {"action": "more_info", "role": "qa-manager", "user_id": "qa.manager"},
    ) == "qa-manager"


def test_more_info_capacity_stops_at_configured_limit() -> None:
    assert _can_run_more_info("more_info", 2, max_rounds=3) is True
    assert _can_run_more_info("more_info", 3, max_rounds=3) is False
    assert _can_run_more_info("approved", 0, max_rounds=3) is False


def test_more_info_limit_notice_preserves_current_ai_result() -> None:
    notice = _build_more_info_limit_notice(
        {
            "recommendation": "Inspect and recalibrate GR-204.",
            "risk_level": "critical",
            "operator_dialogue": "Previous answer.",
        },
        max_rounds=3,
    )

    assert notice["recommendation"] == "Inspect and recalibrate GR-204."
    assert notice["risk_level"] == "critical"
    assert "More Info limit has been reached (3 rounds)" in notice["operator_dialogue"]
    assert "No additional AI analysis was run" in notice["analysis"]