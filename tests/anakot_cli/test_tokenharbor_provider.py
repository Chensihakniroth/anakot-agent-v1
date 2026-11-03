"""Tests for Token Harbor provider support (universal API gateway).

Token Harbor (``tokenharbor.ai``) is a single OpenAI-compatible endpoint that
routes one universal key to 16+ model vendors. It is wired in as a built-in
overlay provider, following the same pattern as ``tencent-tokenhub`` and
``nebius-token-factory`` (no plugin dir, resolved via ``ANAKOT_OVERLAYS`` + the
auth registry + the static model catalog).
"""

import os

import pytest

from anakot_cli.auth import (
    PROVIDER_REGISTRY,
    resolve_api_key_provider_credentials,
    resolve_provider,
    get_api_key_provider_status,
)
from anakot_cli.models import (
    _PROVIDER_MODELS,
    CANONICAL_PROVIDERS,
    get_default_model_for_provider,
)
from anakot_cli.models_catalog_static import PROVIDER_GROUPS
from anakot_cli.model_normalize import (
    _LOWERCASE_MODEL_PROVIDERS,
    _MATCHING_PREFIX_STRIP_PROVIDERS,
    normalize_model_for_provider,
)
from anakot_cli.providers import ANAKOT_OVERLAYS, normalize_provider


# Other provider env vars to clear during auto-detection tests
_OTHER_PROVIDER_KEYS = (
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY",
    "GOOGLE_API_KEY", "GEMINI_API_KEY", "DASHSCOPE_API_KEY",
    "XAI_API_KEY", "KIMI_API_KEY", "KILOCODE_API_KEY",
    "MINIMAX_API_KEY", "HF_TOKEN", "GLM_API_KEY", "ZAI_API_KEY",
    "OPENROUTER_API_KEY", "COPILOT_GITHUB_TOKEN", "TOKENHUB_API_KEY",
)


# ---------------------------------------------------------------------------
# Provider registry + overlay metadata
# ---------------------------------------------------------------------------

class TestTokenHarborRegistryAndOverlay:
    def test_overlay_registered(self):
        assert "tokenharbor" in ANAKOT_OVERLAYS
        overlay = ANAKOT_OVERLAYS["tokenharbor"]
        assert overlay.transport == "openai_chat"
        assert overlay.base_url_override == "https://tokenharbor.ai/v1"
        assert overlay.base_url_env_var == "TOKENHARBOR_BASE_URL"
        assert "TOKENHARBOR_API_KEY" in overlay.extra_env_vars

    def test_provider_registry_present(self):
        assert "tokenharbor" in PROVIDER_REGISTRY
        p = PROVIDER_REGISTRY["tokenharbor"]
        assert p.inference_base_url == "https://tokenharbor.ai/v1"
        assert "TOKENHARBOR_API_KEY" in p.api_key_env_vars
        assert p.auth_type == "api_key"

    def test_resolve_provider(self):
        assert normalize_provider("tokenharbor") == "tokenharbor"
        # known aliases
        assert normalize_provider("tencent") == "tencent-tokenhub"
        assert normalize_provider("tokenhub") == "tencent-tokenhub"


# ---------------------------------------------------------------------------
# Provider catalog + picker surfaces
# ---------------------------------------------------------------------------

class TestTokenHarborCatalog:
    def test_canonical_provider(self):
        slugs = {e.slug for e in CANONICAL_PROVIDERS}
        assert "tokenharbor" in slugs
        entry = next(e for e in CANONICAL_PROVIDERS if e.slug == "tokenharbor")
        assert "Token Harbor" in entry.label
        assert "Tencent Hy" != entry.label or "16+" in entry.label

    def test_provider_group(self):
        assert "tokenharbor" not in PROVIDER_GROUPS

    def test_static_model_catalog(self):
        assert "tokenharbor" in _PROVIDER_MODELS
        assert len(_PROVIDER_MODELS["tokenharbor"]) >= 1
        # a representative live-discoverable model is present
        assert "claude-opus-5.5" in _PROVIDER_MODELS["tokenharbor"]

    def test_default_model(self):
        assert get_default_model_for_provider("tokenharbor") == "claude-opus-5.5"


# ---------------------------------------------------------------------------
# Credential resolution + picker status
# ---------------------------------------------------------------------------

class TestTokenHarborCredentials:
    def test_resolve_api_key_credentials(self, monkeypatch):
        monkeypatch.setenv("TOKENHARBOR_API_KEY", "«redacted:sk-th…»")
        monkeypatch.delenv("TOKENHARBOR_BASE_URL", raising=False)
        creds = resolve_api_key_provider_credentials("tokenharbor")
        assert creds["api_key"] == "«redacted:sk-th…»"
        assert creds["base_url"] == "https://tokenharbor.ai/v1"

    def test_configured_status_only_when_key_present(self, monkeypatch):
        monkeypatch.delenv("TOKENHARBOR_API_KEY", raising=False)
        status = get_api_key_provider_status("tokenharbor")
        assert not status["configured"]

    def test_openrouter_key_does_not_make_tokenharbor_configured(self, monkeypatch):
        monkeypatch.delenv("TOKENHARBOR_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
        assert not get_api_key_provider_status("tokenharbor")["configured"]


# ---------------------------------------------------------------------------
# Model identity rules
# ---------------------------------------------------------------------------

class TestTokenHarborModelIdentity:
    def test_not_in_prefix_strip_set(self):
        assert "tokenharbor" not in _MATCHING_PREFIX_STRIP_PROVIDERS

    def test_not_in_lowercase_providers(self):
        assert "tokenharbor" not in _LOWERCASE_MODEL_PROVIDERS

    @pytest.mark.parametrize("empty", ["", None, "   "])
    def test_normalize_empty(self, empty):
        assert normalize_model_for_provider(empty, "tokenharbor") in ("", )
