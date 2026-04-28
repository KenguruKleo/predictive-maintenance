from pathlib import Path
import sys

from azure.ai.agents.models import RunStatus
from azure.core.exceptions import ServiceResponseTimeoutError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from shared.foundry_run import create_thread_and_process_run_with_approval


class _Run:
    def __init__(self, status: RunStatus) -> None:
        self.id = "run-test"
        self.thread_id = "thread-test"
        self.status = status
        self.required_action = None


class _Runs:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.get_kwargs: list[dict] = []

    def get(self, **kwargs):
        self.get_kwargs.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def cancel(self, **kwargs):
        return _Run(RunStatus.CANCELLED)


class _Client:
    def __init__(self, responses: list[object]) -> None:
        self.runs = _Runs(responses)
        self.create_kwargs: dict = {}

    def create_thread_and_run(self, **kwargs):
        self.create_kwargs = kwargs
        return _Run(RunStatus.QUEUED)


def test_foundry_run_uses_network_timeouts_for_create_and_poll() -> None:
    client = _Client([_Run(RunStatus.COMPLETED)])

    result = create_thread_and_process_run_with_approval(
        client,
        agent_id="agent-test",
        thread={},
        max_iterations=1,
        poll_interval=0,
        request_connection_timeout=3,
        request_read_timeout=4,
    )

    assert result.status == RunStatus.COMPLETED
    assert client.create_kwargs["connection_timeout"] == 3
    assert client.create_kwargs["read_timeout"] == 4
    assert client.runs.get_kwargs[0]["connection_timeout"] == 3
    assert client.runs.get_kwargs[0]["read_timeout"] == 4


def test_foundry_run_retries_transient_poll_timeout() -> None:
    client = _Client([
        ServiceResponseTimeoutError("poll read timed out"),
        _Run(RunStatus.COMPLETED),
    ])

    result = create_thread_and_process_run_with_approval(
        client,
        agent_id="agent-test",
        thread={},
        max_wait_seconds=1,
        poll_interval=0,
        request_connection_timeout=3,
        request_read_timeout=4,
    )

    assert result.status == RunStatus.COMPLETED
    assert len(client.runs.get_kwargs) == 2