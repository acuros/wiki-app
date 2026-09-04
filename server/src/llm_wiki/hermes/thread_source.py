import builtins
import time
import uuid
from pathlib import Path
from typing import Any, cast

import httpx

from llm_wiki.application.ports import ListThreadsQueryLike
from llm_wiki.domain.errors import (
    DependencyProtocolError,
    DependencyRateLimited,
    DependencyTimeout,
    DependencyUnavailable,
    InvalidThreadQuery,
    ThreadBusy,
    ThreadNotFound,
)
from llm_wiki.domain.models import Conversation, Page, ThreadId, ThreadSummary, TurnSubmission
from llm_wiki.hermes.client import HermesClient, HermesHttpError
from llm_wiki.hermes.mapper import map_conversation, map_summary
from llm_wiki.hermes.run_tracker import RunTracker, TrackedRun

REQUIRED_CAPABILITIES = {
    "session_cwd",
    "session_activity",
    "session_runtime",
    "runs_honor_session_lock",
}


class HermesThreadSource:
    def __init__(
        self,
        client: HermesClient,
        *,
        project_cwd: str,
        run_state_path: Path,
    ) -> None:
        self._client = client
        self._project_cwd = project_cwd
        self._tracker = RunTracker(client, run_state_path)
        self._is_ready = False

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    async def start(self) -> None:
        await self._client.start()
        try:
            payload = await self._client.get("/v1/capabilities")
            features = payload.get("features") if isinstance(payload, dict) else None
            self._is_ready = isinstance(features, dict) and all(
                features.get(name) is True for name in REQUIRED_CAPABILITIES
            )
            if self._is_ready:
                await self._tracker.start()
        except Exception:
            self._is_ready = False

    async def stop(self) -> None:
        await self._tracker.stop()
        await self._client.stop()
        self._is_ready = False

    async def list(self, query: ListThreadsQueryLike) -> Page[ThreadSummary]:
        offset = self._offset(query.cursor)
        payload = await self._call(
            self._client.get,
            "/api/sessions",
            params={
                "limit": query.limit,
                "offset": offset,
                "archived": str(query.archived).lower(),
            },
        )
        data = self._data(payload)
        items = tuple(
            map_summary(
                item,
                locally_active=any(
                    not run.terminal
                    for run in self._tracker.for_session(str(item.get("id") or ""))
                ),
            )
            for item in data
        )
        has_more = payload.get("has_more") is True if isinstance(payload, dict) else False
        return Page(items, str(offset + len(data)) if has_more else None)

    async def read(self, thread_id: ThreadId) -> Conversation:
        session_id = str(thread_id)
        session_payload = await self._call(self._client.get, f"/api/sessions/{session_id}")
        message_payload = await self._call(
            self._client.get,
            f"/api/sessions/{session_id}/messages",
            params={"limit": 500, "order": "oldest"},
        )
        session = session_payload.get("session") if isinstance(session_payload, dict) else None
        if not isinstance(session, dict):
            raise DependencyProtocolError("Hermes omitted the session resource")
        messages = self._data(message_payload)
        self._tracker.reconcile(session_id, messages)
        return map_conversation(session, messages, self._tracker.for_session(session_id))

    async def create(self, message: str) -> TurnSubmission:
        session_payload = await self._call(
            self._client.post,
            "/api/sessions",
            json={"source": "api_server", "cwd": self._project_cwd},
        )
        session = session_payload.get("session") if isinstance(session_payload, dict) else None
        if not isinstance(session, dict) or not isinstance(session.get("id"), str):
            raise DependencyProtocolError("Hermes omitted the new session id")
        return await self._submit(ThreadId(session["id"]), message)

    async def send(self, thread_id: ThreadId, message: str) -> TurnSubmission:
        return await self._submit(thread_id, message)

    async def update_settings(
        self, thread_id: ThreadId, *, model: str | None = None, effort: str | None = None
    ) -> None:
        session_payload = await self._call(self._client.get, f"/api/sessions/{thread_id}")
        session = session_payload.get("session") if isinstance(session_payload, dict) else None
        runtime = session.get("runtime") if isinstance(session, dict) else None
        runtime = runtime if isinstance(runtime, dict) else {}
        selected_model = model or runtime.get("model")
        options = runtime.get("model_options")
        options = dict(options) if isinstance(options, dict) else {}
        if effort is not None:
            options["reasoning_effort"] = effort
        if not isinstance(selected_model, str) or not selected_model:
            raise DependencyProtocolError("Hermes session has no selectable model")
        model_lock: dict[str, Any] = {
            "model": selected_model,
            "model_options": options,
        }
        provider = runtime.get("provider")
        if isinstance(provider, str) and provider:
            model_lock["provider"] = provider
        await self._call(
            self._client.post,
            f"/api/sessions/{thread_id}/model",
            json=model_lock,
        )

    async def _submit(self, thread_id: ThreadId, message: str) -> TurnSubmission:
        idempotency_key = str(uuid.uuid4())
        payload = await self._call(
            self._client.post,
            "/v1/runs",
            json={"session_id": str(thread_id), "input": message},
            headers={"Idempotency-Key": idempotency_key},
        )
        run_id = payload.get("run_id") if isinstance(payload, dict) else None
        if not isinstance(run_id, str) or not run_id:
            raise DependencyProtocolError("Hermes omitted the run id")
        self._tracker.add(
            TrackedRun(
                run_id=run_id,
                session_id=str(thread_id),
                user_message=message,
                created_at=time.time(),
            )
        )
        return TurnSubmission(thread_id, run_id, "in_progress")

    async def _call(self, function: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return await function(*args, **kwargs)
        except HermesHttpError as exc:
            if exc.status == 404:
                raise ThreadNotFound("Hermes session not found") from exc
            if exc.status == 409 or exc.code == "session_busy":
                raise ThreadBusy("Hermes session is busy") from exc
            if exc.status == 429:
                raise DependencyRateLimited("Hermes run limit reached") from exc
            if exc.status in {401, 403, 500, 502, 503}:
                self._is_ready = False
                raise DependencyUnavailable("Hermes is unavailable") from exc
            raise DependencyProtocolError("Hermes rejected the request") from exc
        except httpx.TimeoutException as exc:
            raise DependencyTimeout("Hermes request timed out") from exc
        except httpx.HTTPError as exc:
            self._is_ready = False
            raise DependencyUnavailable("Hermes is unavailable") from exc

    @staticmethod
    def _data(payload: object) -> builtins.list[dict[str, Any]]:
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise DependencyProtocolError("Hermes omitted response data")
        if not all(isinstance(item, dict) for item in payload["data"]):
            raise DependencyProtocolError("Hermes returned invalid response data")
        return cast(builtins.list[dict[str, Any]], payload["data"])

    @staticmethod
    def _offset(cursor: str | None) -> int:
        if cursor is None:
            return 0
        try:
            value = int(cursor)
        except ValueError as exc:
            raise InvalidThreadQuery("Invalid Hermes cursor") from exc
        if value < 0:
            raise InvalidThreadQuery("Invalid Hermes cursor")
        return value
