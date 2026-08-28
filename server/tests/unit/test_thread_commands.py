from typing import cast

import pytest

from llm_wiki.application.ports import ThreadSource
from llm_wiki.application.thread_commands import ThreadCommandService
from llm_wiki.domain.errors import InvalidMessage, InvalidThreadQuery
from llm_wiki.domain.models import ThreadId, TurnSubmission


class FakeSource:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object, object | None]] = []

    async def create(self, message: str) -> TurnSubmission:
        self.calls.append(("create", message, None))
        return TurnSubmission(ThreadId("thread-1"), "turn-1", "in_progress")

    async def send(self, thread_id: ThreadId, message: str) -> TurnSubmission:
        self.calls.append(("send", thread_id, message))
        return TurnSubmission(thread_id, "turn-2", "in_progress")


async def test_creates_thread_and_sends_message_without_changing_text() -> None:
    source = FakeSource()
    service = ThreadCommandService(cast(ThreadSource, source))

    created = await service.create_thread("  first message  ")
    sent = await service.send_message(ThreadId("thread-1"), "next message")

    assert created.turn_id == "turn-1"
    assert sent.turn_id == "turn-2"
    assert source.calls == [
        ("create", "  first message  ", None),
        ("send", "thread-1", "next message"),
    ]


@pytest.mark.parametrize("message", ["", "   ", "\n\t"])
async def test_rejects_blank_messages(message: str) -> None:
    service = ThreadCommandService(cast(ThreadSource, FakeSource()))

    with pytest.raises(InvalidMessage):
        await service.create_thread(message)


async def test_rejects_empty_thread_id() -> None:
    service = ThreadCommandService(cast(ThreadSource, FakeSource()))

    with pytest.raises(InvalidThreadQuery):
        await service.send_message(ThreadId(""), "message")
