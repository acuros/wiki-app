from typing import cast

import pytest

from llm_wiki.application.thread_queries import ListThreadsQuery
from llm_wiki.codex.rpc_client import CodexRpcClient, RpcRemoteError
from llm_wiki.codex.thread_source import WIKI_PROJECT_CWD, CodexThreadSource
from llm_wiki.domain.errors import DependencyProtocolError, ThreadBusy, ThreadNotFound
from llm_wiki.domain.models import ThreadId


class FakeRpcClient:
    is_ready = True

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.result: object = {"data": [], "nextCursor": None}
        self.results: list[object] = []
        self.error: Exception | None = None

    async def request(self, method: str, params: dict[str, object]) -> object:
        self.calls.append((method, params))
        if self.error:
            raise self.error
        if self.results:
            return self.results.pop(0)
        return self.result


def raw_thread(thread_id: str, cwd: str) -> dict[str, object]:
    return {
        "id": thread_id,
        "name": f"{thread_id} title",
        "preview": thread_id,
        "source": "appServer",
        "cwd": cwd,
        "projectId": None,
        "createdAt": 1_700_000_000,
        "updatedAt": 1_700_000_000,
        "recencyAt": 1_700_000_000,
        "status": {"type": "idle", "activeFlags": []},
    }


async def test_list_translates_query_to_stable_codex_method() -> None:
    client = FakeRpcClient()
    source = CodexThreadSource(cast(CodexRpcClient, client))

    await source.list(ListThreadsQuery(cursor="opaque", limit=100, archived=True))

    assert client.calls == [
        (
            "thread/list",
            {
                "cursor": "opaque",
                "limit": 100,
                "sortKey": "recency_at",
                "sortDirection": "desc",
                "sourceKinds": ["appServer", "cli", "vscode"],
                "archived": True,
            },
        )
    ]


async def test_list_only_returns_threads_from_wiki_project() -> None:
    client = FakeRpcClient()
    client.result = {
        "data": [
            raw_thread("wiki-thread", WIKI_PROJECT_CWD),
            raw_thread("other-thread", "/home/joshua/projects/fenb/study-api"),
        ],
        "nextCursor": "opaque",
    }
    source = CodexThreadSource(cast(CodexRpcClient, client))

    page = await source.list(ListThreadsQuery())

    assert [thread.id for thread in page.items] == ["wiki-thread"]
    assert page.next_cursor == "opaque"


async def test_list_skips_pages_without_wiki_threads() -> None:
    client = FakeRpcClient()
    client.results = [
        {
            "data": [raw_thread("other-thread", "/home/joshua/projects/fenb/study-api")],
            "nextCursor": "next",
        },
        {
            "data": [raw_thread("wiki-thread", WIKI_PROJECT_CWD)],
            "nextCursor": None,
        },
    ]
    source = CodexThreadSource(cast(CodexRpcClient, client))

    page = await source.list(ListThreadsQuery())

    assert [thread.id for thread in page.items] == ["wiki-thread"]
    assert client.calls[1][1]["cursor"] == "next"


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Thread not found", ThreadNotFound),
        ("Permission denied", DependencyProtocolError),
    ],
)
async def test_read_classifies_remote_errors(message: str, expected: type[Exception]) -> None:
    client = FakeRpcClient()
    client.error = RpcRemoteError(-32000, message)
    source = CodexThreadSource(cast(CodexRpcClient, client))

    with pytest.raises(expected):
        await source.read(ThreadId("missing"))

    assert client.calls == [("thread/read", {"threadId": "missing", "includeTurns": True})]


async def test_create_starts_thread_with_auto_review_then_starts_turn() -> None:
    client = FakeRpcClient()
    client.results = [
        {"thread": {"id": "thread-1"}},
        {"turn": {"id": "turn-1", "status": "inProgress", "items": []}},
    ]
    source = CodexThreadSource(cast(CodexRpcClient, client))

    submission = await source.create("hello")

    assert submission.thread_id == "thread-1"
    assert submission.turn_id == "turn-1"
    assert client.calls == [
        (
            "thread/start",
            {
                "approvalsReviewer": "auto_review",
                "cwd": "/home/joshua/projects/private/wiki",
            },
        ),
        (
            "turn/start",
            {
                "threadId": "thread-1",
                "input": [{"type": "text", "text": "hello"}],
            },
        ),
    ]


async def test_send_resumes_with_auto_review_then_starts_turn() -> None:
    client = FakeRpcClient()
    client.results = [
        {"thread": {"id": "thread-1"}},
        {"turn": {"id": "turn-2", "status": "inProgress", "items": []}},
    ]
    source = CodexThreadSource(cast(CodexRpcClient, client))

    submission = await source.send(ThreadId("thread-1"), "follow up")

    assert submission.turn_id == "turn-2"
    assert client.calls == [
        (
            "thread/resume",
            {"threadId": "thread-1", "approvalsReviewer": "auto_review"},
        ),
        (
            "turn/start",
            {
                "threadId": "thread-1",
                "input": [{"type": "text", "text": "follow up"}],
            },
        ),
    ]


async def test_updates_thread_settings_with_codex_setting_names() -> None:
    client = FakeRpcClient()
    source = CodexThreadSource(cast(CodexRpcClient, client))

    await source.update_settings(ThreadId("thread-1"), model="gpt-5.6-sol", effort="xhigh")

    assert client.calls == [
        (
            "thread/settings/update",
            {"threadId": "thread-1", "model": "gpt-5.6-sol", "effort": "xhigh"},
        )
    ]


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Thread not found", ThreadNotFound),
        ("Thread already has an active turn", ThreadBusy),
        ("Permission denied", DependencyProtocolError),
    ],
)
async def test_send_classifies_remote_errors(message: str, expected: type[Exception]) -> None:
    client = FakeRpcClient()
    client.error = RpcRemoteError(-32000, message)
    source = CodexThreadSource(cast(CodexRpcClient, client))

    with pytest.raises(expected):
        await source.send(ThreadId("thread-1"), "hello")
