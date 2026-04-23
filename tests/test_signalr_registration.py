"""Unit tests for SignalR connection registration."""

import json
import sys
import urllib.request
from pathlib import Path

import azure.functions as func

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import triggers.http_signalr as http_signalr  # noqa: E402
from shared.signalr_client import add_connection_to_group_sync  # noqa: E402


def test_register_signalr_connection_adds_role_groups(monkeypatch) -> None:
    added: list[tuple[str, str]] = []

    monkeypatch.setattr(http_signalr, "get_caller_roles", lambda req: ["Operator", "QAManager"])
    monkeypatch.setattr(http_signalr, "require_any_role", lambda roles, allowed: None)
    monkeypatch.setattr(
        http_signalr,
        "add_connection_to_group_sync",
        lambda connection_id, group_name: added.append((connection_id, group_name)) or True,
    )

    req = func.HttpRequest(
        method="POST",
        url="http://localhost/api/signalr/register",
        body=json.dumps({"connection_id": "abc123"}).encode(),
        headers={"Content-Type": "application/json"},
    )

    response = http_signalr.register_signalr_connection(req)
    payload = json.loads(response.get_body())

    assert response.status_code == 200
    assert payload["registered_groups"] == ["role:operator", "role:qa-manager"]
    assert payload["failed_groups"] == []
    assert added == [
        ("abc123", "role:operator"),
        ("abc123", "role:qa-manager"),
    ]


def test_register_signalr_connection_rejects_missing_connection_id(monkeypatch) -> None:
    monkeypatch.setattr(http_signalr, "get_caller_roles", lambda req: ["Operator"])
    monkeypatch.setattr(http_signalr, "require_any_role", lambda roles, allowed: None)

    req = func.HttpRequest(
        method="POST",
        url="http://localhost/api/signalr/register",
        body=json.dumps({}).encode(),
        headers={"Content-Type": "application/json"},
    )

    response = http_signalr.register_signalr_connection(req)
    payload = json.loads(response.get_body())

    assert response.status_code == 400
    assert payload["error"] == "connection_id is required"


def test_add_connection_to_group_sync_sends_json_media_type(monkeypatch) -> None:
    monkeypatch.setenv(
        "AzureSignalRConnectionString",
        "Endpoint=https://example.service.signalr.net;AccessKey=test-key;Version=1.0;",
    )

    captured: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(req: urllib.request.Request, timeout: int = 10):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["data"] = req.data
        captured["content_type"] = req.headers.get("Content-type")
        captured["authorization"] = req.headers.get("Authorization")
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    success = add_connection_to_group_sync("conn-123", "role:operator")

    assert success is True
    assert captured["method"] == "PUT"
    assert captured["data"] == b"{}"
    assert captured["content_type"] == "application/json"
    assert captured["authorization"].startswith("Bearer ")
    assert captured["url"] == (
        "https://example.service.signalr.net/api/v1/hubs/deviationHub/"
        "groups/role%3Aoperator/connections/conn-123"
    )