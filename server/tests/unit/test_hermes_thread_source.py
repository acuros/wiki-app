from pathlib import Path
from typing import Any

import pytest

from llm_wiki.application.thread_queries import ListThreadsQuery
from llm_wiki.domain.errors import DependencyRateLimited, ThreadBusy
from llm_wiki.domain.models import ThreadId
from llm_wiki.hermes.client import HermesHttpError
from llm_wiki.hermes.thread_source import REQUIRED_CAPABILITIES, HermesThreadSource


class FakeHermesClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, object]]] = []
        self.responses: list[object] = []
        self.error: Exception | None = None

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def get(self, path: str, **kwargs: object) -> Any:
        self.calls.append(("GET", path, kwargs))
        if self.error:
            raise self.error
        if path == "/v1/capabilities":
            return {"features": dict.fromkeys(REQUIRED_CAPABILITIES, True)}
        return self.responses.pop(0)

    async def post(self, path: str, **kwargs: object) -> Any:
        self.calls.append(("POST", path, kwargs))
        if self.error:
            raise self.error
        return self.responses.pop(0)

    async def stream_run(self, _run_id: str):
        if False:
            yield {}


def source(client: FakeHermesClient, tmp_path: Path) -> HermesThreadSource:
    return HermesThreadSource(  # type: ignore[arg-type]
        client,
        project_cwd="/home/joshua/projects/private/wiki",
        run_state_path=tmp_path / "runs.json",
    )


async def test_start_requires_extended_hermes_capabilities(tmp_path: Path) -> None:
    client = FakeHermesClient()
    item = source(client, tmp_path)

    await item.start()

    assert item.is_ready is True


async def test_list_uses_offset_cursor_and_includes_all_sources(tmp_path: Path) -> None:
    client = FakeHermesClient()
    client.responses = [
        {
            "data": [
                {
                    "id": "telegram-session",
                    "source": "telegram",
                    "title": None,
                    "preview": "hello",
                    "cwd": "/workspace",
                    "started_at": 1_700_000_000.0,
                    "last_active": 1_700_000_001.0,
                    "activity": {"active": False, "surfaces": [], "started_at": None},
                }
            ],
            "has_more": True,
        }
    ]
    item = source(client, tmp_path)

    page = await item.list(ListThreadsQuery(cursor="20", limit=20, archived=True))

    assert [summary.id for summary in page.items] == ["telegram-session"]
    assert page.next_cursor == "21"
    assert client.calls[0] == (
        "GET",
        "/api/sessions",
        {"params": {"limit": 20, "offset": 20, "archived": "true"}},
    )


async def test_create_persists_wiki_cwd_then_starts_idempotent_run(tmp_path: Path) -> None:
    client = FakeHermesClient()
    client.responses = [
        {"session": {"id": "session-new"}},
        {"run_id": "run-new", "status": "started"},
    ]
    item = source(client, tmp_path)

    submission = await item.create("hello")
    await item.stop()

    assert submission.thread_id == "session-new"
    assert submission.turn_id == "run-new"
    assert client.calls[0] == (
        "POST",
        "/api/sessions",
        {"json": {"source": "api_server", "cwd": "/home/joshua/projects/private/wiki"}},
    )
    assert client.calls[1][0:2] == ("POST", "/v1/runs")
    assert client.calls[1][2]["json"] == {"session_id": "session-new", "input": "hello"}
    assert "Idempotency-Key" in client.calls[1][2]["headers"]


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (HermesHttpError(409, "session_busy", "busy"), ThreadBusy),
        (HermesHttpError(429, "run_limit", "busy"), DependencyRateLimited),
    ],
)
async def test_send_classifies_hermes_errors(
    tmp_path: Path, error: Exception, expected: type[Exception]
) -> None:
    client = FakeHermesClient()
    client.error = error
    item = source(client, tmp_path)

    with pytest.raises(expected):
        await item.send(ThreadId("session-1"), "hello")


async def test_settings_merge_partial_effort_with_existing_model(tmp_path: Path) -> None:
    client = FakeHermesClient()
    client.responses = [
        {
            "session": {
                "id": "session-1",
                "runtime": {
                    "provider": "openai-codex",
                    "model": "gpt-5.6-terra",
                    "model_options": {"reasoning_effort": "medium"},
                },
            }
        },
        {"object": "hermes.session.model_lock"},
    ]
    item = source(client, tmp_path)

    await item.update_settings(ThreadId("session-1"), effort="high")

    assert client.calls[1] == (
        "POST",
        "/api/sessions/session-1/model",
        {
            "json": {
                "provider": "openai-codex",
                "model": "gpt-5.6-terra",
                "model_options": {"reasoning_effort": "high"},
            }
        },
    )
