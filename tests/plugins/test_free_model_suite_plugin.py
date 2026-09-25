"""Behavior tests for the bundled Free Model Suite plugin API."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from anakot_cli.web_models import ModelAssignment

PLUGIN_FILE = (
    Path(__file__).resolve().parents[2]
    / "plugins"
    / "free-model-suite"
    / "dashboard"
    / "plugin_api.py"
)


def _load_plugin():
    assert PLUGIN_FILE.exists(), f"plugin file missing: {PLUGIN_FILE}"
    name = "anakot_dashboard_plugin_free_model_suite_test"
    spec = importlib.util.spec_from_file_location(name, PLUGIN_FILE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def plugin():
    module = _load_plugin()
    app = FastAPI()
    app.include_router(module.router, prefix="/api/plugins/free-model-suite")
    return module, TestClient(app)


def test_catalog_reuses_inventory_and_keeps_profile_scope(plugin, monkeypatch):
    module, client = plugin
    captured = {}

    def fake_build(ctx, **kwargs):
        from anakot_constants import get_anakot_home

        captured["home"] = get_anakot_home()
        captured["kwargs"] = kwargs
        return {
            "provider": "openrouter",
            "model": "stealth/space-bunny-alpha",
            "providers": [],
        }

    monkeypatch.setattr(module, "build_model_options_payload", fake_build)
    monkeypatch.setattr(module, "load_picker_context", lambda: object())

    response = client.get("/api/plugins/free-model-suite/catalog")

    assert response.status_code == 200
    assert response.json()["model"] == "stealth/space-bunny-alpha"
    assert captured["kwargs"] == {
        "explicit_only": False,
        "include_unconfigured": False,
        "refresh": False,
    }
    assert captured["home"] == Path(__import__("os").environ["ANAKOT_HOME"])


def test_catalog_scope_moves_a_to_b_to_a(plugin, monkeypatch, tmp_path):
    module, client = plugin
    homes = []
    fake_home = tmp_path / ".anakot"
    research_home = fake_home / "profiles" / "research"
    research_home.mkdir(parents=True)
    (research_home / "SOUL.md").write_text("# Research\n", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("ANAKOT_HOME", str(fake_home))

    def fake_build(ctx, **kwargs):
        from anakot_constants import get_anakot_home

        homes.append(get_anakot_home())
        return {"providers": []}

    monkeypatch.setattr(module, "build_model_options_payload", fake_build)
    monkeypatch.setattr(module, "load_picker_context", lambda: object())

    for profile in (None, "research", None):
        response = client.get(
            "/api/plugins/free-model-suite/catalog",
            params={} if profile is None else {"profile": profile},
        )
        assert response.status_code == 200

    assert homes == [fake_home, fake_home / "profiles" / "research", fake_home]


def test_apply_delegates_to_the_canonical_model_assignment_contract(plugin, monkeypatch):
    module, client = plugin
    captured = {}

    async def fake_set(body, profile=None):
        captured["body"] = body
        captured["profile"] = profile
        return {"ok": True, "provider": body.provider, "model": body.model}

    monkeypatch.setattr(module, "set_model_assignment", fake_set)

    response = client.post(
        "/api/plugins/free-model-suite/models?profile=research",
        json={"provider": "openrouter", "model": "openai/gpt-oss-120b:free"},
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert isinstance(captured["body"], ModelAssignment)
    assert captured["body"].scope == "main"
    assert captured["body"].provider == "openrouter"
    assert captured["body"].model == "openai/gpt-oss-120b:free"
    assert captured["profile"] == "research"


def test_bundled_manifest_exposes_only_the_validated_api_entry():
    from anakot_cli.web_server_dashboard import _discover_dashboard_plugins

    rows = {row["name"]: row for row in _discover_dashboard_plugins()}
    row = rows["free-model-suite"]

    assert row["source"] == "bundled"
    assert row["_api_file"] == "plugin_api.py"
    assert (PLUGIN_FILE.parent / row["_api_file"]).resolve().is_relative_to(PLUGIN_FILE.parent.resolve())


def test_probe_surfaces_reasoning_finish_reason_and_hallucinated_tool_calls(plugin, monkeypatch):
    module, client = plugin
    captured = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured["request"] = kwargs
            message = SimpleNamespace(
                content="4",
                reasoning="I should add two and two.",
                reasoning_content=None,
                reasoning_details=None,
                tool_calls=[
                    SimpleNamespace(
                        function=SimpleNamespace(name="calculator", arguments='{"expression":"2+2"}')
                    )
                ],
            )
            return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="length")])

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))

    def fake_resolve(provider, *, model, async_mode):
        captured["resolve"] = (provider, model, async_mode)
        return fake_client, model

    monkeypatch.setattr(module, "resolve_provider_client", fake_resolve)

    response = client.post(
        "/api/plugins/free-model-suite/probe",
        json={
            "provider": "openrouter",
            "model": "openai/gpt-oss-120b:free",
            "prompt": "What is 2+2?",
            "max_tokens": 64,
            "timeout_s": 5,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "provider": "openrouter",
        "model": "openai/gpt-oss-120b:free",
        "content": "4",
        "reasoning": "I should add two and two.",
        "finish_reason": "length",
        "tool_calls": [{"name": "calculator", "arguments": '{"expression":"2+2"}'}],
    }
    assert captured["resolve"] == ("openrouter", "openai/gpt-oss-120b:free", True)
    assert captured["request"]["stream"] is False
    assert captured["request"]["max_tokens"] == 64


def test_probe_rejects_oversized_inputs_before_resolving_a_client(plugin, monkeypatch):
    module, client = plugin

    def fail_resolve(*args, **kwargs):
        raise AssertionError("client resolution must not run for invalid bounded inputs")

    monkeypatch.setattr(module, "resolve_provider_client", fail_resolve)

    response = client.post(
        "/api/plugins/free-model-suite/probe",
        json={"provider": "nous", "model": "some-model", "prompt": "x" * 1001},
    )

    assert response.status_code == 422


def test_probe_rejects_empty_identity_before_resolving_a_client(plugin, monkeypatch):
    module, client = plugin

    def fail_resolve(*args, **kwargs):
        raise AssertionError("client resolution must not run for an empty provider/model")

    monkeypatch.setattr(module, "resolve_provider_client", fail_resolve)

    response = client.post(
        "/api/plugins/free-model-suite/probe",
        json={"provider": " ", "model": " ", "prompt": "hello"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "provider, model, and prompt are required"
