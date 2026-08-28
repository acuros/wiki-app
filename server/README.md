# LLM Wiki Server

로컬 Codex app-server의 사용자 thread를 읽기 전용 HTTP API로 제공한다.

## 개발

Python 3.14와 `uv`가 필요하다.

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy
```

## 실행

Codex app-server는 별도 process로 먼저 실행한다.

```bash
/usr/lib/chatgpt/resources/codex app-server \
  --listen "unix://${XDG_RUNTIME_DIR}/llm-wiki-codex.sock"
```

허용할 Tailscale 로그인 계정을 설정하고 localhost에서 Web API를 실행한다.

```bash
export LLM_WIKI_ALLOWED_TAILSCALE_USERS='user@example.com'
uv run uvicorn llm_wiki.bootstrap:create_app --factory --host 127.0.0.1 --port 8787 --workers 1
```

API endpoint:

- `GET /api/v1/threads`
- `GET /api/v1/threads/{thread_id}`
- `GET /health/live`
- `GET /health/ready`

`/api/v1/*` 요청에는 Tailscale Serve가 설정하는 `Tailscale-User-Login` header가 필요하다.
