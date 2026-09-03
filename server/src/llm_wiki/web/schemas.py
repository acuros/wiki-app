from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from llm_wiki.domain.models import (
    AssistantMessage,
    Conversation,
    ConversationEntry,
    Plan,
    ReferenceContent,
    TextContent,
    ThreadSummary,
    TurnSubmission,
    UserMessage,
)


class TextContentResponse(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ReferenceContentResponse(BaseModel):
    type: Literal["reference"] = "reference"
    reference_type: str
    target: str
    name: str | None = None


ContentResponse = Annotated[
    TextContentResponse | ReferenceContentResponse, Field(discriminator="type")
]


class UserMessageResponse(BaseModel):
    id: str
    type: Literal["user_message"] = "user_message"
    content: list[ContentResponse]


class AssistantMessageResponse(BaseModel):
    id: str
    type: Literal["assistant_message"] = "assistant_message"
    phase: str
    content: list[ContentResponse]


class PlanResponse(BaseModel):
    id: str
    type: Literal["plan"] = "plan"
    content: list[ContentResponse]


EntryResponse = Annotated[
    UserMessageResponse | AssistantMessageResponse | PlanResponse,
    Field(discriminator="type"),
]


class ThreadSummaryResponse(BaseModel):
    id: str
    title: str | None
    preview: str
    source: str
    cwd: str
    project_id: str | None
    created_at: datetime
    updated_at: datetime
    recency_at: datetime
    status: str
    active_flags: list[str]


class TurnResponse(BaseModel):
    id: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    entries: list[EntryResponse]
    omitted_item_count: int
    omitted_item_types: list[str]


class ThreadListResponse(BaseModel):
    threads: list[ThreadSummaryResponse]
    next_cursor: str | None


class ThreadDetailResponse(ThreadSummaryResponse):
    turns: list[TurnResponse]


class MessageRequest(BaseModel):
    message: str


class ThreadSettingsRequest(BaseModel):
    model: Literal["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"] | None = None
    effort: Literal["none", "low", "medium", "high", "xhigh"] | None = None


class TurnSubmissionResponse(BaseModel):
    thread_id: str
    turn_id: str
    status: Literal["in_progress"]


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorBody


def _content(block: TextContent | ReferenceContent) -> ContentResponse:
    if isinstance(block, TextContent):
        return TextContentResponse(text=block.text)
    return ReferenceContentResponse(
        reference_type=block.reference_type.value,
        target=block.target,
        name=block.name,
    )


def _entry(entry: ConversationEntry) -> EntryResponse:
    content = [_content(block) for block in entry.content]
    if isinstance(entry, UserMessage):
        return UserMessageResponse(id=entry.id, content=content)
    if isinstance(entry, AssistantMessage):
        return AssistantMessageResponse(id=entry.id, phase=entry.phase.value, content=content)
    if isinstance(entry, Plan):
        return PlanResponse(id=entry.id, content=content)
    raise AssertionError("Unhandled conversation entry")


def thread_summary_response(summary: ThreadSummary) -> ThreadSummaryResponse:
    return ThreadSummaryResponse(
        id=summary.id,
        title=summary.title,
        preview=summary.preview,
        source=summary.source.value,
        cwd=summary.cwd,
        project_id=summary.project_id,
        created_at=summary.created_at,
        updated_at=summary.updated_at,
        recency_at=summary.recency_at,
        status=summary.status.value,
        active_flags=list(summary.active_flags),
    )


def thread_detail_response(conversation: Conversation) -> ThreadDetailResponse:
    summary = thread_summary_response(conversation.summary)
    turns = [
        TurnResponse(
            id=turn.id,
            status=turn.status,
            started_at=turn.started_at,
            completed_at=turn.completed_at,
            duration_ms=turn.duration_ms,
            entries=[_entry(entry) for entry in turn.entries],
            omitted_item_count=turn.omitted_item_count,
            omitted_item_types=list(turn.omitted_item_types),
        )
        for turn in conversation.turns
    ]
    return ThreadDetailResponse(**summary.model_dump(), turns=turns)


def turn_submission_response(submission: TurnSubmission) -> TurnSubmissionResponse:
    return TurnSubmissionResponse(
        thread_id=submission.thread_id,
        turn_id=submission.turn_id,
        status="in_progress",
    )
