from datetime import UTC, datetime

import httpx

from llm_wiki.application.thread_queries import ListThreadsQuery
from llm_wiki.bootstrap import create_app
from llm_wiki.config import Settings
from llm_wiki.domain.errors import (
    DependencyProtocolError,
    DependencyTimeout,
    DependencyUnavailable,
    ThreadBusy,
    ThreadNotFound,
)
from llm_wiki.domain.models import (
    AssistantMessage,
    AssistantPhase,
    Conversation,
    Page,
    TextContent,
    ThreadId,
    ThreadSourceKind,
    ThreadStatusKind,
    ThreadSummary,
    Turn,
    TurnSubmission,
    UserMessage,
)


def summary() -> ThreadSummary:
    now = datetime(2026, 8, 27, 12, tzinfo=UTC)
    return ThreadSummary(
        ThreadId("thread-1"),
        "A title",
        "preview",
        ThreadSourceKind.APP_SERVER,
        "/workspace",
        None,
        now,
        now,
        now,
        ThreadStatusKind.NOT_LOADED,
        (),
    )


class FakeSource:
    def __init__(self) -> None:
        self.is_ready = True
        self.last_query: ListThreadsQuery | None = None
        self.calls: list[tuple[str, object, object | None]] = []
        self.error: Exception | None = None

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def list(self, query: ListThreadsQuery) -> Page[ThreadSummary]:
        self.last_query = query
        if self.error:
            raise self.error
        return Page((summary(),), "next")

    async def read(self, thread_id: ThreadId) -> Conversation:
        if self.error:
            raise self.error
        return Conversation(
            summary(),
            (
                Turn(
                    "turn-1",
                    "completed",
                    summary().created_at,
                    summary().updated_at,
                    0,
                    (
                        UserMessage("user", (TextContent("hello"),)),
                        AssistantMessage(
                            "agent", AssistantPhase.FINAL_ANSWER, (TextContent("done"),)
                        ),
                    ),
                    1,
                    ("reasoning",),
                ),
            ),
        )

    async def create(self, message: str) -> TurnSubmission:
        if self.error:
            raise self.error
        self.calls.append(("create", message, None))
        return TurnSubmission(ThreadId("thread-new"), "turn-new", "in_progress")

    async def send(self, thread_id: ThreadId, message: str) -> TurnSubmission:
        if self.error:
            raise self.error
        self.calls.append(("send", thread_id, message))
        return TurnSubmission(thread_id, "turn-next", "in_progress")


async def client_for(source: FakeSource) -> httpx.AsyncClient:
    app = create_app(Settings(allowed_tailscale_users="allowed@example.com"), source)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_health_does_not_require_authentication() -> None:
    source = FakeSource()
    async with await client_for(source) as client:
        assert (await client.get("/health/live")).status_code == 200
        assert (await client.get("/health/ready")).status_code == 200
        source.is_ready = False
        assert (await client.get("/health/ready")).status_code == 503


async def test_authentication_and_allowlist() -> None:
    async with await client_for(FakeSource()) as client:
        missing = await client.get("/api/v1/threads")
        forbidden = await client.get(
            "/api/v1/threads", headers={"Tailscale-User-Login": "other@example.com"}
        )
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "authentication_required"
    assert forbidden.status_code == 403


async def test_list_and_detail_contract() -> None:
    source = FakeSource()
    headers = {"Tailscale-User-Login": "allowed@example.com"}
    async with await client_for(source) as client:
        listed = await client.get(
            "/api/v1/threads?cursor=opaque&limit=100&archived=true", headers=headers
        )
        detail = await client.get("/api/v1/threads/thread-1", headers=headers)
    assert listed.status_code == 200
    assert source.last_query == ListThreadsQuery("opaque", 100, True)
    assert listed.json()["threads"][0]["source"] == "app_server"
    assert listed.json()["threads"][0]["created_at"] == "2026-08-27T12:00:00Z"
    assert detail.status_code == 200
    assert [entry["type"] for entry in detail.json()["turns"][0]["entries"]] == [
        "user_message",
        "assistant_message",
    ]
    assert detail.json()["turns"][0]["omitted_item_types"] == ["reasoning"]


async def test_default_thread_page_uses_twenty_items() -> None:
    source = FakeSource()
    headers = {"Tailscale-User-Login": "allowed@example.com"}
    async with await client_for(source) as client:
        response = await client.get("/api/v1/threads", headers=headers)

    assert response.status_code == 200
    assert source.last_query == ListThreadsQuery(limit=20)


async def test_create_and_send_message_contract() -> None:
    source = FakeSource()
    headers = {"Tailscale-User-Login": "allowed@example.com"}
    async with await client_for(source) as client:
        created = await client.post("/api/v1/threads", json={"message": "first"}, headers=headers)
        sent = await client.post(
            "/api/v1/threads/thread-1/messages",
            json={"message": "next"},
            headers=headers,
        )

    assert created.status_code == 202
    assert created.json() == {
        "thread_id": "thread-new",
        "turn_id": "turn-new",
        "status": "in_progress",
    }
    assert sent.status_code == 202
    assert sent.json() == {
        "thread_id": "thread-1",
        "turn_id": "turn-next",
        "status": "in_progress",
    }
    assert source.calls == [
        ("create", "first", None),
        ("send", "thread-1", "next"),
    ]


async def test_rejects_blank_message() -> None:
    headers = {"Tailscale-User-Login": "allowed@example.com"}
    async with await client_for(FakeSource()) as client:
        response = await client.post("/api/v1/threads", json={"message": "   "}, headers=headers)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


async def test_invalid_query_uses_error_envelope_and_request_id() -> None:
    headers = {"Tailscale-User-Login": "allowed@example.com", "X-Request-ID": "request-1"}
    async with await client_for(FakeSource()) as client:
        response = await client.get("/api/v1/threads?limit=101", headers=headers)
    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "invalid_request",
            "message": "The request is invalid.",
            "request_id": "request-1",
        }
    }
    assert response.headers["X-Request-ID"] == "request-1"


async def test_dependency_errors_are_sanitized() -> None:
    headers = {"Tailscale-User-Login": "allowed@example.com"}
    cases = [
        (DependencyUnavailable("secret raw payload"), 503, "dependency_unavailable"),
        (DependencyTimeout("secret raw payload"), 504, "dependency_timeout"),
        (DependencyProtocolError("secret raw payload"), 502, "dependency_protocol_error"),
        (ThreadNotFound("secret raw payload"), 404, "thread_not_found"),
        (ThreadBusy("secret raw payload"), 409, "thread_busy"),
    ]
    for error, status, code in cases:
        source = FakeSource()
        source.error = error
        async with await client_for(source) as client:
            response = await client.post(
                "/api/v1/threads/thread-1/messages",
                json={"message": "next"},
                headers=headers,
            )
        assert response.status_code == status
        assert response.json()["error"]["code"] == code
        assert "secret" not in response.text
