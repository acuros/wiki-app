# LLM Wiki Server

로컬 Hermes Gateway의 사용자 대화를 조회하고 메시지를 보낼 수 있는 HTTP API를 제공한다.

## 개발

Python 3.14와 `uv`가 필요하다.

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy
```

## 실행

Hermes Gateway의 API server를 loopback에서 먼저 실행한다.

`~/.hermes/config.yaml`에는 다음 설정을 둔다.

```yaml
gateway:
  api_server:
    enabled: true
    host: 127.0.0.1
    port: 8642
```

`deploy/hermes-api.env.example`을 참고해 mode `0600`의
`~/.config/llm-wiki/hermes-api.env`를 만들고, Hermes Gateway와 Wiki Web systemd unit이
같은 파일을 읽게 한다. 브라우저가 Hermes API를 직접 호출하지 않으므로 CORS는 설정하지 않는다.

```bash
hermes gateway
```

허용할 Tailscale 로그인 계정을 설정하고 localhost에서 Web API를 실행한다.

```bash
export LLM_WIKI_ALLOWED_TAILSCALE_USERS='user@example.com'
export LLM_WIKI_HERMES_API_KEY='same-value-as-API_SERVER_KEY'
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
진행 상태와 최종 답변을 확인한다. 새 대화와 기존 대화 실행은 Hermes Sessions/Runs API를
사용하며, 위험한 도구 실행에는 Hermes의 unattended approval 정책이 적용된다.
