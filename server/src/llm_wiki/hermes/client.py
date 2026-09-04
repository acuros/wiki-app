from collections.abc import AsyncIterator, Mapping
from typing import Any

import httpx


class HermesHttpError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class HermesClient:
    def __init__(self, base_url: str, api_key: str, *, timeout: float = 30) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=httpx.Timeout(self._timeout, connect=5),
            )

    async def stop(self) -> None:
        client, self._client = self._client, None
        if client is not None:
            await client.aclose()

    async def get(
        self,
        path: str,
        *,
        params: Mapping[str, str | int | float | bool | None] | None = None,
    ) -> Any:
        response = await self._require_client().get(path, params=params)
        return self._decode(response)

    async def post(
        self,
        path: str,
        *,
        json: Mapping[str, object],
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        response = await self._require_client().post(path, json=json, headers=headers)
        return self._decode(response)

    async def stream_run(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        client = self._require_client()
        async with client.stream("GET", f"/v1/runs/{run_id}/events", timeout=None) as response:
            if response.is_error:
                self._decode(response)
            event_name: str | None = None
            data_lines: list[str] = []
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    event_name = line[6:].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[5:].strip())
                elif not line and data_lines:
                    payload = self._decode_json_text("\n".join(data_lines))
                    if isinstance(payload, dict):
                        payload.setdefault("event", event_name or payload.get("event") or "message")
                        yield payload
                    event_name = None
                    data_lines = []

    def _require_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("HermesClient.start() must be called first")
        return self._client

    @classmethod
    def _decode(cls, response: httpx.Response) -> Any:
        try:
            payload = response.json()
        except ValueError as exc:
            raise HermesHttpError(response.status_code, "invalid_response", "Invalid JSON") from exc
        if response.is_error:
            error = payload.get("error") if isinstance(payload, dict) else None
            error = error if isinstance(error, dict) else {}
            raise HermesHttpError(
                response.status_code,
                str(error.get("code") or "hermes_error"),
                str(error.get("message") or "Hermes request failed"),
            )
        return payload

    @staticmethod
    def _decode_json_text(value: str) -> Any:
        import json

        try:
            return json.loads(value)
        except ValueError:
            return None
