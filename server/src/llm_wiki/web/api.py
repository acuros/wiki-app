from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Query, Request

from llm_wiki.application.thread_queries import ListThreadsQuery, ThreadQueryService
from llm_wiki.domain.models import ThreadId
from llm_wiki.web.auth import require_tailscale_user
from llm_wiki.web.schemas import (
    ErrorResponse,
    ThreadDetailResponse,
    ThreadListResponse,
    thread_detail_response,
    thread_summary_response,
)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
    504: {"model": ErrorResponse},
}
router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_tailscale_user)])


async def _service(request: Request) -> ThreadQueryService:
    return cast(ThreadQueryService, request.app.state.thread_service)


@router.get("/threads", response_model=ThreadListResponse, responses=ERROR_RESPONSES)
async def list_threads(
    service: Annotated[ThreadQueryService, Depends(_service)],
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query()] = 50,
    archived: Annotated[bool, Query()] = False,
) -> ThreadListResponse:
    page = await service.list_threads(ListThreadsQuery(cursor, limit, archived))
    return ThreadListResponse(
        threads=[thread_summary_response(item) for item in page.items],
        next_cursor=page.next_cursor,
    )


@router.get(
    "/threads/{thread_id}",
    response_model=ThreadDetailResponse,
    responses={**ERROR_RESPONSES, 404: {"model": ErrorResponse}},
)
async def get_thread(
    thread_id: str,
    service: Annotated[ThreadQueryService, Depends(_service)],
) -> ThreadDetailResponse:
    return thread_detail_response(await service.get_thread(ThreadId(thread_id)))
