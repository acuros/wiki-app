from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import NewType

ThreadId = NewType("ThreadId", str)


class ThreadSourceKind(StrEnum):
    APP_SERVER = "app_server"
    CLI = "cli"
    VSCODE = "vscode"
    UNKNOWN = "unknown"


class ThreadStatusKind(StrEnum):
    NOT_LOADED = "not_loaded"
    IDLE = "idle"
    SYSTEM_ERROR = "system_error"
    ACTIVE = "active"
    UNKNOWN = "unknown"


class AssistantPhase(StrEnum):
    COMMENTARY = "commentary"
    FINAL_ANSWER = "final_answer"
    UNKNOWN = "unknown"


class ReferenceKind(StrEnum):
    IMAGE = "image"
    LOCAL_IMAGE = "local_image"
    AUDIO = "audio"
    LOCAL_AUDIO = "local_audio"
    SKILL = "skill"
    MENTION = "mention"


@dataclass(frozen=True, slots=True)
class ThreadSummary:
    id: ThreadId
    title: str | None
    preview: str
    source: ThreadSourceKind
    cwd: str
    project_id: str | None
    created_at: datetime
    updated_at: datetime
    recency_at: datetime
    status: ThreadStatusKind
    active_flags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TextContent:
    text: str


@dataclass(frozen=True, slots=True)
class ReferenceContent:
    reference_type: ReferenceKind
    target: str
    name: str | None = None


ContentBlock = TextContent | ReferenceContent


@dataclass(frozen=True, slots=True)
class UserMessage:
    id: str
    content: tuple[ContentBlock, ...]


@dataclass(frozen=True, slots=True)
class AssistantMessage:
    id: str
    phase: AssistantPhase
    content: tuple[ContentBlock, ...]


@dataclass(frozen=True, slots=True)
class Plan:
    id: str
    content: tuple[ContentBlock, ...]


ConversationEntry = UserMessage | AssistantMessage | Plan


@dataclass(frozen=True, slots=True)
class Turn:
    id: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    entries: tuple[ConversationEntry, ...]
    omitted_item_count: int
    omitted_item_types: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Conversation:
    summary: ThreadSummary
    turns: tuple[Turn, ...]


@dataclass(frozen=True, slots=True)
class Page[T]:
    items: tuple[T, ...]
    next_cursor: str | None
