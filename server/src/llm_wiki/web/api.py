from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Query, Request, status

from llm_wiki.application.thread_commands import ThreadCommandService
from llm_wiki.application.thread_queries import ListThreadsQuery, ThreadQueryService
from llm_wiki.domain.models import ThreadId
from llm_wiki.web.auth import require_tailscale_user
from llm_wiki.web.schemas import (
    ErrorResponse,
    MessageRequest,
    ThreadDetailResponse,
    ThreadListResponse,
    TurnSubmissionResponse,
    thread_detail_response,
    thread_summary_response,
    turn_submission_response,
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


async def _query_service(request: Request) -> ThreadQueryService:
    return cast(ThreadQueryService, request.app.state.thread_query_service)


async def _command_service(request: Request) -> ThreadCommandService:
    return cast(ThreadCommandService, request.app.state.thread_command_service)


@router.get("/threads", response_model=ThreadListResponse, responses=ERROR_RESPONSES)
async def list_threads(
    service: Annotated[ThreadQueryService, Depends(_query_service)],
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query()] = 20,
    archived: Annotated[bool, Query()] = False,
) -> ThreadListResponse:
    page = await service.list_threads(ListThreadsQuery(cursor, limit, archived))
    return ThreadListResponse(
        threads=[thread_summary_response(item) for item in page.items],
        next_cursor=page.next_cursor,
    )


@router.post(
    "/threads",
    response_model=TurnSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={**ERROR_RESPONSES, 409: {"model": ErrorResponse}},
)
async def create_thread(
    body: MessageRequest,
    service: Annotated[ThreadCommandService, Depends(_command_service)],
) -> TurnSubmissionResponse:
    return turn_submission_response(await service.create_thread(body.message))


@router.get(
    "/threads/{thread_id}",
    response_model=ThreadDetailResponse,
    responses={**ERROR_RESPONSES, 404: {"model": ErrorResponse}},
)
async def get_thread(
    thread_id: str,
    service: Annotated[ThreadQueryService, Depends(_query_service)],
) -> ThreadDetailResponse:
    return thread_detail_response(await service.get_thread(ThreadId(thread_id)))


@router.post(
    "/threads/{thread_id}/messages",
    response_model=TurnSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        **ERROR_RESPONSES,
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def send_message(
    thread_id: str,
    body: MessageRequest,
    service: Annotated[ThreadCommandService, Depends(_command_service)],
) -> TurnSubmissionResponse:
    return turn_submission_response(await service.send_message(ThreadId(thread_id), body.message))
