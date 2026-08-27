from llm_wiki.application.ports import ListThreadsQueryLike
from llm_wiki.codex.mapper import map_thread_list_result, map_thread_read_result
from llm_wiki.codex.rpc_client import CodexRpcClient, RpcRemoteError
from llm_wiki.domain.errors import DependencyProtocolError, ThreadNotFound
from llm_wiki.domain.models import Conversation, Page, ThreadId, ThreadSummary


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
            message = exc.message.casefold()
            if "not found" in message or "does not exist" in message:
                raise ThreadNotFound("Thread not found") from exc
            raise DependencyProtocolError("Codex rejected thread/read") from exc
        return map_thread_read_result(result)
