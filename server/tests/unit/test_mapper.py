from datetime import UTC, datetime

import pytest

from llm_wiki.codex.mapper import map_thread_list_result, map_thread_read_result
from llm_wiki.domain.errors import DependencyProtocolError
from llm_wiki.domain.models import AssistantMessage, ReferenceContent, UserMessage


def raw_thread(*, turns: list[object] | None = None) -> dict[str, object]:
    return {
        "id": "thread-1",
        "name": "Thread title",
        "preview": "hello",
        "source": "appServer",
        "cwd": "/workspace",
        "projectId": None,
        "createdAt": 1_700_000_000,
        "updatedAt": 1_700_000_100,
        "recencyAt": None,
        "status": {"type": "active", "activeFlags": ["waitingOnUserInput"]},
        "turns": turns or [],
        "unknownAdditiveField": {"allowed": True},
    }


def test_maps_thread_page_and_falls_back_to_updated_at_for_recency() -> None:
    page = map_thread_list_result({"data": [raw_thread()], "nextCursor": "opaque"})

    summary = page.items[0]
    assert summary.id == "thread-1"
    assert summary.source == "app_server"
    assert summary.status == "active"
    assert summary.active_flags == ("waitingOnUserInput",)
    assert summary.created_at == datetime.fromtimestamp(1_700_000_000, UTC)
    assert summary.recency_at == summary.updated_at
    assert page.next_cursor == "opaque"


def test_projects_conversation_entries_and_reports_omissions() -> None:
    turn = {
        "id": "turn-1",
        "status": "completed",
        "startedAt": 1_700_000_000,
        "completedAt": 1_700_000_001,
        "durationMs": 1000,
        "items": [
            {
                "id": "user-1",
                "type": "userMessage",
                "content": [
                    {"type": "text", "text": "hello"},
                    {"type": "image", "url": "https://example.test/image.png"},
                    {"type": "skill", "name": "demo", "path": "/skills/demo"},
                ],
            },
            {"id": "agent-1", "type": "agentMessage", "text": "working", "phase": "commentary"},
            {"id": "agent-2", "type": "agentMessage", "text": "done", "phase": None},
            {"id": "plan-1", "type": "plan", "text": "one step"},
            {"id": "reason-1", "type": "reasoning", "summary": []},
            {"id": "tool-1", "type": "commandExecution"},
            {"id": "reason-2", "type": "reasoning", "summary": []},
            {"id": "future-1", "type": "futureItem", "extra": True},
        ],
    }

    conversation = map_thread_read_result({"thread": raw_thread(turns=[turn])})

    mapped_turn = conversation.turns[0]
    assert len(mapped_turn.entries) == 4
    assert isinstance(mapped_turn.entries[0], UserMessage)
    assert isinstance(mapped_turn.entries[0].content[1], ReferenceContent)
    assert isinstance(mapped_turn.entries[1], AssistantMessage)
    assert mapped_turn.entries[1].phase == "commentary"
    assert isinstance(mapped_turn.entries[2], AssistantMessage)
    assert mapped_turn.entries[2].phase == "unknown"
    assert mapped_turn.omitted_item_count == 4
    assert mapped_turn.omitted_item_types == ("reasoning", "commandExecution", "futureItem")


@pytest.mark.parametrize(
    "payload",
    [
        {"data": [{**raw_thread(), "id": 123}]},
        {"data": [{**raw_thread(), "createdAt": "today"}]},
        {"data": [{key: value for key, value in raw_thread().items() if key != "source"}]},
        {"data": [{key: value for key, value in raw_thread().items() if key != "projectId"}]},
        {"data": [{**raw_thread(), "status": {"type": "active", "activeFlags": "bad"}}]},
        {"nextCursor": None},
    ],
)
def test_rejects_missing_or_invalid_required_fields(payload: object) -> None:
    with pytest.raises(DependencyProtocolError):
        map_thread_list_result(payload)
