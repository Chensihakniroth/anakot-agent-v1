"""Codex account service-tier negotiation contracts."""

from types import SimpleNamespace


def test_service_tier_catalog_maps_fast_to_priority():
    from agent.codex_service_tiers import _advertised_tiers

    assert _advertised_tiers({"service_tiers": [{"id": "priority"}]}) == {"priority"}
    assert _advertised_tiers({"additional_speed_tiers": ["fast", "standard"]}) == {"priority", "standard"}
    assert _advertised_tiers({"service_tiers": []}) == set()


def test_unsupported_priority_is_removed(monkeypatch):
    import agent.codex_service_tiers as tiers

    monkeypatch.setattr(tiers, "_tiers_for_model", lambda *args: frozenset())
    agent = SimpleNamespace(provider="openai-codex", api_mode="codex_responses", model="gpt-5.6",
                            base_url="https://chatgpt.com/backend-api/codex", api_key="token")
    overrides = {"service_tier": "priority"}
    tiers.negotiate_request_tier(agent, overrides)
    assert overrides == {}


def test_unknown_priority_is_preserved(monkeypatch):
    import agent.codex_service_tiers as tiers

    monkeypatch.setattr(tiers, "_tiers_for_model", lambda *args: None)
    agent = SimpleNamespace(provider="openai-codex", api_mode="codex_responses", model="gpt-5.6",
                            base_url="https://chatgpt.com/backend-api/codex", api_key="token")
    overrides = {"service_tier": "priority"}
    tiers.negotiate_request_tier(agent, overrides)
    assert overrides == {"service_tier": "priority"}
