"""OmniRouters wiring contracts.

Two properties earn an assertion each, because both are load-bearing and both
fail *silently* otherwise — a chat request that 401s or a picker row that never
appears looks like "the provider just isn't set up" to the user:

1. Identity is consistent across the two independent alias tables
   (``anakot_cli.providers.ALIASES`` and ``anakot_cli.models``'s
   ``_PROVIDER_ALIASES``). They are separate dicts, so adding an alias to only
   one makes ``--provider omni`` resolve while ``/model omni:<model>`` silently
   falls through to the current provider.
2. The profile sends no reasoning field. OmniRouters documents ``extra_body`` as
   a generic provider-extension container rather than a reasoning schema, so a
   blind ``extra_body.reasoning`` risks a 400 on routes that reject unknown keys.
   The gate flag is passed as the transport passes it, including ``False``.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def omnirouters_profile():
    import model_tools  # noqa: F401  (plugin discovery registers the profile)
    import providers

    profile = providers.get_provider_profile("omnirouters")
    assert profile is not None, "omnirouters provider profile must be registered"
    return profile


def test_alias_tables_agree():
    """``omni`` must reach the provider through every alias consumer."""
    from anakot_cli.providers import get_provider, normalize_provider
    from anakot_cli.models import parse_model_input

    for alias in ("omnirouters", "omni", "omni-router", "omnirouter", "omniroute"):
        assert normalize_provider(alias) == "omnirouters", f"runtime alias {alias!r} unresolved"
        assert get_provider(alias) is not None, f"overlay resolution failed for {alias!r}"
        provider, model = parse_model_input(f"{alias}:gpt-4o", "openrouter")
        assert (provider, model) == ("omnirouters", "gpt-4o"), f"/model parsing failed for {alias!r}"


def test_runtime_provider_resolves_openai_chat_endpoint():
    """The profile and the overlay must agree on one endpoint + wire, or the
    resolver picks a base_url the profile never authenticated against."""
    import model_tools  # noqa: F401
    from anakot_cli.providers import get_provider
    from providers import get_provider_profile

    profile = get_provider_profile("omnirouters")
    pdef = get_provider("omnirouters")
    assert pdef.transport == "openai_chat"
    assert pdef.base_url == profile.base_url == "https://omnirouters.com/v1"
    assert "OMNIROUTERS_API_KEY" in profile.env_vars
    assert "OMNIROUTE_API_KEY" in profile.env_vars
    assert "OMNI_API_KEY" in profile.env_vars


def test_api_key_env_var_resolves_credentials(monkeypatch):
    """The documented env var (and its natural aliases) must resolve."""
    import model_tools  # noqa: F401
    from anakot_cli.auth import resolve_api_key_provider_credentials

    monkeypatch.delenv("OMNIROUTE_BASE_URL", raising=False)
    monkeypatch.delenv("OMNIROUTERS_BASE_URL", raising=False)
    monkeypatch.delenv("OMNI_BASE_URL", raising=False)
    monkeypatch.setenv("OMNIROUTERS_API_KEY", "sk-omni-test")
    creds = resolve_api_key_provider_credentials("omnirouters")
    assert creds["api_key"] == "sk-omni-test"

    monkeypatch.delenv("OMNIROUTERS_API_KEY", raising=False)
    monkeypatch.setenv("OMNIROUTE_API_KEY", "sk-omni-test-2")
    monkeypatch.setenv("OMNIROUTE_BASE_URL", "http://localhost:20128/v1")
    creds2 = resolve_api_key_provider_credentials("omnirouters")
    assert creds2["api_key"] == "sk-omni-test-2"
    assert creds2["base_url"] == "http://localhost:20128/v1"


def test_catalog_is_live_not_hardcoded(omnirouters_profile):
    """The catalog is account-scoped, so a shipped model list would point the
    picker at models this key cannot reach. fetch_models() must be the source."""
    from anakot_cli.models import CANONICAL_PROVIDERS

    entry = next(p for p in CANONICAL_PROVIDERS if p.slug == "omnirouters")
    assert entry.label == "OmniRouters"
    assert omnirouters_profile.fallback_models == ()
    assert omnirouters_profile.supports_model_listing is True
    assert omnirouters_profile.models_url == ""  # -> base_url + "/models"


def test_no_reasoning_field_on_the_wire(omnirouters_profile):
    """OmniRouters has no declared reasoning schema — omit the field entirely."""
    from agent.transports.chat_completions import ChatCompletionsTransport

    build = ChatCompletionsTransport().build_kwargs
    for supports_reasoning in (False, True):
        kwargs = build(
            model="gpt-4o",
            messages=[{"role": "user", "content": "ping"}],
            tools=None,
            provider_profile=omnirouters_profile,
            provider_name="omnirouters",
            base_url="https://omnirouters.com/v1",
            reasoning_config={"enabled": True, "effort": "high"},
            supports_reasoning=supports_reasoning,
        )
        assert "reasoning" not in (kwargs.get("extra_body") or {}), (
            f"OmniRouters must not receive extra_body.reasoning (supports_reasoning={supports_reasoning})"
        )
        assert "reasoning_effort" not in kwargs
