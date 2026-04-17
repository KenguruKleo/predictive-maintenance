"""
Severity classification for GMP deviation alerts.

Rules (from T-023 spec):
  critical : duration > 30 min  OR  magnitude > 20% of tolerance band
  major    : duration > 2 min   OR  magnitude > 5%  of tolerance band
  minor    : everything else
"""


def classify_severity(body: dict) -> str:
    measured: float = body["measured_value"]
    lower: float = body["lower_limit"]
    upper: float = body["upper_limit"]
    duration_sec: float = body.get("duration_seconds", 0)

    # Magnitude as % of tolerance band width
    tolerance_band = abs(upper - lower) or 1
    deviation = abs(measured - lower) if measured < lower else abs(measured - upper)
    magnitude_pct = deviation / tolerance_band * 100

    duration_min = duration_sec / 60

    if duration_min > 30 or magnitude_pct > 20:
        return "critical"
    elif duration_min > 2 or magnitude_pct > 5:
        return "major"
    else:
        return "minor"
