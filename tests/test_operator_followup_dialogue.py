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


def test_initial_dialogue_rewrites_stale_comparison_language() -> None:
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

    assert dialogue == "Verify the flowmeter calibration immediately to address the critical deviation."
    assert "remains the same" not in dialogue.lower()


def test_followup_dialogue_rewrites_requirement_question_to_direct_answer() -> None:
    previous_ai_result = {
        "operator_dialogue": "Previous follow-up answer.",
        "recommendation": "Investigate and recalibrate the spray rate control system on GR-204.",
        "root_cause": "The deviation exceeds the established NOR range.",
        "risk_level": "medium",
        "batch_disposition": "hold_pending_review",
    }
    current_result = {
        "operator_dialogue": (
            "I reviewed whether the BPR for Metformin HCl 500mg Tablets mandates stopping the line at a spray rate "
            "of 138 g/min for 35 minutes. The recommendation remains unchanged as the deviation exceeds the NOR limits."
        ),
        "recommendation": "Investigate and recalibrate the spray rate control system on GR-204.",
        "root_cause": "The deviation exceeds the established NOR range.",
        "risk_level": "medium",
        "batch_disposition": "hold_pending_review",
        "evidence_citations": [
            {
                "source": "BPR-MET-500-v3.2",
                "section": "Product NOR",
                "text_excerpt": "spray_rate_g_min: [75,105]",
            }
        ],
    }
    operator_questions = [
        {
            "round": 2,
            "asked_by": "ivan.petrenko",
            "question": (
                "Check if the BPR for Metformin HCl 500mg has a direct requirement to stop the line "
                "at a spray rate of 138 g/min for 35 minutes."
            ),
        }
    ]

    dialogue = _normalize_operator_dialogue(
        current_result,
        more_info_round=2,
        previous_ai_result=previous_ai_result,
        operator_questions=operator_questions,
    )

    assert "did not find a retrieved bpr or sop instruction" in dialogue.lower()
    assert "directly requires stopping the line" in dialogue.lower()
    assert "75,105" in dialogue
    assert "i kept the recommendation and batch disposition unchanged because" in dialogue.lower()
    assert "the batch remains on hold pending review" in dialogue.lower()
    assert "recommended next action" in dialogue.lower()
    assert dialogue != current_result["operator_dialogue"]


def test_followup_dialogue_with_changed_fields_stays_complete_under_limit() -> None:
    previous_ai_result = {
        "operator_dialogue": "Previous follow-up answer.",
        "recommendation": "Immediately verify the calibration of the flowmeter and inspect the tubing and nozzle for wear or blockages.",
        "root_cause": "The deviation in spray_rate_g_min on equipment GR-204 was likely caused by a calibration drift in the flowmeter.",
        "risk_level": "high",
        "batch_disposition": "hold_pending_review",
    }
    current_result = {
        "operator_dialogue": (
            "I reviewed the BPR for Metformin HCl 500mg and found no direct requirement to stop the line at a spray rate "
            "of 138 g/min for 35 minutes. The recommendation and batch disposition remain unchanged as the deviation "
            "still poses a high risk to product quality."
        ),
        "recommendation": "Verify the calibration of the flowmeter and inspect the tubing and nozzle for wear or blockages.",
        "root_cause": (
            "The deviation in spray_rate_g_min on equipment GR-204 was likely caused by a calibration drift in the "
            "flowmeter, as the equipment's last calibration was on 2026-02-01 and is due on 2026-08-01."
        ),
        "risk_level": "high",
        "batch_disposition": "conditional_release_pending_testing",
        "evidence_citations": [
            {
                "source": "BPR for Metformin HCl 500mg Granulation Process Parameters",
                "section": "Spray Rate",
                "text_excerpt": "Spray rate must be maintained within 70-110 g/min to ensure uniform granulation.",
            }
        ],
    }
    operator_questions = [
        {
            "round": 1,
            "asked_by": "ivan.petrenko",
            "question": (
                "Check if the BPR for Metformin HCl 500mg has a direct requirement to stop the line at a spray rate "
                "of 138 g/min for 35 minutes. If there is no direct requirement, adjust the recommendation and batch "
                "disposition using the actual BPR and SOP limits."
            ),
        }
    ]

    dialogue = _normalize_operator_dialogue(
        current_result,
        more_info_round=1,
        previous_ai_result=previous_ai_result,
        operator_questions=operator_questions,
    )

    assert len(dialogue) <= 800
    assert not dialogue.endswith("Update")
    assert "directly requires stopping the line" in dialogue.lower()
    assert "the batch is now under conditional release pending testing" in dialogue.lower()
    assert "recommended next action" in dialogue.lower()
    assert dialogue != current_result["operator_dialogue"]