from typing import Annotated

from fastapi import Header, Request

from llm_wiki.web.errors import AuthenticationRequired, Forbidden


async def require_tailscale_user(
    request: Request,
    login: Annotated[str | None, Header(alias="Tailscale-User-Login")] = None,
) -> None:
    if login is None:
        raise AuthenticationRequired
    if login not in request.app.state.allowed_users:
        raise Forbidden
