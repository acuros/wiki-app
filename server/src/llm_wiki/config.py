import os
from functools import cached_property

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_codex_socket() -> str:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    return f"{runtime_dir}/llm-wiki-codex.sock"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LLM_WIKI_", extra="ignore")

    codex_socket: str = Field(default_factory=_default_codex_socket)
    http_host: str = "127.0.0.1"
    http_port: int = Field(default=8787, ge=1, le=65535)
    allowed_tailscale_users: str
    codex_connect_timeout_seconds: float = Field(default=5, gt=0)
    codex_request_timeout_seconds: float = Field(default=30, gt=0)
    codex_max_pending_requests: int = Field(default=32, ge=1)
    codex_max_message_bytes: int = Field(default=67_108_864, ge=1024)
    log_level: str = "INFO"

    @field_validator("http_host")
    @classmethod
    def localhost_only(cls, value: str) -> str:
        if value != "127.0.0.1":
            raise ValueError("LLM Wiki must bind to 127.0.0.1")
        return value

    @field_validator("allowed_tailscale_users")
    @classmethod
    def non_empty_allowlist(cls, value: str) -> str:
        if not any(part.strip() for part in value.split(",")):
            raise ValueError("At least one Tailscale user is required")
        return value

    @cached_property
    def allowed_users(self) -> frozenset[str]:
        return frozenset(
            part.strip() for part in self.allowed_tailscale_users.split(",") if part.strip()
        )
