"""Focused tests for the T-029 decision endpoint and persistence helpers."""

import asyncio
import json
import sys
from pathlib import Path

import azure.durable_functions as df

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import triggers.http_decision as http_decision  # noqa: E402


def _get_http_decision_user_function():
    outer = http_decision.http_decision._function._func
    freevars = getattr(outer.__code__, "co_freevars", ())
    closure = getattr(outer, "__closure__", ()) or ()
    closure_map = {
        name: cell.cell_contents
        for name, cell in zip(freevars, closure)
    }
    return closure_map.get("user_code", outer)


HTTP_DECISION = _get_http_decision_user_function()


class FakeRequest:
    def __init__(self, body: dict | None = None, *, headers: dict | None = None, route_params: dict | None = None):
        self._body = body if body is not None else {}
        self.headers = headers or {}
        self.route_params = route_params or {}

    def get_json(self):
        return self._body


class FakeStatus:
    def __init__(self, runtime_status):
        self.runtime_status = runtime_status


class FakeDurableClient:
    def __init__(self, status):
        self.status = status
        self.raised_events: list[tuple[str, str, dict]] = []

    async def get_status(self, instance_id: str):
        self.last_status_instance_id = instance_id
        return self.status

    async def raise_event(self, instance_id: str, event_name: str, payload: dict):
        self.raised_events.append((instance_id, event_name, payload))


def test_http_decision_requires_authentication(monkeypatch) -> None:
    monkeypatch.setattr(http_decision, "get_caller_roles", lambda req: [])

    req = FakeRequest(
        {"action": "approved", "user_id": "ivan.petrenko"},
        route_params={"incident_id": "INC-2026-0029"},
    )

    response = asyncio.run(HTTP_DECISION(req, FakeDurableClient(None)))

    assert response.status_code == 401
    assert json.loads(response.get_body())["error"] == "Authentication required"


def test_http_decision_forbids_unapproved_role(monkeypatch) -> None:
    monkeypatch.setattr(http_decision, "get_caller_roles", lambda req: ["Auditor"])

    req = FakeRequest(
        {"action": "approved", "user_id": "ivan.petrenko"},
        route_params={"incident_id": "INC-2026-0029"},
    )

    response = asyncio.run(HTTP_DECISION(req, FakeDurableClient(None)))

    assert response.status_code == 403
    assert "Access denied" in json.loads(response.get_body())["error"]


def test_http_decision_requires_question_for_more_info(monkeypatch) -> None:
    monkeypatch.setattr(http_decision, "get_caller_roles", lambda req: ["Operator"])
    monkeypatch.setattr(http_decision, "get_caller_id", lambda req: "ivan.petrenko")

    req = FakeRequest(
        {"action": "more_info", "user_id": "ivan.petrenko"},
        route_params={"incident_id": "INC-2026-0029"},
    )

    response = asyncio.run(HTTP_DECISION(req, FakeDurableClient(None)))

    assert response.status_code == 400
    assert json.loads(response.get_body())["error"] == "'question' is required when action=more_info"


def test_http_decision_uses_authenticated_caller_identity(monkeypatch) -> None:
    recorded: dict = {}
    monkeypatch.setattr(http_decision, "get_caller_roles", lambda req: ["Operator"])
    monkeypatch.setattr(http_decision, "get_caller_id", lambda req: "auth.operator")
    monkeypatch.setattr(
        http_decision,
        "_record_decision",
        lambda incident_id, decision, now_iso: recorded.update(
            {"incident_id": incident_id, "decision": decision, "now_iso": now_iso}
        ),
    )

    req = FakeRequest(
        {
            "action": "approved",
            "user_id": "spoofed.user",
            "role": "qa-manager",
            "reason": "Proceed with corrective action.",
        },
        route_params={"incident_id": "INC-2026-0029"},
    )
    client = FakeDurableClient(FakeStatus(df.OrchestrationRuntimeStatus.Running))

    response = asyncio.run(HTTP_DECISION(req, client))
    payload = json.loads(response.get_body())

    assert response.status_code == 202
    assert payload == {
        "status": "decision_received",
        "instance_id": "durable-INC-2026-0029",
    }
    assert recorded["incident_id"] == "INC-2026-0029"
    assert recorded["decision"]["user_id"] == "auth.operator"
    assert recorded["decision"]["role"] == "operator"
    assert client.raised_events == [
        (
            "durable-INC-2026-0029",
            "operator_decision",
            {
                "action": "approved",
                "user_id": "auth.operator",
                "role": "operator",
                "reason": "Proceed with corrective action.",
                "question": "",
            },
        )
    ]


def test_http_decision_returns_404_when_no_active_orchestrator(monkeypatch) -> None:
    monkeypatch.setattr(http_decision, "get_caller_roles", lambda req: ["QAManager"])
    monkeypatch.setattr(http_decision, "get_caller_id", lambda req: "qa.manager")

    req = FakeRequest(
        {"action": "rejected", "reason": "Rejected by QA."},
        route_params={"incident_id": "INC-2026-0029"},
    )
    client = FakeDurableClient(FakeStatus(df.OrchestrationRuntimeStatus.Completed))

    response = asyncio.run(HTTP_DECISION(req, client))
    payload = json.loads(response.get_body())

    assert response.status_code == 404
    assert "No active orchestrator found" in payload["error"]
    assert "OrchestrationRuntimeStatus.Completed" in payload["error"]


def test_record_decision_updates_approval_task_incident_and_event(monkeypatch) -> None:
    patched_incident: dict = {}
    created_items: list[dict] = []
    patch_operations: list[dict] = []
    upserted_events: list[dict] = []

    class FakeApprovalTasksContainer:
        def patch_item(self, item, partition_key, patch_operations):
            raise http_decision.CosmosResourceNotFoundError(message="missing")

        def create_item(self, item):
            created_items.append(item)

    class FakeEventsContainer:
        def upsert_item(self, item):
            upserted_events.append(item)

    class FakeDatabase:
        def get_container_client(self, name):
            if name == "approval-tasks":
                return FakeApprovalTasksContainer()
            if name == "incident_events":
                return FakeEventsContainer()
            raise AssertionError(f"Unexpected container: {name}")

    class FakeCosmosClient:
        def get_database_client(self, name):
            assert name == http_decision.DB_NAME
            return FakeDatabase()

    monkeypatch.setattr(http_decision, "get_cosmos_client", lambda: FakeCosmosClient())
    monkeypatch.setattr(
        http_decision,
        "patch_incident_by_id",
        lambda db, incident_id, ops: patched_incident.update({"incident_id": incident_id, "ops": ops}),
    )

    http_decision._record_decision(
        incident_id="INC-2026-0029",
        decision={
            "action": "more_info",
            "user_id": "ivan.petrenko",
            "role": "operator",
            "reason": "",
            "question": "What was the batch moisture at T+0?",
        },
        now_iso="2026-04-20T12:00:00+00:00",
    )

    assert created_items[0]["incidentId"] == "INC-2026-0029"
    assert created_items[0]["status"] == "more_info_requested"
    assert patched_incident["incident_id"] == "INC-2026-0029"
    patch_operations = patched_incident["ops"]
    assert {op["path"]: op["value"] for op in patch_operations}["/status"] == "awaiting_agents"
    assert upserted_events[0]["eventType"] == "operator_decision"
    assert upserted_events[0]["question"] == "What was the batch moisture at T+0?"