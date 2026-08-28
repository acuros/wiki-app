# LLM Wiki Server

로컬 Codex app-server의 사용자 thread를 조회하고 메시지를 보낼 수 있는 HTTP API를 제공한다.

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

- `GET /api/v1/threads` (기본 20개, cursor pagination)
- `POST /api/v1/threads` (새 thread 생성과 첫 turn 시작)
- `GET /api/v1/threads/{thread_id}`
- `POST /api/v1/threads/{thread_id}/messages` (기존 thread의 새 turn 시작)
- `GET /health/live`
- `GET /health/ready`

`/api/v1/*` 요청에는 Tailscale Serve가 설정하는 `Tailscale-User-Login` header가 필요하다.
메시지 전송 endpoint는 `202 Accepted`를 반환한다. 클라이언트는 thread 상세 조회를 반복해
진행 상태와 최종 답변을 확인한다. 새 thread 시작과 기존 thread 재개에는 Codex의
`approvalsReviewer="auto_review"` 설정을 사용한다.
