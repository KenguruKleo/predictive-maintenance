from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from activities.run_foundry_agents import _normalize_operator_dialogue


def test_followup_dialogue_keeps_explicit_model_answer() -> None:
    explicit = "The recommendation remains unchanged: investigate and calibrate the spray rate equipment to address the deviation."

    dialogue = _normalize_operator_dialogue(
        {
            "operator_dialogue": explicit,
            "recommendation": "Approve corrective actions and inspect the spray-rate control path on GR-204.",
            "root_cause": "The sustained spray-rate deviation may come from calibration drift or equipment wear.",
            "risk_level": "high",
            "batch_disposition": "hold_pending_review",
        },
        more_info_round=2,
        previous_ai_result={
            "operator_dialogue": "Previous answer.",
            "recommendation": "Approve corrective actions and inspect the spray-rate control path on GR-204.",
        },
        operator_questions=[
            {
                "round": 2,
                "question": "Compare the current case with historical incidents for GR-204.",
                "asked_by": "operator",
            }
        ],
    )

    assert dialogue == explicit


def test_followup_dialogue_keeps_good_explicit_answer() -> None:
    explicit = (
        "I reviewed your question about sensor and flowmeter calibration versus tubing. "
        "I did not find enough new evidence to change the recommendation, so it remains focused "
        "on immediate investigation while the root-cause hypothesis stays unchanged."
    )

    dialogue = _normalize_operator_dialogue(
        {
            "operator_dialogue": explicit,
            "recommendation": "Immediate investigation and corrective actions are required.",
            "root_cause": "The deviation exceeds the established limit.",
            "risk_level": "high",
            "batch_disposition": "hold_pending_review",
        },
        more_info_round=1,
        previous_ai_result={
            "operator_dialogue": "Previous answer.",
            "recommendation": "Immediate investigation and corrective actions are required.",
            "root_cause": "The deviation exceeds the established limit.",
            "risk_level": "high",
            "batch_disposition": "hold_pending_review",
        },
        operator_questions=[{"round": 1, "question": "Check sensor calibration.", "asked_by": "operator"}],
    )

    assert dialogue == explicit


def test_initial_dialogue_keeps_explicit_model_text() -> None:
    dialogue = _normalize_operator_dialogue(
        {
            "operator_dialogue": (
                "We reviewed the incident regarding the spray rate deviation. The recommendation remains the same: "
                "verify the flowmeter calibration immediately to address the critical deviation."
            ),
            "recommendation": "Verify the flowmeter calibration immediately to address the critical deviation.",
            "analysis": "The spray rate deviation is critical and requires immediate verification of the flowmeter.",
            "root_cause": "Potential flowmeter calibration drift.",
            "risk_level": "high",
            "batch_disposition": "hold_pending_review",
        },
        more_info_round=0,
        previous_ai_result={},
        operator_questions=[],
    )

    assert "remains the same" in dialogue.lower()


def test_initial_dialogue_uses_recommendation_fallback_when_missing() -> None:
    dialogue = _normalize_operator_dialogue(
        {
            "operator_dialogue": "",
            "recommendation": "Verify the flowmeter calibration immediately to address the critical deviation.",
            "analysis": "The spray rate deviation is critical and requires immediate verification of the flowmeter.",
        },
        more_info_round=0,
        previous_ai_result={},
        operator_questions=[],
    )

    assert dialogue == "Verify the flowmeter calibration immediately to address the critical deviation."


def test_followup_dialogue_uses_recommendation_fallback_when_missing() -> None:
    dialogue = _normalize_operator_dialogue(
        {
            "operator_dialogue": "",
            "recommendation": "Approve corrective actions and inspect the spray-rate control path on GR-204.",
            "analysis": "Historical evidence was reviewed but the model did not return a separate operator summary.",
        },
        more_info_round=2,
        previous_ai_result={"operator_dialogue": "Previous answer."},
        operator_questions=[{"round": 2, "question": "Compare with historical incidents.", "asked_by": "operator"}],
    )

    assert dialogue == "Approve corrective actions and inspect the spray-rate control path on GR-204."