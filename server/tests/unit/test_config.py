from llm_wiki.config import Settings


def test_default_codex_socket_uses_user_runtime_directory(monkeypatch) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")

    settings = Settings(allowed_tailscale_users="allowed@example.com")

    assert settings.codex_socket == "/run/user/1000/llm-wiki-codex.sock"


def test_codex_socket_falls_back_to_tmp_without_runtime_directory(monkeypatch) -> None:
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)

    settings = Settings(allowed_tailscale_users="allowed@example.com")

    assert settings.codex_socket == "/tmp/llm-wiki-codex.sock"
