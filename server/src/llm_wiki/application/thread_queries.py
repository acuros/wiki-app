from dataclasses import dataclass

from llm_wiki.application.ports import ThreadSource
from llm_wiki.domain.errors import InvalidThreadQuery
from llm_wiki.domain.models import Conversation, Page, ThreadId, ThreadSummary


@dataclass(frozen=True, slots=True)
class ListThreadsQuery:
    cursor: str | None = None
    limit: int = 20
    archived: bool = False


class ThreadQueryService:
    def __init__(self, source: ThreadSource) -> None:
        self._source = source

    async def list_threads(self, query: ListThreadsQuery) -> Page[ThreadSummary]:
        if not 1 <= query.limit <= 100:
            raise InvalidThreadQuery("limit must be between 1 and 100")
        if query.cursor == "":
            raise InvalidThreadQuery("cursor must not be empty")
        return await self._source.list(query)

    async def get_thread(self, thread_id: ThreadId) -> Conversation:
        if not thread_id:
            raise InvalidThreadQuery("thread id must not be empty")
        return await self._source.read(thread_id)
