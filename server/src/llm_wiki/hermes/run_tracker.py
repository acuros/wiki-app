import asyncio
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from llm_wiki.hermes.client import HermesClient, HermesHttpError


@dataclass(slots=True)
class TrackedRun:
    run_id: str
    session_id: str
    user_message: str
    created_at: float
    status: str = "queued"
    commentary: list[str] = field(default_factory=list)
    final_answer: str = ""

    @property
    def terminal(self) -> bool:
        return self.status in {"completed", "failed", "cancelled", "interrupted"}


class RunTracker:
    def __init__(self, client: HermesClient, state_path: Path) -> None:
        self._client = client
        self._state_path = state_path
        self._runs: dict[str, TrackedRun] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def start(self) -> None:
        self._load()
        for run_id in tuple(self._runs):
            self._watch(run_id)

    async def stop(self) -> None:
        tasks = tuple(self._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

    def add(self, run: TrackedRun) -> None:
        self._runs[run.run_id] = run
        self._save()
        self._watch(run.run_id)

    def for_session(self, session_id: str) -> tuple[TrackedRun, ...]:
        return tuple(run for run in self._runs.values() if run.session_id == session_id)

    def reconcile(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        text = "\n".join(
            str(message.get("content") or "")
            for message in messages
            if isinstance(message.get("content"), str)
        )
        removed = False
        for run_id, run in tuple(self._runs.items()):
            if run.session_id != session_id or not run.terminal:
                continue
            if run.user_message in text and (not run.final_answer or run.final_answer in text):
                self._runs.pop(run_id, None)
                removed = True
        if removed:
            self._save()

    def _watch(self, run_id: str) -> None:
        task = self._tasks.get(run_id)
        if task is None or task.done():
            self._tasks[run_id] = asyncio.create_task(self._consume(run_id))

    async def _consume(self, run_id: str) -> None:
        run = self._runs.get(run_id)
        if run is None:
            return
        try:
            while not run.terminal:
                try:
                    status = await self._client.get(f"/v1/runs/{run_id}")
                    if isinstance(status, dict):
                        self._apply_status(run, status)
                        self._save()
                    if run.terminal:
                        break
                    async for event in self._client.stream_run(run_id):
                        self._apply(run, event)
                        self._save()
                    if not run.terminal:
                        await asyncio.sleep(1)
                except HermesHttpError as exc:
                    if exc.status == 404:
                        run.status = "interrupted"
                        run.commentary.append("Hermes 실행 상태를 더 이상 찾을 수 없습니다.")
                        self._save()
                        break
                    await asyncio.sleep(1)
                except Exception:
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise
        except HermesHttpError as exc:
            if exc.status == 404:
                run.status = "interrupted"
                run.commentary.append("Hermes 실행 상태를 더 이상 찾을 수 없습니다.")
                self._save()
        except Exception:
            return
        finally:
            self._tasks.pop(run_id, None)

    @staticmethod
    def _apply(run: TrackedRun, event: dict[str, Any]) -> None:
        name = str(event.get("event") or "")
        if name == "message.delta":
            delta = event.get("delta")
            if isinstance(delta, str):
                run.final_answer += delta
        elif name == "reasoning.available":
            text = event.get("text")
            if isinstance(text, str) and text:
                run.commentary.append(text)
        elif name == "tool.started":
            tool = str(event.get("tool") or "tool")
            preview = str(event.get("preview") or "").strip()
            run.commentary.append(f"{tool}: {preview}" if preview else tool)
        elif name == "approval.request":
            run.status = "waiting_for_approval"
            run.commentary.append("Hermes가 도구 실행 승인을 기다리고 있습니다.")
        elif name == "run.completed":
            run.status = "completed"
            output = event.get("output")
            if isinstance(output, str):
                run.final_answer = output
        elif name in {"run.failed", "run.cancelled", "run.interrupted"}:
            run.status = name.removeprefix("run.")
            error = event.get("error")
            if isinstance(error, str) and error:
                run.commentary.append(error)
        elif name == "run.started":
            run.status = "running"

    @classmethod
    def _apply_status(cls, run: TrackedRun, status: dict[str, Any]) -> None:
        state = status.get("status")
        if isinstance(state, str):
            run.status = state
        output = status.get("output")
        if isinstance(output, str) and output:
            run.final_answer = output
        error = status.get("error")
        if isinstance(error, str) and error and error not in run.commentary:
            run.commentary.append(error)

    def _load(self) -> None:
        try:
            payload = json.loads(self._state_path.read_text(encoding="utf-8"))
            values = payload.get("runs", []) if isinstance(payload, dict) else []
            self._runs = {
                run.run_id: run
                for item in values
                if isinstance(item, dict)
                for run in [TrackedRun(**item)]
            }
        except (OSError, ValueError, TypeError):
            self._runs = {}

    def _save(self) -> None:
        temporary: Path | None = None
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(
                {"runs": [asdict(run) for run in self._runs.values()]},
                ensure_ascii=False,
            )
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self._state_path.parent,
                prefix=f".{self._state_path.name}.",
                delete=False,
            ) as output:
                temporary = Path(output.name)
                output.write(payload)
            os.chmod(temporary, 0o600)
            os.replace(temporary, self._state_path)
            temporary = None
        except OSError:
            # A run was already accepted by Hermes. Journal I/O must not turn
            # that acceptance into a retryable HTTP failure and duplicate it.
            return
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
