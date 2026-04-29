"""
Alert payload validation + prompt injection sanitization.

validate_alert_payload() raises ValueError with a descriptive message on failure.
sanitize_string_fields() strips prompt injection patterns from user-controlled strings.
"""

import re
from typing import Any

# ---------------------------------------------------------------------------
# Required / optional fields
# ---------------------------------------------------------------------------

REQUIRED_FIELDS: list[tuple[str, type]] = [
    ("equipment_id", str),
    ("deviation_type", str),
    ("parameter", str),
    ("measured_value", (int, float)),
    ("lower_limit", (int, float)),
    ("upper_limit", (int, float)),
    ("unit", str),
]

ALLOWED_DEVIATION_TYPES = {
    "process_parameter_excursion",
    "environmental_excursion",
    "equipment_failure",
    "material_defect",
    "documentation_error",
    "other",
}

# Max length for string fields — prevents oversized payloads
MAX_STRING_LENGTH = 500
_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

# ---------------------------------------------------------------------------
# Prompt injection patterns to strip / block
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(?:(?:all|previous|above)\s+){0,3}instructions?"
    r"|you\s+are\s+now|new\s+system\s+prompt"
    r"|disregard\s+(all|previous)"
    r"|act\s+as\s+(?:a\s+)?(?:DAN|jailbreak)"
    r"|<\s*(?:system|user|assistant)\s*>)",
    re.IGNORECASE,
)

_INJECTION_COMMAND_TOKENS = {
    "ignore", "forget", "disregard", "override", "bypass", "disable", "reveal", "leak",
}
_INJECTION_TARGET_TOKENS = {
    "instruction", "instructions", "system", "prompt", "guardrail", "guardrails", "policy",
    "policies", "rule", "rules", "limitation", "limitations",
}
_ROLE_SWITCH_TOKENS = {"switch", "change", "become", "act", "pretend"}
_UNSAFE_ROLE_TOKENS = {"unrestricted", "admin", "root", "developer", "dan"}


def has_prompt_injection_signals(value: str) -> bool:
    """Detect likely prompt-injection intent using rule-based signals, with regex as fallback."""
    normalized = normalize_free_text(value).lower()
    if not normalized:
        return False

    # Keep regex as a fallback for known direct signatures.
    if _INJECTION_PATTERNS.search(normalized):
        return True

    tokens = set(re.findall(r"[a-z0-9_]+", normalized))
    has_command = bool(tokens & _INJECTION_COMMAND_TOKENS)
    has_target = bool(tokens & _INJECTION_TARGET_TOKENS)
    if has_command and has_target:
        return True

    # Role/persona hijack without explicit regex pattern.
    if "role" in tokens and bool(tokens & _ROLE_SWITCH_TOKENS) and bool(tokens & _UNSAFE_ROLE_TOKENS):
        return True

    # Common obfuscation attempts.
    if ("base64" in tokens or "encoded" in tokens) and ("decode" in tokens or "decrypt" in tokens):
        if has_target or "prompt" in tokens:
            return True

    return False


def validate_alert_payload(body: Any) -> None:
    """
    Validate required fields, types, and business rules.
    Raises ValueError with a human-readable message on any failure.
    """
    if not isinstance(body, dict):
        raise ValueError("Request body must be a JSON object")

    # Required fields
    for field, expected_type in REQUIRED_FIELDS:
        if field not in body:
            raise ValueError(f"Missing required field: '{field}'")
        if not isinstance(body[field], expected_type):
            raise ValueError(
                f"Field '{field}' must be {expected_type.__name__ if isinstance(expected_type, type) else 'a number'}"
            )

    # String length guard
    for field, expected_type in REQUIRED_FIELDS:
        if expected_type is str and len(body[field]) > MAX_STRING_LENGTH:
            raise ValueError(f"Field '{field}' exceeds maximum length of {MAX_STRING_LENGTH}")

    # deviation_type allow-list
    if body["deviation_type"] not in ALLOWED_DEVIATION_TYPES:
        raise ValueError(
            f"Invalid deviation_type '{body['deviation_type']}'. "
            f"Allowed: {sorted(ALLOWED_DEVIATION_TYPES)}"
        )

    # Numeric range: lower_limit < upper_limit
    if body["lower_limit"] >= body["upper_limit"]:
        raise ValueError("'lower_limit' must be less than 'upper_limit'")

    # Optional string fields length
    for optional_field in ("batch_id", "alert_id", "detected_by"):
        val = body.get(optional_field)
        if val is not None:
            if not isinstance(val, str):
                raise ValueError(f"Optional field '{optional_field}' must be a string")
            if len(val) > MAX_STRING_LENGTH:
                raise ValueError(f"Optional field '{optional_field}' exceeds maximum length")


def sanitize_string_fields(body: dict) -> None:
    """
    Scan all string-valued fields in the payload for prompt injection patterns.
    Raises ValueError if a suspicious pattern is detected.
    This is an in-place check — does NOT modify the payload.
    """
    string_fields = [
        "equipment_id", "deviation_type", "parameter", "unit",
        "detected_by", "batch_id", "alert_id", "reason", "question",
    ]
    for field in string_fields:
        value = body.get(field)
        if not isinstance(value, str):
            continue
        normalized = normalize_free_text(value)
        if len(normalized) > MAX_STRING_LENGTH:
            raise ValueError(
                f"Field '{field}' exceeds maximum length of {MAX_STRING_LENGTH}"
            )
        if _CONTROL_CHAR_PATTERN.search(value):
            raise ValueError(
                f"Potentially unsafe control characters detected in field '{field}'. Request rejected."
            )
        if has_prompt_injection_signals(normalized):
            raise ValueError(
                f"Potentially unsafe content detected in field '{field}'. Request rejected."
            )


def normalize_free_text(value: Any) -> str:
    """Normalize user-provided free-text fields before persistence and search use."""
    if value is None:
        return ""
    text = str(value)
    text = _CONTROL_CHAR_PATTERN.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
