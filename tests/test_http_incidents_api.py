"""Focused endpoint tests for incident list/detail access behavior."""

import json
import sys
from pathlib import Path

import azure.functions as func

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import triggers.http_incidents as http_incidents  # noqa: E402


class FakeContainer:
    def __init__(self, responses: list[list[dict] | list[int]]) -> None:
        self._responses = responses
        self.calls: list[dict] = []

    def query_items(self, query, parameters, enable_cross_partition_query=True):
        self.calls.append(
            {
                "query": query,
                "parameters": parameters,
                "enable_cross_partition_query": enable_cross_partition_query,
            }
        )
        return self._responses[len(self.calls) - 1]


def test_list_incidents_returns_slim_payload_and_total(monkeypatch) -> None:
    container = FakeContainer(
        responses=[
            [
                {
                    "id": "INC-2026-0101",
                    "incident_number": "INC-2026-0101",
                    "equipment_id": "GR-204",
                    "batch_id": "B-42",
                    "title": "Granulator excursion",
                    "severity": "high",
                    "status": "pending_approval",
                    "reported_at": "2026-04-28T10:00:00Z",
                    "reported_by": "sensor",
                    "workflow_state": {
                        "assigned_to": "ivan.petrenko",
                        "current_step": "awaiting_human",
                    },
                    "ai_analysis": {
                        "risk_level": "HIGH",
                        "confidence": 0.82,
                        "agent_recommendation": "APPROVE",
                        "root_cause": "Valve drift",
                    },
                    "operatorAgreesWithAgent": True,
                    "lastDecision": {"action": "approved"},
                }
            ],
            [1],
        ]
    )

    monkeypatch.setattr(http_incidents, "get_caller_roles", lambda req: ["Operator"])
    monkeypatch.setattr(http_incidents, "require_any_role", lambda roles, allowed: None)
    monkeypatch.setattr(http_incidents, "get_caller_id", lambda req: "ivan.petrenko")
    monkeypatch.setattr(http_incidents, "get_container", lambda name: container)

    req = func.HttpRequest(
        method="GET",
        url="http://localhost/api/incidents?page=1&page_size=20&status=pending_approval&status=escalated",
        body=b"",
        params={"page": "1", "page_size": "20"},
    )

    response = http_incidents.list_incidents(req)
    payload = json.loads(response.get_body())

    assert response.status_code == 200
    assert payload["total"] == 1
    assert payload["page"] == 1
    assert payload["page_size"] == 20
    assert payload["items"] == [
        {
            "id": "INC-2026-0101",
            "incident_number": "INC-2026-0101",
            "equipment_id": "GR-204",
            "batch_id": "B-42",
            "title": "Granulator excursion",
            "severity": "high",
            "status": "pending_approval",
            "reported_at": "2026-04-28T10:00:00Z",
            "created_at": "2026-04-28T10:00:00Z",
            "reported_by": "sensor",
            "risk_level": "HIGH",
            "confidence": 0.82,
            "assigned_to": "ivan.petrenko",
            "current_step": "awaiting_human",
            "ai_analysis": {"agent_recommendation": "APPROVE"},
            "operatorAgreesWithAgent": True,
            "lastDecision": {"action": "approved"},
        }
    ]
    assert len(container.calls) == 2
    assert any(param == {"name": "@caller_id", "value": "ivan.petrenko"} for param in container.calls[0]["parameters"])


def test_list_incidents_rejects_invalid_pagination(monkeypatch) -> None:
    monkeypatch.setattr(http_incidents, "get_caller_roles", lambda req: ["Operator"])
    monkeypatch.setattr(http_incidents, "require_any_role", lambda roles, allowed: None)

    req = func.HttpRequest(
        method="GET",
        url="http://localhost/api/incidents?page=bad",
        body=b"",
        params={"page": "bad"},
    )

    response = http_incidents.list_incidents(req)
    payload = json.loads(response.get_body())

    assert response.status_code == 400
    assert payload["error"] == "Invalid pagination parameters"


def test_get_incident_forbids_operator_access_to_other_assignee(monkeypatch) -> None:
    container = FakeContainer(
        responses=[
            [
                {
                    "id": "INC-2026-0102",
                    "workflow_state": {"assigned_to": "other.operator"},
                }
            ]
        ]
    )

    monkeypatch.setattr(http_incidents, "get_caller_roles", lambda req: ["Operator"])
    monkeypatch.setattr(http_incidents, "require_any_role", lambda roles, allowed: None)
    monkeypatch.setattr(http_incidents, "get_caller_id", lambda req: "ivan.petrenko")
    monkeypatch.setattr(http_incidents, "get_container", lambda name: container)

    req = func.HttpRequest(
        method="GET",
        url="http://localhost/api/incidents/INC-2026-0102",
        body=b"",
        route_params={"incident_id": "INC-2026-0102"},
    )

    response = http_incidents.get_incident(req)
    payload = json.loads(response.get_body())

    assert response.status_code == 403
    assert payload["error"] == "Access denied to this incident"


def test_get_incident_returns_full_document_for_qamanager(monkeypatch) -> None:
    incident = {
        "id": "INC-2026-0103",
        "status": "escalated",
        "workflow_state": {"assigned_to": "qa.manager"},
        "ai_analysis": {"confidence": 0.44},
    }
    container = FakeContainer(responses=[[incident]])

    monkeypatch.setattr(http_incidents, "get_caller_roles", lambda req: ["QAManager"])
    monkeypatch.setattr(http_incidents, "require_any_role", lambda roles, allowed: None)
    monkeypatch.setattr(http_incidents, "get_container", lambda name: container)

    req = func.HttpRequest(
        method="GET",
        url="http://localhost/api/incidents/INC-2026-0103",
        body=b"",
        route_params={"incident_id": "INC-2026-0103"},
    )

    response = http_incidents.get_incident(req)
    payload = json.loads(response.get_body())

    assert response.status_code == 200
    assert payload == incident


def test_get_incident_returns_404_when_missing(monkeypatch) -> None:
    container = FakeContainer(responses=[[]])

    monkeypatch.setattr(http_incidents, "get_caller_roles", lambda req: ["Auditor"])
    monkeypatch.setattr(http_incidents, "require_any_role", lambda roles, allowed: None)
    monkeypatch.setattr(http_incidents, "get_container", lambda name: container)

    req = func.HttpRequest(
        method="GET",
        url="http://localhost/api/incidents/INC-2026-4040",
        body=b"",
        route_params={"incident_id": "INC-2026-4040"},
    )

    response = http_incidents.get_incident(req)
    payload = json.loads(response.get_body())

    assert response.status_code == 404
    assert payload["error"] == "Incident 'INC-2026-4040' not found"