from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Never

from llm_wiki.domain.errors import DependencyProtocolError
from llm_wiki.domain.models import (
    AssistantMessage,
    AssistantPhase,
    Conversation,
    ConversationEntry,
    TextContent,
    ThreadId,
    ThreadSourceKind,
    ThreadStatusKind,
    ThreadSummary,
    Turn,
    UserMessage,
)
from llm_wiki.hermes.run_tracker import TrackedRun

JsonObject = Mapping[str, Any]
PERSISTED_MESSAGE_MATCH_WINDOW_SECONDS = 60


def _invalid() -> Never:
    raise DependencyProtocolError("Hermes returned an invalid response")


def _object(value: object) -> JsonObject:
    if not isinstance(value, Mapping):
        _invalid()
    return value


def _string(data: JsonObject, key: str, default: str = "") -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        _invalid()
    return value


def _nullable_string(data: JsonObject, key: str) -> str:
    value = data.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        _invalid()
    return value


def _timestamp(value: object, *, required: bool = False) -> datetime | None:
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _invalid()
    try:
        return datetime.fromtimestamp(value, UTC)
    except (OverflowError, OSError, ValueError):
        _invalid()


def map_summary(value: object, *, locally_active: bool = False) -> ThreadSummary:
    data = _object(value)
    session_id = _string(data, "id")
    if not session_id:
        _invalid()
    started_at = _timestamp(data.get("started_at"), required=True)
    last_active = _timestamp(data.get("last_active")) or started_at
    assert started_at is not None and last_active is not None
    activity = data.get("activity")
    activity = activity if isinstance(activity, Mapping) else {}
    active = activity.get("active") is True or locally_active
    surfaces = activity.get("surfaces")
    flags = tuple(str(item) for item in surfaces) if isinstance(surfaces, list) else ()
    preview = _nullable_string(data, "preview")
    title = data.get("title")
    if title is not None and not isinstance(title, str):
        _invalid()
    return ThreadSummary(
        id=ThreadId(session_id),
        title=title or preview or None,
        preview=preview,
        source=ThreadSourceKind.HERMES,
        cwd=_nullable_string(data, "cwd"),
        project_id=None,
        created_at=started_at,
        updated_at=last_active,
        recency_at=last_active,
        status=ThreadStatusKind.ACTIVE if active else ThreadStatusKind.IDLE,
        active_flags=flags or (("turn",) if active else ()),
    )


def map_conversation(
    session: object,
    messages: Sequence[dict[str, Any]],
    overlays: Sequence[TrackedRun] = (),
) -> Conversation:
    active = any(not run.terminal for run in overlays)
    summary = map_summary(session, locally_active=active)
    groups: list[list[dict[str, Any]]] = []
    for message in messages:
        if message.get("role") == "user" or not groups:
            groups.append([])
        groups[-1].append(message)
    turns = [
        _map_turn(group, index, active=active and index == len(groups) - 1)
        for index, group in enumerate(groups)
    ]
    turns.extend(
        _overlay_turn(run, include_user=not _has_persisted_user_message(messages, run))
        for run in overlays
    )
    return Conversation(summary=summary, turns=tuple(turns))


def _has_persisted_user_message(
    messages: Sequence[dict[str, Any]], run: TrackedRun
) -> bool:
    for message in messages:
        if message.get("role") != "user" or message.get("content") != run.user_message:
            continue
        timestamp = message.get("timestamp")
        if isinstance(timestamp, (int, float)) and not isinstance(timestamp, bool):
            if abs(timestamp - run.created_at) <= PERSISTED_MESSAGE_MATCH_WINDOW_SECONDS:
                return True
    return False


def _map_turn(messages: list[dict[str, Any]], index: int, *, active: bool) -> Turn:
    textual_assistants = [
        position
        for position, message in enumerate(messages)
        if message.get("role") == "assistant" and isinstance(message.get("content"), str)
        and bool(str(message.get("content") or ""))
    ]
    final_position = textual_assistants[-1] if textual_assistants else None
    entries: list[ConversationEntry] = []
    omitted: list[str] = []
    omitted_count = 0
    for position, message in enumerate(messages):
        role = str(message.get("role") or "unknown")
        message_id = str(message.get("id") or f"message-{index}-{position}")
        content = message.get("content")
        if role == "user" and isinstance(content, str):
            entries.append(UserMessage(message_id, (TextContent(content),)))
            continue
        if role == "assistant":
            reasoning = message.get("reasoning_content") or message.get("reasoning")
            if isinstance(reasoning, str) and reasoning:
                entries.append(
                    AssistantMessage(
                        f"{message_id}-reasoning",
                        AssistantPhase.COMMENTARY,
                        (TextContent(reasoning),),
                    )
                )
            if isinstance(content, str) and content:
                phase = (
                    AssistantPhase.FINAL_ANSWER
                    if position == final_position
                    else AssistantPhase.COMMENTARY
                )
                entries.append(AssistantMessage(message_id, phase, (TextContent(content),)))
                continue
        omitted_count += 1
        if role not in omitted:
            omitted.append(role)
    timestamps = [
        timestamp
        for message in messages
        if (timestamp := _timestamp(message.get("timestamp"))) is not None
    ]
    started_at = timestamps[0] if timestamps else None
    completed_at = None if active else (timestamps[-1] if timestamps else None)
    duration_ms = (
        int((completed_at - started_at).total_seconds() * 1000)
        if started_at is not None and completed_at is not None
        else None
    )
    first_id = str(messages[0].get("id") or index) if messages else str(index)
    return Turn(
        id=f"hermes-{first_id}",
        status="inProgress" if active else "completed",
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        entries=tuple(entries),
        omitted_item_count=omitted_count,
        omitted_item_types=tuple(omitted),
    )


def _overlay_turn(run: TrackedRun, *, include_user: bool) -> Turn:
    started_at = datetime.fromtimestamp(run.created_at, UTC)
    entries: list[ConversationEntry] = []
    if include_user:
        entries.append(UserMessage(f"{run.run_id}-user", (TextContent(run.user_message),)))
    entries.extend(
        AssistantMessage(
            f"{run.run_id}-commentary-{index}",
            AssistantPhase.COMMENTARY,
            (TextContent(text),),
        )
        for index, text in enumerate(run.commentary)
    )
    if run.final_answer:
        entries.append(
            AssistantMessage(
                f"{run.run_id}-answer",
                AssistantPhase.FINAL_ANSWER,
                (TextContent(run.final_answer),),
            )
        )
    return Turn(
        id=run.run_id,
        status="completed" if run.terminal else "inProgress",
        started_at=started_at,
        completed_at=None,
        duration_ms=None,
        entries=tuple(entries),
        omitted_item_count=0,
        omitted_item_types=(),
    )
