from typing import cast

import pytest

from llm_wiki.application.ports import ThreadSource
from llm_wiki.application.thread_queries import ListThreadsQuery, ThreadQueryService
from llm_wiki.domain.errors import InvalidThreadQuery


class UnusedSource:
    async def list(self, query: object) -> object:
        raise AssertionError("source should not be called")

    async def read(self, thread_id: object) -> object:
        raise AssertionError("source should not be called")


@pytest.mark.parametrize("limit", [0, 101])
async def test_rejects_invalid_limits(limit: int) -> None:
    service = ThreadQueryService(cast(ThreadSource, UnusedSource()))
    with pytest.raises(InvalidThreadQuery):
        await service.list_threads(ListThreadsQuery(limit=limit))


async def test_rejects_empty_cursor() -> None:
    service = ThreadQueryService(cast(ThreadSource, UnusedSource()))
    with pytest.raises(InvalidThreadQuery):
        await service.list_threads(ListThreadsQuery(cursor=""))
