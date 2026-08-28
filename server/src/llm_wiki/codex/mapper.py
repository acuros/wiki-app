from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Never

from llm_wiki.domain.errors import DependencyProtocolError
from llm_wiki.domain.models import (
    AssistantMessage,
    AssistantPhase,
    Conversation,
    ConversationEntry,
    Page,
    Plan,
    ReferenceContent,
    ReferenceKind,
    TextContent,
    ThreadId,
    ThreadSourceKind,
    ThreadStatusKind,
    ThreadSummary,
    Turn,
    TurnSubmission,
    UserMessage,
)

JsonObject = Mapping[str, Any]


def _protocol_error() -> Never:
    raise DependencyProtocolError("Codex returned an invalid response")


def _object(value: object) -> JsonObject:
    if not isinstance(value, Mapping):
        _protocol_error()
    return value


def _required_string(data: JsonObject, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        _protocol_error()
    return value


def _optional_string(data: JsonObject, key: str) -> str | None:
    value = data.get(key)
    if value is not None and not isinstance(value, str):
        _protocol_error()
    return value


def _required_nullable_string(data: JsonObject, key: str) -> str | None:
    if key not in data:
        _protocol_error()
    return _optional_string(data, key)


def _timestamp(value: object, *, optional: bool = False) -> datetime | None:
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        _protocol_error()
    try:
        return datetime.fromtimestamp(value, UTC)
    except OverflowError, OSError, ValueError:
        _protocol_error()


def _source(value: object) -> ThreadSourceKind:
    if value == "appServer":
        return ThreadSourceKind.APP_SERVER
    if value == "cli":
        return ThreadSourceKind.CLI
    if value == "vscode":
        return ThreadSourceKind.VSCODE
    if isinstance(value, str):
        return ThreadSourceKind.UNKNOWN
    if isinstance(value, Mapping):
        custom = value.get("custom")
        sub_agent = value.get("subAgent")
        if isinstance(custom, str) or isinstance(sub_agent, Mapping):
            return ThreadSourceKind.UNKNOWN
    _protocol_error()


def _status(value: object) -> tuple[ThreadStatusKind, tuple[str, ...]]:
    data = _object(value)
    status_type = _required_string(data, "type")
    status = {
        "notLoaded": ThreadStatusKind.NOT_LOADED,
        "idle": ThreadStatusKind.IDLE,
        "systemError": ThreadStatusKind.SYSTEM_ERROR,
        "active": ThreadStatusKind.ACTIVE,
    }.get(status_type, ThreadStatusKind.UNKNOWN)
    flags_value = data.get("activeFlags", [])
    if not isinstance(flags_value, list) or not all(isinstance(flag, str) for flag in flags_value):
        _protocol_error()
    return status, tuple(flags_value)


def map_thread_summary(value: object) -> ThreadSummary:
    data = _object(value)
    created_at = _timestamp(data.get("createdAt"))
    updated_at = _timestamp(data.get("updatedAt"))
    recency_at = _timestamp(data.get("recencyAt"), optional=True) or updated_at
    assert created_at is not None and updated_at is not None and recency_at is not None
    status, active_flags = _status(data.get("status"))
    return ThreadSummary(
        id=ThreadId(_required_string(data, "id")),
        title=_optional_string(data, "name"),
        preview=_required_string(data, "preview"),
        source=_source(data.get("source")),
        cwd=_required_string(data, "cwd"),
        project_id=_required_nullable_string(data, "projectId"),
        created_at=created_at,
        updated_at=updated_at,
        recency_at=recency_at,
        status=status,
        active_flags=active_flags,
    )


def _reference(data: JsonObject, item_type: str) -> ReferenceContent:
    reference_type = {
        "image": ReferenceKind.IMAGE,
        "localImage": ReferenceKind.LOCAL_IMAGE,
        "audio": ReferenceKind.AUDIO,
        "localAudio": ReferenceKind.LOCAL_AUDIO,
        "skill": ReferenceKind.SKILL,
        "mention": ReferenceKind.MENTION,
    }.get(item_type)
    if reference_type is None:
        _protocol_error()
    target_key = "url" if item_type in {"image", "audio"} else "path"
    name = _optional_string(data, "name") if item_type in {"skill", "mention"} else None
    return ReferenceContent(reference_type, _required_string(data, target_key), name)


def _user_message(data: JsonObject) -> UserMessage:
    content_value = data.get("content")
    if not isinstance(content_value, list):
        _protocol_error()
    content: list[TextContent | ReferenceContent] = []
    for raw_block in content_value:
        block = _object(raw_block)
        block_type = _required_string(block, "type")
        if block_type == "text":
            content.append(TextContent(_required_string(block, "text")))
        else:
            content.append(_reference(block, block_type))
    return UserMessage(_required_string(data, "id"), tuple(content))


def _entry(value: object) -> ConversationEntry | None:
    data = _object(value)
    item_type = _required_string(data, "type")
    if item_type == "userMessage":
        return _user_message(data)
    if item_type == "agentMessage":
        phase_value = data.get("phase")
        phase = (
            {
                "commentary": AssistantPhase.COMMENTARY,
                "final_answer": AssistantPhase.FINAL_ANSWER,
            }.get(phase_value, AssistantPhase.UNKNOWN)
            if isinstance(phase_value, str)
            else AssistantPhase.UNKNOWN
        )
        return AssistantMessage(
            _required_string(data, "id"),
            phase,
            (TextContent(_required_string(data, "text")),),
        )
    if item_type == "plan":
        return Plan(
            _required_string(data, "id"),
            (TextContent(_required_string(data, "text")),),
        )
    return None


def _turn(value: object) -> Turn:
    data = _object(value)
    items = data.get("items")
    if not isinstance(items, list):
        _protocol_error()
    entries: list[ConversationEntry] = []
    omitted_types: list[str] = []
    omitted_count = 0
    for raw_item in items:
        item = _object(raw_item)
        item_type = _required_string(item, "type")
        entry = _entry(item)
        if entry is None:
            omitted_count += 1
            if item_type not in omitted_types:
                omitted_types.append(item_type)
        else:
            entries.append(entry)
    duration = data.get("durationMs")
    if duration is not None and (isinstance(duration, bool) or not isinstance(duration, int)):
        _protocol_error()
    return Turn(
        id=_required_string(data, "id"),
        status=_required_string(data, "status"),
        started_at=_timestamp(data.get("startedAt"), optional=True),
        completed_at=_timestamp(data.get("completedAt"), optional=True),
        duration_ms=duration,
        entries=tuple(entries),
        omitted_item_count=omitted_count,
        omitted_item_types=tuple(omitted_types),
    )


def map_thread_list_result(value: object) -> Page[ThreadSummary]:
    data = _object(value)
    raw_items = data.get("data")
    if not isinstance(raw_items, list):
        _protocol_error()
    cursor = data.get("nextCursor")
    if cursor is not None and not isinstance(cursor, str):
        _protocol_error()
    return Page(tuple(map_thread_summary(item) for item in raw_items), cursor)


def map_thread_read_result(value: object) -> Conversation:
    data = _object(value)
    raw_thread = _object(data.get("thread"))
    turns = raw_thread.get("turns")
    if not isinstance(turns, list):
        _protocol_error()
    return Conversation(map_thread_summary(raw_thread), tuple(_turn(turn) for turn in turns))


def map_thread_start_result(value: object) -> ThreadId:
    data = _object(value)
    thread = _object(data.get("thread"))
    return ThreadId(_required_string(thread, "id"))


def map_turn_start_result(thread_id: ThreadId, value: object) -> TurnSubmission:
    data = _object(value)
    turn = _object(data.get("turn"))
    if _required_string(turn, "status") != "inProgress":
        _protocol_error()
    return TurnSubmission(
        thread_id=thread_id,
        turn_id=_required_string(turn, "id"),
        status="in_progress",
    )
