"""OpenAI-native server-side web search parity tests."""

import json


def test_openai_native_provider_uses_read_only_codex_credential_probe(tmp_path, monkeypatch):
    from plugins.web.openai_native.provider import OpenAINativeWebSearchProvider

    monkeypatch.setattr("anakot_constants.get_anakot_home", lambda: tmp_path)
    provider = OpenAINativeWebSearchProvider()
    assert provider.is_available() is False

    (tmp_path / "auth.json").write_text(
        json.dumps({"credential_pool": {"openai-codex": [{"access_token": "token"}]}}),
        encoding="utf-8",
    )
    assert provider.is_available() is True
    result = provider.search("ignored")
    assert result["success"] is False
    assert "server-side" in result["error"]


def test_codex_openai_native_backend_declares_provider_web_search(monkeypatch):
    import agent.transports.codex as codex_mod
    from agent.transports import get_transport

    monkeypatch.setattr(codex_mod, "_openai_prefers_native_web_search", lambda params: True)
    transport = get_transport("codex_responses")
    result = transport.build_kwargs(
        model="gpt-5.6",
        messages=[{"role": "user", "content": "Search the web."}],
        tools=[
            {"type": "function", "function": {"name": "read_file", "parameters": {}}},
            {"type": "function", "function": {"name": "web_search", "parameters": {}}},
        ],
        is_codex_backend=True,
    )
    tools = result["tools"]
    assert {tool.get("type") for tool in tools} >= {"function", "web_search"}
    assert not any(tool.get("type") == "function" and tool.get("name") == "web_search" for tool in tools)
    assert any(tool == {"type": "web_search"} for tool in tools)
