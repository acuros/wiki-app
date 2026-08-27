from typing import Protocol

from llm_wiki.domain.models import Conversation, Page, ThreadId, ThreadSummary


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


class ReadinessProbe(Protocol):
    @property
    def is_ready(self) -> bool: ...
