import asyncio
import contextlib
import json
import logging
import random
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from websockets.asyncio.client import ClientConnection, unix_connect
from websockets.exceptions import ConnectionClosed, WebSocketException

from llm_wiki import __version__
from llm_wiki.domain.errors import (
    DependencyProtocolError,
    DependencyTimeout,
    DependencyUnavailable,
)

logger = logging.getLogger(__name__)
Connector = Callable[[], Awaitable[ClientConnection]]


class RpcRemoteError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class CodexRpcClient:
    def __init__(
        self,
        socket_path: str,
        *,
        connect_timeout: float = 5,
        request_timeout: float = 30,
        max_pending: int = 32,
        max_message_bytes: int = 67_108_864,
        connector: Connector | None = None,
    ) -> None:
        self._socket_path = socket_path
        self._connect_timeout = connect_timeout
        self._request_timeout = request_timeout
        self._pending_limit = asyncio.Semaphore(max_pending)
        self._send_lock = asyncio.Lock()
        self._next_id = 0
        self._pending: dict[int, asyncio.Future[object]] = {}
        self._websocket: ClientConnection | None = None
        self._runner: asyncio.Task[None] | None = None
        self._stopping = False
        self._ready = False
        self._ready_event = asyncio.Event()
        self._user_agent: str | None = None
        self._connector = connector or (
            lambda: unix_connect(
                path=self._socket_path,
                open_timeout=self._connect_timeout,
                max_size=max_message_bytes,
                compression=None,
                ping_interval=20,
                ping_timeout=20,
            )
        )

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def user_agent(self) -> str | None:
        return self._user_agent

    async def start(self) -> None:
        if self._runner is None:
            self._stopping = False
            self._runner = asyncio.create_task(self._run(), name="codex-rpc-connection")
            await asyncio.sleep(0)

    async def wait_until_ready(self, wait_seconds: float) -> None:
        try:
            async with asyncio.timeout(wait_seconds):
                await self._ready_event.wait()
        except TimeoutError as exc:
            raise DependencyUnavailable("Codex is unavailable") from exc

    async def stop(self) -> None:
        self._stopping = True
        self._ready = False
        self._ready_event.clear()
        websocket = self._websocket
        if websocket is not None:
            await websocket.close()
        if self._runner is not None:
            self._runner.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._runner
            self._runner = None
        self._fail_pending(DependencyUnavailable("Codex connection closed"))

    async def request(self, method: str, params: Mapping[str, object]) -> object:
        if not self._ready:
            raise DependencyUnavailable("Codex is unavailable")
        return await self._request(method, params)

    async def _request(self, method: str, params: Mapping[str, object]) -> object:
        future: asyncio.Future[object] | None = None
        request_id: int | None = None
        try:
            async with asyncio.timeout(self._request_timeout):
                async with self._pending_limit:
                    loop = asyncio.get_running_loop()
                    future = loop.create_future()
                    async with self._send_lock:
                        websocket = self._websocket
                        if websocket is None:
                            raise DependencyUnavailable("Codex is unavailable")
                        request_id = self._next_id
                        self._next_id += 1
                        self._pending[request_id] = future
                        try:
                            await websocket.send(
                                json.dumps(
                                    {"method": method, "id": request_id, "params": dict(params)},
                                    separators=(",", ":"),
                                )
                            )
                        except (ConnectionClosed, OSError, WebSocketException) as exc:
                            self._pending.pop(request_id, None)
                            raise DependencyUnavailable("Codex is unavailable") from exc
                    return await future
        except TimeoutError as exc:
            if request_id is not None:
                self._pending.pop(request_id, None)
            if future is not None:
                future.cancel()
            raise DependencyTimeout("Codex request timed out") from exc

    async def _run(self) -> None:
        delay = 0.5
        while not self._stopping:
            try:
                websocket = await self._connector()
                try:
                    self._websocket = websocket
                    reader = asyncio.create_task(
                        self._read_messages(websocket), name="codex-rpc-reader"
                    )
                    try:
                        result = _as_object(
                            await self._request(
                                "initialize",
                                {
                                    "clientInfo": {
                                        "name": "llm_wiki_server",
                                        "title": "LLM Wiki Server",
                                        "version": __version__,
                                    }
                                },
                            )
                        )
                        user_agent = result.get("userAgent")
                        if not isinstance(user_agent, str):
                            raise DependencyProtocolError("Invalid initialize response")
                        await websocket.send('{"method":"initialized","params":{}}')
                        self._user_agent = user_agent
                        self._ready = True
                        self._ready_event.set()
                        logger.info("Codex connection ready", extra={"codex_version": user_agent})
                        delay = 0.5
                        await reader
                    finally:
                        reader.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await reader
                finally:
                    await websocket.close()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if not self._stopping:
                    logger.warning(
                        "Codex connection unavailable",
                        extra={"error_type": type(exc).__name__},
                    )
            finally:
                self._ready = False
                self._ready_event.clear()
                self._websocket = None
                self._fail_pending(DependencyUnavailable("Codex connection closed"))
            if not self._stopping:
                await asyncio.sleep(delay + random.uniform(0, delay / 4))
                delay = min(delay * 2, 30)

    async def _read_messages(self, websocket: ClientConnection) -> None:
        try:
            async for raw_message in websocket:
                if not isinstance(raw_message, str):
                    raise DependencyProtocolError("Codex sent a binary message")
                try:
                    message = json.loads(raw_message)
                except json.JSONDecodeError as exc:
                    raise DependencyProtocolError("Codex sent invalid JSON") from exc
                data = _as_object(message)
                request_id = data.get("id")
                if isinstance(request_id, int) and not isinstance(request_id, bool):
                    if "method" in data:
                        await self._reject_server_request(websocket, request_id)
                        continue
                    future = self._pending.pop(request_id, None)
                    if future is None:
                        continue
                    if "error" in data:
                        error = _as_object(data["error"])
                        code = error.get("code")
                        message_text = error.get("message")
                        if not isinstance(code, int) or not isinstance(message_text, str):
                            future.set_exception(DependencyProtocolError("Invalid JSON-RPC error"))
                        else:
                            future.set_exception(RpcRemoteError(code, message_text))
                    elif "result" in data:
                        future.set_result(data["result"])
                    else:
                        future.set_exception(DependencyProtocolError("Invalid JSON-RPC response"))
                    continue
                method = data.get("method")
                if isinstance(method, str):
                    logger.debug(
                        "Ignored Codex notification",
                        extra={"rpc_method": method, "size": len(raw_message)},
                    )
                    continue
                raise DependencyProtocolError("Invalid JSON-RPC message")
        except DependencyProtocolError as exc:
            self._fail_pending(exc)
            raise
        except (ConnectionClosed, OSError, WebSocketException) as exc:
            self._fail_pending(DependencyUnavailable("Codex connection closed"))
            raise DependencyUnavailable("Codex connection closed") from exc
        finally:
            self._ready = False
            self._ready_event.clear()
            self._fail_pending(DependencyUnavailable("Codex connection closed"))

    async def _reject_server_request(self, websocket: ClientConnection, request_id: int) -> None:
        async with self._send_lock:
            await websocket.send(
                json.dumps(
                    {"id": request_id, "error": {"code": -32601, "message": "Method not found"}},
                    separators=(",", ":"),
                )
            )

    def _fail_pending(self, error: Exception) -> None:
        for future in self._pending.values():
            if not future.done():
                future.set_exception(error)
        self._pending.clear()


def _as_object(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DependencyProtocolError("Codex returned an invalid JSON-RPC object")
    return value
