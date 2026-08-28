import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Protocol, cast

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from llm_wiki.application.ports import ThreadSource
from llm_wiki.application.thread_commands import ThreadCommandService
from llm_wiki.application.thread_queries import ThreadQueryService
from llm_wiki.codex.rpc_client import CodexRpcClient
from llm_wiki.codex.thread_source import CodexThreadSource
from llm_wiki.config import Settings
from llm_wiki.logging_config import configure_logging
from llm_wiki.web.api import router
from llm_wiki.web.errors import install_error_handlers


class ManagedThreadSource(ThreadSource, Protocol):
    @property
    def is_ready(self) -> bool: ...

    async def start(self) -> None: ...

    async def stop(self) -> None: ...


def create_app(
    settings: Settings | None = None,
    source: ManagedThreadSource | None = None,
) -> FastAPI:
    settings = settings or Settings()  # type: ignore[call-arg]
    if source is None:
        client = CodexRpcClient(
            settings.codex_socket,
            connect_timeout=settings.codex_connect_timeout_seconds,
            request_timeout=settings.codex_request_timeout_seconds,
            max_pending=settings.codex_max_pending_requests,
            max_message_bytes=settings.codex_max_message_bytes,
        )
        source = CodexThreadSource(client)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        assert source is not None
        await source.start()
        try:
            yield
        finally:
            await source.stop()

    configure_logging(settings.log_level)
    app = FastAPI(title="LLM Wiki API", version="1.0.0", lifespan=lifespan)
    app.state.allowed_users = settings.allowed_users
    thread_source = cast(ThreadSource, source)
    app.state.thread_query_service = ThreadQueryService(thread_source)
    app.state.thread_command_service = ThreadCommandService(thread_source)
    app.state.readiness = source

    @app.middleware("http")
    async def request_id_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request.state.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        started_at = time.monotonic()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        route = request.scope.get("route")
        route_template = getattr(route, "path", "unmatched")
        logging.getLogger("llm_wiki.http").info(
            "HTTP request completed",
            extra={
                "request_id": request.state.request_id,
                "http_method": request.method,
                "route": route_template,
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - started_at) * 1000, 3),
            },
        )
        return response

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    async def ready() -> JSONResponse:
        if app.state.readiness.is_ready:
            return JSONResponse({"status": "ready"})
        return JSONResponse({"status": "not_ready"}, status_code=503)

    install_error_handlers(app)
    app.include_router(router)
    return app
