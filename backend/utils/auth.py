"""
backend/utils/auth.py — JWT token parsing + role-based access control (T-035)

Strategy:
  - Production: verify JWT signature using Entra ID JWKS endpoint, then
    extract 'roles' claim from the validated payload.
  - Local dev: if USE_LOCAL_MOCK_AUTH=true, header X-Mock-Role is used
    instead of a token (e.g. X-Mock-Role: Operator).

JWKS keys are cached in-process (invalidated after JWKS_CACHE_TTL_SECONDS).

Usage:
    from utils.auth import get_caller_roles, require_any_role

    roles = get_caller_roles(req)
    require_any_role(roles, ["Operator", "QAManager"])  # raises AuthError on 403
"""

import json
import logging
import os
import time
import urllib.request

import azure.functions as func
import jwt
from jwt.algorithms import RSAAlgorithm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_TENANT_ID = os.getenv(
    "ENTRA_TENANT_ID",
    "baf5b083-4c53-493a-8af7-a6ae9812014c",
)
_API_CLIENT_ID = os.getenv(
    "ENTRA_API_CLIENT_ID",
    "38843d08-f211-4445-bcef-a07d383f2ee6",
)
_API_AUDIENCE = os.getenv(
    "ENTRA_API_AUDIENCE",
    f"api://{_API_CLIENT_ID}",
)
_JWKS_URI = (
    f"https://login.microsoftonline.com/{_TENANT_ID}/discovery/v2.0/keys"
)
_VALID_ISSUERS = [
    f"https://sts.windows.net/{_TENANT_ID}/",
    f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0",
]

JWKS_CACHE_TTL_SECONDS = 3600  # re-fetch JWKS once per hour

USE_LOCAL_MOCK_AUTH = os.getenv("USE_LOCAL_MOCK_AUTH", "false").lower() == "true"

# ---------------------------------------------------------------------------
# JWKS in-process cache (survives across warm invocations)
# ---------------------------------------------------------------------------
_jwks_cache: dict = {}
_jwks_fetched_at: float = -(JWKS_CACHE_TTL_SECONDS + 1)


def _get_jwks() -> dict:
    """Return JWKS keys, refreshing from Entra ID if cache is stale."""
    global _jwks_cache, _jwks_fetched_at
    if time.monotonic() - _jwks_fetched_at > JWKS_CACHE_TTL_SECONDS:
        try:
            with urllib.request.urlopen(_JWKS_URI, timeout=5) as resp:
                _jwks_cache = json.loads(resp.read())
                _jwks_fetched_at = time.monotonic()
        except Exception as exc:
            logger.warning("Failed to refresh JWKS: %s", exc)
            # Return stale cache if available; will retry on next call
    return _jwks_cache


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

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
    e.g. ['Operator', 'QAManager'].  Returns [] if no valid token is present.

    Raises AuthError(401) if a Bearer token is provided but fails validation.
    """
    if USE_LOCAL_MOCK_AUTH:
        mock_role = req.headers.get("X-Mock-Role", "")
        return [r.strip() for r in mock_role.split(",") if r.strip()]

    auth_header = req.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return []

    token = auth_header[len("Bearer "):]
    return _verify_and_decode_roles(token)


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
# Internal — JWT signature verification
# ---------------------------------------------------------------------------

def _verify_and_decode_roles(token: str) -> list[str]:
    """
    Fully verify the JWT: signature (RS256 via JWKS), audience, issuer, expiry.
    Returns the 'roles' list from the payload on success.
    Raises AuthError(401) on any validation failure.
    """
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.DecodeError:
        raise AuthError(401, "Malformed token")

    kid = unverified_header.get("kid")
    alg = unverified_header.get("alg", "")

    if alg not in ("RS256",):
        raise AuthError(401, f"Unsupported token algorithm: {alg}")

    # Find the matching public key in JWKS
    public_key = _resolve_public_key(kid)
    if public_key is None:
        # Key not found — JWKS may be stale; force refresh once
        global _jwks_fetched_at
        _jwks_fetched_at = 0.0
        public_key = _resolve_public_key(kid)

    if public_key is None:
        logger.warning("JWT kid=%s not found in JWKS after refresh", kid)
        raise AuthError(401, "Unknown token signing key")

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=_API_AUDIENCE,
            issuer=_VALID_ISSUERS,
            options={"verify_iss": True, "require": ["exp", "aud"]},
        )
        return payload.get("roles", [])

    except jwt.ExpiredSignatureError:
        raise AuthError(401, "Token expired")
    except jwt.InvalidAudienceError:
        raise AuthError(401, "Invalid token audience")
    except jwt.InvalidIssuerError:
        raise AuthError(401, "Invalid token issuer")
    except jwt.InvalidTokenError as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise AuthError(401, "Invalid token")


def _resolve_public_key(kid: str | None):
    """Look up the RSA public key for the given key ID in JWKS."""
    jwks = _get_jwks()
    for key_data in jwks.get("keys", []):
        if kid is None or key_data.get("kid") == kid:
            try:
                return RSAAlgorithm.from_jwk(json.dumps(key_data))
            except Exception as exc:
                logger.warning("Failed to parse JWK: %s", exc)
    return None

