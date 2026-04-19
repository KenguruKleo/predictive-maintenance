from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from activities.run_foundry_agents import _normalize_operator_dialogue


def test_followup_dialogue_is_rewritten_when_it_just_repeats_recommendation() -> None:
    previous_ai_result = {
        "operator_dialogue": (
            "We have detected a high deviation in the spray rate on equipment GR-204, "
            "measuring 138 g/min, which exceeds the acceptable range. Immediate corrective "
            "actions are required."
        ),
        "recommendation": "Immediate investigation and corrective actions are required to address the spray rate deviation on equipment GR-204.",
        "root_cause": "The deviation exceeds the established limit.",
        "risk_level": "high",
        "batch_disposition": "hold_pending_review",
    }
    current_result = {
        "operator_dialogue": (
            "We have detected a high deviation in the spray rate on equipment GR-204, "
            "measuring 138 g/min, which exceeds the acceptable range. Immediate corrective "
            "actions are required."
        ),
        "recommendation": "Immediate investigation and corrective actions are required to address the spray rate deviation on equipment GR-204.",
        "root_cause": "The deviation exceeds the established limit.",
        "risk_level": "high",
        "batch_disposition": "hold_pending_review",
    }
    operator_questions = [
        {
            "round": 1,
            "asked_by": "ivan.petrenko",
            "question": "Check if the cause could be in the sensor or flowmeter calibration, rather than the tubing.",
        }
    ]

    dialogue = _normalize_operator_dialogue(
        current_result,
        more_info_round=1,
        previous_ai_result=previous_ai_result,
        operator_questions=operator_questions,
    )

    assert "sensor or flowmeter calibration" in dialogue
    assert "did not find enough new evidence to change" in dialogue.lower()
    assert dialogue != current_result["operator_dialogue"]


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