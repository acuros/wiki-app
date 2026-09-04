import uuid
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from llm_wiki.domain.errors import (
    DependencyProtocolError,
    DependencyRateLimited,
    DependencyTimeout,
    DependencyUnavailable,
    InvalidMessage,
    InvalidThreadQuery,
    ThreadBusy,
    ThreadNotFound,
)


@dataclass(frozen=True, slots=True)
class HttpError(Exception):
    status: int
    code: str
    message: str


AuthenticationRequired = HttpError(401, "authentication_required", "Authentication is required.")
Forbidden = HttpError(403, "forbidden", "Access is forbidden.")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def _response(request: Request, status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "request_id": _request_id(request)}},
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HttpError)
    async def handle_http_error(request: Request, exc: HttpError) -> JSONResponse:
        return _response(request, exc.status, exc.code, exc.message)

    @app.exception_handler(InvalidThreadQuery)
    async def handle_invalid_query(request: Request, _exc: InvalidThreadQuery) -> JSONResponse:
        return _response(request, 400, "invalid_request", "The request is invalid.")

    @app.exception_handler(InvalidMessage)
    async def handle_invalid_message(request: Request, _exc: InvalidMessage) -> JSONResponse:
        return _response(request, 400, "invalid_request", "The request is invalid.")

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, _exc: RequestValidationError) -> JSONResponse:
        return _response(request, 400, "invalid_request", "The request is invalid.")

    @app.exception_handler(ThreadNotFound)
    async def handle_not_found(request: Request, _exc: ThreadNotFound) -> JSONResponse:
        return _response(request, 404, "thread_not_found", "The requested thread was not found.")

    @app.exception_handler(ThreadBusy)
    async def handle_thread_busy(request: Request, _exc: ThreadBusy) -> JSONResponse:
        return _response(request, 409, "thread_busy", "The thread already has an active turn.")

    @app.exception_handler(DependencyUnavailable)
    async def handle_unavailable(request: Request, _exc: DependencyUnavailable) -> JSONResponse:
        return _response(
            request, 503, "dependency_unavailable", "The conversation source is unavailable."
        )

    @app.exception_handler(DependencyTimeout)
    async def handle_timeout(request: Request, _exc: DependencyTimeout) -> JSONResponse:
        return _response(request, 504, "dependency_timeout", "The conversation source timed out.")

    @app.exception_handler(DependencyRateLimited)
    async def handle_rate_limited(
        request: Request, _exc: DependencyRateLimited
    ) -> JSONResponse:
        return _response(
            request,
            429,
            "dependency_rate_limited",
            "The conversation source is busy. Try again shortly.",
        )

    @app.exception_handler(DependencyProtocolError)
    async def handle_protocol(request: Request, _exc: DependencyProtocolError) -> JSONResponse:
        return _response(
            request,
            502,
            "dependency_protocol_error",
            "The conversation source returned an invalid response.",
        )
