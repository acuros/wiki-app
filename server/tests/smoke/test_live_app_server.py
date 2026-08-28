import asyncio
import contextlib
import os

import pytest
from anyio import Path as AsyncPath

from llm_wiki.application.thread_queries import ListThreadsQuery
from llm_wiki.codex.rpc_client import CodexRpcClient
from llm_wiki.codex.thread_source import CodexThreadSource

EXECUTABLE_ENV = "LLM_WIKI_LIVE_CODEX_EXECUTABLE"


@pytest.mark.skipif(
    not os.environ.get(EXECUTABLE_ENV), reason="live Codex executable not configured"
)
async def test_current_app_server_can_list_and_read_threads() -> None:
    executable = os.environ[EXECUTABLE_ENV]
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    socket_path = f"{runtime_dir}/llm-wiki-codex-test-{os.getpid()}.sock"
    async_socket_path = AsyncPath(socket_path)
    process = await asyncio.create_subprocess_exec(
        executable,
        "app-server",
        "--listen",
        f"unix://{socket_path}",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    client = CodexRpcClient(socket_path, connect_timeout=1, request_timeout=30)
    try:
        async with asyncio.timeout(5):
            while not await async_socket_path.exists():
                if process.returncode is not None:
                    pytest.fail("Codex app-server exited before creating its socket")
                await asyncio.sleep(0.01)
        await client.start()
        await client.wait_until_ready(5)
        source = CodexThreadSource(client)
        page = await source.list(ListThreadsQuery(limit=1))
        if page.items:
            conversation = await source.read(page.items[0].id)
            assert conversation.summary.id == page.items[0].id
    finally:
        await client.stop()
        if process.returncode is None:
            process.terminate()
            with contextlib.suppress(TimeoutError):
                async with asyncio.timeout(5):
                    await process.wait()
            if process.returncode is None:
                process.kill()
                await process.wait()
        with contextlib.suppress(FileNotFoundError):
            os.unlink(socket_path)
