"""
backend/utils/auth.py — JWT token parsing + role-based access control (T-035)

Strategy:
  - Decode JWT payload (base64) to extract 'roles' claim — no signature
    verification needed here because Azure Functions host validates the
    Entra ID token before the request reaches the function code when
    EasyAuth is enabled.
  - For local dev: if USE_LOCAL_MOCK_AUTH=true, header X-Mock-Role is used
    instead of a token (e.g. X-Mock-Role: Operator).

Usage:
    from utils.auth import get_caller_roles, require_any_role

    roles = get_caller_roles(req)
    require_any_role(roles, ["Operator", "QAManager"])  # raises on 403
"""

import base64
import json
import logging
import os

import azure.functions as func

logger = logging.getLogger(__name__)

USE_LOCAL_MOCK_AUTH = os.getenv("USE_LOCAL_MOCK_AUTH", "false").lower() == "true"


class AuthError(Exception):
    """Raised when authentication/authorisation fails."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


def get_caller_roles(req: func.HttpRequest) -> list[str]:
    """
    Extract role claims from the incoming request.

    Returns a list of role strings from the Entra ID app roles claim,
    e.g. ['Operator', 'QAManager'].  Returns [] if no token is present
    (anonymous / function-key-only call).
    """
    if USE_LOCAL_MOCK_AUTH:
        mock_role = req.headers.get("X-Mock-Role", "")
        return [r.strip() for r in mock_role.split(",") if r.strip()]

    auth_header = req.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return []

    token = auth_header[len("Bearer "):]
    return _decode_roles_from_jwt(token)


def require_any_role(roles: list[str], allowed: list[str]) -> None:
    """
    Raise AuthError(403) if none of the caller's roles are in `allowed`.
    Raise AuthError(401) if roles list is empty (unauthenticated).
    """
    if not roles:
        raise AuthError(401, "Authentication required")
    if not any(r in allowed for r in roles):
        raise AuthError(403, f"Access denied. Required one of: {allowed}")


def get_primary_role(roles: list[str]) -> str:
    """Return the most-privileged role from the list (for filtering logic)."""
    priority = ["ITAdmin", "QAManager", "Auditor", "MaintenanceTech", "Operator"]
    for role in priority:
        if role in roles:
            return role
    return roles[0] if roles else "unknown"


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _decode_roles_from_jwt(token: str) -> list[str]:
    """
    Decode the JWT payload segment and extract the 'roles' claim.
    Does NOT verify signature — trust Azure Functions EasyAuth for that.
    """
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return []

        # Add padding so base64 decodes cleanly
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
        return payload.get("roles", [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to decode JWT roles: %s", exc)
        return []
