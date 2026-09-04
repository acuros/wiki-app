from llm_wiki.domain.models import AssistantMessage, AssistantPhase, UserMessage
from llm_wiki.hermes.mapper import map_conversation, map_summary
from llm_wiki.hermes.run_tracker import TrackedRun


def raw_session(*, active: bool = False) -> dict[str, object]:
    return {
        "id": "session-1",
        "source": "desktop",
        "title": "Hermes session",
        "preview": "hello",
        "cwd": "/workspace",
        "started_at": 1_700_000_000.0,
        "last_active": 1_700_000_010.0,
        "activity": {
            "active": active,
            "surfaces": ["desktop"] if active else [],
            "started_at": 1_700_000_005.0 if active else None,
        },
    }


def test_summary_maps_hermes_activity_without_source_filtering() -> None:
    summary = map_summary(raw_session(active=True))

    assert summary.id == "session-1"
    assert summary.source == "hermes"
    assert summary.status == "active"
    assert summary.active_flags == ("desktop",)
    assert summary.cwd == "/workspace"


def test_conversation_groups_messages_and_keeps_only_last_answer_final() -> None:
    messages = [
        {"id": "u1", "role": "user", "content": "hello", "timestamp": 1_700_000_001.0},
        {
            "id": "a1",
            "role": "assistant",
            "content": "checking",
            "reasoning_content": "thinking",
            "timestamp": 1_700_000_002.0,
        },
        {"id": "t1", "role": "tool", "content": "secret args", "timestamp": 1_700_000_003.0},
        {"id": "a2", "role": "assistant", "content": "done", "timestamp": 1_700_000_004.0},
    ]

    conversation = map_conversation(raw_session(), messages)
    turn = conversation.turns[0]

    assert isinstance(turn.entries[0], UserMessage)
    assistant = [entry for entry in turn.entries if isinstance(entry, AssistantMessage)]
    assert [entry.phase for entry in assistant] == [
        AssistantPhase.COMMENTARY,
        AssistantPhase.COMMENTARY,
        AssistantPhase.FINAL_ANSWER,
    ]
    assert turn.omitted_item_types == ("tool",)
    assert "secret args" not in repr(turn.entries)


def test_conversation_does_not_repeat_a_tracked_user_message_after_it_is_persisted() -> None:
    messages = [
        {"id": "u1", "role": "user", "content": "hello", "timestamp": 1_700_000_001.0},
    ]
    run = TrackedRun(
        run_id="run-1",
        session_id="session-1",
        user_message="hello",
        created_at=1_700_000_001.5,
        status="running",
        commentary=["searching"],
    )

    conversation = map_conversation(raw_session(), messages, [run])
    entries = [entry for turn in conversation.turns for entry in turn.entries]

    assert sum(isinstance(entry, UserMessage) for entry in entries) == 1
    assert any(
        isinstance(entry, AssistantMessage) and entry.content[0].text == "searching"
        for entry in entries
    )


def test_conversation_keeps_overlay_user_when_matching_history_is_old() -> None:
    messages = [
        {"id": "u1", "role": "user", "content": "hello", "timestamp": 1_700_000_001.0},
    ]
    run = TrackedRun(
        run_id="run-1",
        session_id="session-1",
        user_message="hello",
        created_at=1_700_001_001.0,
        status="running",
    )

    conversation = map_conversation(raw_session(), messages, [run])
    entries = [entry for turn in conversation.turns for entry in turn.entries]

    assert sum(isinstance(entry, UserMessage) for entry in entries) == 2
