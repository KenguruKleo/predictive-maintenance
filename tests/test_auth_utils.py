"""Focused tests for backend auth and caller identity helpers."""

import sys
from pathlib import Path

import azure.functions as func
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import utils.auth as auth_utils  # noqa: E402


def test_get_caller_roles_reads_mock_headers_in_local_mode(monkeypatch) -> None:
    monkeypatch.setattr(auth_utils, "USE_LOCAL_MOCK_AUTH", True)
    req = func.HttpRequest(
        method="GET",
        url="http://localhost/api/test",
        body=b"",
        headers={"X-Mock-Role": "Operator, QAManager"},
    )

    assert auth_utils.get_caller_roles(req) == ["Operator", "QAManager"]


def test_get_caller_id_prefers_mock_user_id_in_local_mode(monkeypatch) -> None:
    monkeypatch.setattr(auth_utils, "USE_LOCAL_MOCK_AUTH", True)
    req = func.HttpRequest(
        method="GET",
        url="http://localhost/api/test",
        body=b"",
        headers={
            "X-Mock-Role": "Operator",
            "X-Mock-User-Id": "operator.user",
            "X-Mock-User": "fallback.user",
        },
    )

    assert auth_utils.get_caller_id(req) == "operator.user"


def test_get_caller_id_falls_back_to_demo_user_when_mock_role_exists(monkeypatch) -> None:
    monkeypatch.setattr(auth_utils, "USE_LOCAL_MOCK_AUTH", True)
    req = func.HttpRequest(
        method="GET",
        url="http://localhost/api/test",
        body=b"",
        headers={"X-Mock-Role": "Operator"},
    )

    assert auth_utils.get_caller_id(req) == "ivan.petrenko"


def test_get_caller_roles_rejects_valid_token_without_app_roles(monkeypatch) -> None:
    monkeypatch.setattr(auth_utils, "USE_LOCAL_MOCK_AUTH", False)
    monkeypatch.setattr(auth_utils, "_verify_and_decode_payload", lambda token: {"sub": "user-1"})
    req = func.HttpRequest(
        method="GET",
        url="http://localhost/api/test",
        body=b"",
        headers={"Authorization": "Bearer valid-token-without-roles"},
    )

    with pytest.raises(auth_utils.AuthError) as forbidden:
        auth_utils.get_caller_roles(req)

    assert forbidden.value.status_code == 403
    assert forbidden.value.message == "No Sentinel app role assigned"


def test_verify_payload_accepts_api_client_id_audience(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        auth_utils.jwt,
        "get_unverified_header",
        lambda token: {"kid": "test-key", "alg": "RS256"},
    )
    monkeypatch.setattr(auth_utils, "_resolve_public_key", lambda kid: "public-key")

    def fake_decode(token, key, *, algorithms, audience, issuer, options):
        captured["audience"] = audience
        return {"aud": auth_utils._API_CLIENT_ID, "roles": ["Operator"]}

    monkeypatch.setattr(auth_utils.jwt, "decode", fake_decode)

    payload = auth_utils._verify_and_decode_payload("token-with-guid-audience")

    assert payload["aud"] == auth_utils._API_CLIENT_ID
    assert auth_utils._API_CLIENT_ID in captured["audience"]
    assert f"api://{auth_utils._API_CLIENT_ID}" in captured["audience"]


def test_require_any_role_raises_for_unauthenticated_and_disallowed_roles() -> None:
    with pytest.raises(auth_utils.AuthError) as unauthenticated:
        auth_utils.require_any_role([], ["Operator"])

    with pytest.raises(auth_utils.AuthError) as forbidden:
        auth_utils.require_any_role(["Auditor"], ["Operator", "QAManager"])

    assert unauthenticated.value.status_code == 401
    assert unauthenticated.value.message == "Authentication required"
    assert forbidden.value.status_code == 403
    assert "Required one of" in forbidden.value.message


def test_get_primary_role_uses_privilege_priority_order() -> None:
    assert auth_utils.get_primary_role(["Operator", "ITAdmin"]) == "ITAdmin"
    assert auth_utils.get_primary_role(["MaintenanceTech", "Operator"]) == "MaintenanceTech"
    assert auth_utils.get_primary_role([]) == "unknown"