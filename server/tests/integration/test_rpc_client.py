import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from websockets.asyncio.server import ServerConnection, unix_serve

from llm_wiki.codex.rpc_client import CodexRpcClient
from llm_wiki.domain.errors import (
    DependencyProtocolError,
    DependencyTimeout,
    DependencyUnavailable,
)


async def wait_until_ready(client: CodexRpcClient) -> None:
    await client.wait_until_ready(2)


def decode(message: str | bytes) -> dict[str, Any]:
    assert isinstance(message, str)
    value = json.loads(message)
    assert isinstance(value, dict)
    return value


async def handshake(websocket: ServerConnection, messages: list[dict[str, Any]]) -> None:
    initialize = decode(await websocket.recv())
    messages.append(initialize)
    assert initialize["method"] == "initialize"
    assert initialize["params"]["clientInfo"]["name"] == "llm_wiki_server"
    await websocket.send(
        json.dumps(
            {
                "id": initialize["id"],
                "result": {
                    "userAgent": "codex-cli/test",
                    "codexHome": "/tmp/codex-home",
                    "platformFamily": "unix",
                    "platformOs": "linux",
                },
            }
        )
    )
    initialized = decode(await websocket.recv())
    messages.append(initialized)
    assert initialized == {"method": "initialized", "params": {}}


async def test_handshake_out_of_order_responses_notification_and_server_request(
    tmp_path: Path,
) -> None:
    socket_path = tmp_path / "codex.sock"
    messages: list[dict[str, Any]] = []

    async def handler(websocket: ServerConnection) -> None:
        await handshake(websocket, messages)
        first = decode(await websocket.recv())
        second = decode(await websocket.recv())
        await websocket.send(json.dumps({"method": "thread/status/changed", "params": {}}))
        await websocket.send(json.dumps({"id": 999, "method": "approval/request", "params": {}}))
        rejection = decode(await websocket.recv())
        messages.append(rejection)
        await websocket.send(json.dumps({"id": second["id"], "result": {"value": "second"}}))
        await websocket.send(json.dumps({"id": first["id"], "result": {"value": "first"}}))
        await websocket.wait_closed()

    server = await unix_serve(handler, path=str(socket_path))
    client = CodexRpcClient(str(socket_path), request_timeout=1)
    await client.start()
    try:
        await wait_until_ready(client)
        first_task = asyncio.create_task(client.request("first", {}))
        second_task = asyncio.create_task(client.request("second", {}))
        assert await second_task == {"value": "second"}
        assert await first_task == {"value": "first"}
        assert client.user_agent == "codex-cli/test"
        assert messages[0]["method"] == "initialize"
        assert messages[1]["method"] == "initialized"
        assert messages[2] == {
            "id": 999,
            "error": {"code": -32601, "message": "Method not found"},
        }
    finally:
        await client.stop()
        server.close()
        await server.wait_closed()


async def test_request_timeout(tmp_path: Path) -> None:
    socket_path = tmp_path / "timeout.sock"
    request_seen = asyncio.Event()

    async def handler(websocket: ServerConnection) -> None:
        await handshake(websocket, [])
        await websocket.recv()
        request_seen.set()
        await websocket.wait_closed()

    server = await unix_serve(handler, path=str(socket_path))
    client = CodexRpcClient(str(socket_path), request_timeout=0.05)
    await client.start()
    try:
        await wait_until_ready(client)
        with pytest.raises(DependencyTimeout):
            await client.request("slow", {})
        assert request_seen.is_set()
    finally:
        await client.stop()
        server.close()
        await server.wait_closed()


async def test_disconnect_fails_pending_request_and_clears_readiness(tmp_path: Path) -> None:
    socket_path = tmp_path / "disconnect.sock"

    async def handler(websocket: ServerConnection) -> None:
        await handshake(websocket, [])
        await websocket.recv()
        await websocket.close()

    server = await unix_serve(handler, path=str(socket_path))
    client = CodexRpcClient(str(socket_path), request_timeout=1)
    await client.start()
    try:
        await wait_until_ready(client)
        with pytest.raises(DependencyUnavailable):
            await client.request("disconnect", {})
        assert not client.is_ready
    finally:
        await client.stop()
        server.close()
        await server.wait_closed()


async def test_max_pending_applies_backpressure(tmp_path: Path) -> None:
    socket_path = tmp_path / "backpressure.sock"
    first_seen = asyncio.Event()
    second_arrived_early = False

    async def handler(websocket: ServerConnection) -> None:
        nonlocal second_arrived_early
        await handshake(websocket, [])
        first = decode(await websocket.recv())
        first_seen.set()
        try:
            async with asyncio.timeout(0.05):
                await websocket.recv()
            second_arrived_early = True
        except TimeoutError:
            pass
        await websocket.send(json.dumps({"id": first["id"], "result": {"order": 1}}))
        second = decode(await websocket.recv())
        await websocket.send(json.dumps({"id": second["id"], "result": {"order": 2}}))
        await websocket.wait_closed()

    server = await unix_serve(handler, path=str(socket_path))
    client = CodexRpcClient(str(socket_path), request_timeout=1, max_pending=1)
    await client.start()
    try:
        await wait_until_ready(client)
        first_task = asyncio.create_task(client.request("first", {}))
        await first_seen.wait()
        second_task = asyncio.create_task(client.request("second", {}))
        assert await first_task == {"order": 1}
        assert await second_task == {"order": 2}
        assert not second_arrived_early
    finally:
        await client.stop()
        server.close()
        await server.wait_closed()


async def test_reconnect_performs_a_new_handshake(tmp_path: Path) -> None:
    socket_path = tmp_path / "reconnect.sock"
    connection_count = 0
    second_connection = asyncio.Event()

    async def handler(websocket: ServerConnection) -> None:
        nonlocal connection_count
        connection_count += 1
        await handshake(websocket, [])
        if connection_count == 1:
            await websocket.close()
            return
        second_connection.set()
        await websocket.wait_closed()

    server = await unix_serve(handler, path=str(socket_path))
    client = CodexRpcClient(str(socket_path), request_timeout=1)
    await client.start()
    try:
        async with asyncio.timeout(2):
            await second_connection.wait()
        await wait_until_ready(client)
        assert connection_count == 2
        assert client.is_ready
    finally:
        await client.stop()
        server.close()
        await server.wait_closed()


async def test_protocol_error_is_propagated_to_pending_request(tmp_path: Path) -> None:
    socket_path = tmp_path / "protocol.sock"

    async def handler(websocket: ServerConnection) -> None:
        await handshake(websocket, [])
        await websocket.recv()
        await websocket.send("not-json")
        await websocket.wait_closed()

    server = await unix_serve(handler, path=str(socket_path))
    client = CodexRpcClient(str(socket_path), request_timeout=1)
    await client.start()
    try:
        await wait_until_ready(client)
        with pytest.raises(DependencyProtocolError):
            await client.request("invalid", {})
    finally:
        await client.stop()
        server.close()
        await server.wait_closed()
