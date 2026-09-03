from typing import Protocol

from llm_wiki.domain.models import Conversation, Page, ThreadId, ThreadSummary, TurnSubmission


class ListThreadsQueryLike(Protocol):
    @property
    def cursor(self) -> str | None: ...

    @property
    def limit(self) -> int: ...

    @property
    def archived(self) -> bool: ...


class ThreadSource(Protocol):
    async def list(self, query: ListThreadsQueryLike) -> Page[ThreadSummary]: ...

    async def read(self, thread_id: ThreadId) -> Conversation: ...

    async def create(self, message: str) -> TurnSubmission: ...

    async def send(self, thread_id: ThreadId, message: str) -> TurnSubmission: ...

    async def update_settings(
        self, thread_id: ThreadId, *, model: str | None = None, effort: str | None = None
    ) -> None: ...


class ReadinessProbe(Protocol):
    @property
    def is_ready(self) -> bool: ...
