import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from orchestrators.incident_orchestrator import _get_followup_review_role  # noqa: E402


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