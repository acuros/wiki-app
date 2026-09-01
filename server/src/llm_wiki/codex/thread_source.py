from llm_wiki.application.ports import ListThreadsQueryLike
from llm_wiki.codex.mapper import (
    map_thread_list_result,
    map_thread_read_result,
    map_thread_start_result,
    map_turn_start_result,
)
from llm_wiki.codex.rpc_client import CodexRpcClient, RpcRemoteError
from llm_wiki.domain.errors import DependencyProtocolError, ThreadBusy, ThreadNotFound
from llm_wiki.domain.models import Conversation, Page, ThreadId, ThreadSummary, TurnSubmission

AUTO_REVIEW = "auto_review"
WIKI_PROJECT_CWD = "/home/joshua/projects/private/wiki"


class CodexThreadSource:
    def __init__(self, client: CodexRpcClient) -> None:
        self._client = client

    @property
    def is_ready(self) -> bool:
        return self._client.is_ready

    async def start(self) -> None:
        await self._client.start()

    async def stop(self) -> None:
        await self._client.stop()

    async def list(self, query: ListThreadsQueryLike) -> Page[ThreadSummary]:
        try:
            result = await self._client.request(
                "thread/list",
                {
                    "cursor": query.cursor,
                    "limit": query.limit,
                    "sortKey": "recency_at",
                    "sortDirection": "desc",
                    "sourceKinds": ["appServer", "cli", "vscode"],
                    "archived": query.archived,
                },
            )
        except RpcRemoteError as exc:
            raise DependencyProtocolError("Codex rejected thread/list") from exc
        return map_thread_list_result(result)

    async def read(self, thread_id: ThreadId) -> Conversation:
        try:
            result = await self._client.request(
                "thread/read", {"threadId": str(thread_id), "includeTurns": True}
            )
        except RpcRemoteError as exc:
            if _is_not_found(exc):
                raise ThreadNotFound("Thread not found") from exc
            raise DependencyProtocolError("Codex rejected thread/read") from exc
        return map_thread_read_result(result)

    async def create(self, message: str) -> TurnSubmission:
        try:
            start_result = await self._client.request(
                "thread/start",
                {"approvalsReviewer": AUTO_REVIEW, "cwd": WIKI_PROJECT_CWD},
            )
            thread_id = map_thread_start_result(start_result)
            turn_result = await self._client.request(
                "turn/start",
                {
                    "threadId": str(thread_id),
                    "input": [{"type": "text", "text": message}],
                },
            )
        except RpcRemoteError as exc:
            if _is_busy(exc):
                raise ThreadBusy("Thread already has an active turn") from exc
            raise DependencyProtocolError("Codex rejected thread creation") from exc
        return map_turn_start_result(thread_id, turn_result)

    async def send(self, thread_id: ThreadId, message: str) -> TurnSubmission:
        try:
            await self._client.request(
                "thread/resume",
                {"threadId": str(thread_id), "approvalsReviewer": AUTO_REVIEW},
            )
            turn_result = await self._client.request(
                "turn/start",
                {
                    "threadId": str(thread_id),
                    "input": [{"type": "text", "text": message}],
                },
            )
        except RpcRemoteError as exc:
            if _is_not_found(exc):
                raise ThreadNotFound("Thread not found") from exc
            if _is_busy(exc):
                raise ThreadBusy("Thread already has an active turn") from exc
            raise DependencyProtocolError("Codex rejected message submission") from exc
        return map_turn_start_result(thread_id, turn_result)


def _is_not_found(error: RpcRemoteError) -> bool:
    message = error.message.casefold()
    return "not found" in message or "does not exist" in message


def _is_busy(error: RpcRemoteError) -> bool:
    message = error.message.casefold()
    return any(
        phrase in message
        for phrase in ("active turn", "turn is in progress", "turn already in progress")
    )
