"""Plugin-declared settings fields rendered as settings_schema (#46600, #87934).

Drives the real manifest reader + config writer against a temp ANAKOT_HOME: fields carry
each schema key with its current value, and writes land in the SAME
``plugins.entries.<id>.settings`` namespace ``ctx.get_config`` reads — never a secret into
config.yaml.
"""

import pytest

from anakot_cli import plugins_settings

MANIFEST = """\
name: demo-plugin
version: 1.0.0
config_schema:
  api_url: {type: str, default: "https://example.invalid", description: "Service endpoint"}
  retries: {type: int, default: 3}
  verbose: {type: bool, default: false}
  mode: {type: str, choices: [fast, careful], default: fast}
  api_key: {type: secret, description: "Token"}
"""


@pytest.fixture
def plugins_home(tmp_path, monkeypatch):
    home = tmp_path / "anakot-home"
    plugin_dir = home / "plugins" / "demo-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(MANIFEST, encoding="utf-8")
    (home / "config.yaml").write_text(
        "plugins:\n  entries:\n    demo-plugin:\n      settings:\n        retries: 7\n", encoding="utf-8")
    monkeypatch.setenv("ANAKOT_HOME", str(home))
    return home


def test_fields_carry_schema_with_current_values_and_no_secret_values(plugins_home, monkeypatch):
    monkeypatch.setenv("DEMO_PLUGIN_API_KEY", "shh")

    fields = {f["key"]: f for f in plugins_settings.plugin_settings_fields("demo-plugin", plugins_home / "plugins" / "demo-plugin")}

    assert fields["api_url"]["type"] == "string" and fields["api_url"]["value"] == "https://example.invalid"
    assert fields["retries"]["type"] == "number" and fields["retries"]["value"] == 7  # config.yaml wins over default
    assert fields["verbose"]["type"] == "boolean" and fields["verbose"]["value"] is False
    assert fields["mode"]["type"] == "enum" and fields["mode"]["choices"] == ["fast", "careful"]
    assert fields["api_key"] == {"key": "api_key", "type": "secret", "label": "api_key", "description": "Token",
                                 "required": False, "env": "DEMO_PLUGIN_API_KEY", "has_value": True}


def test_save_writes_the_plugin_namespace_and_refuses_secrets_and_bad_types(plugins_home):
    plugin_dir = plugins_home / "plugins" / "demo-plugin"

    written = plugins_settings.save_plugin_settings(
        "demo-plugin", plugin_dir, {"api_url": "https://real.invalid", "retries": 2, "mode": "careful"})

    assert sorted(written) == ["api_url", "mode", "retries"]
    from anakot_cli.config import load_config_readonly
    assert load_config_readonly()["plugins"]["entries"]["demo-plugin"]["settings"] == {
        "api_url": "https://real.invalid", "retries": 2, "mode": "careful"}
    refreshed = {f["key"]: f["value"] for f in plugins_settings.plugin_settings_fields("demo-plugin", plugin_dir)
                 if "value" in f}
    assert refreshed["retries"] == 2 and refreshed["mode"] == "careful"

    for values in ({"api_key": "leak"}, {"retries": "two"}, {"mode": "reckless"}, {"unknown": 1}):
        with pytest.raises(ValueError):
            plugins_settings.save_plugin_settings("demo-plugin", plugin_dir, values)
    assert "api_key" not in (plugins_home / "config.yaml").read_text(encoding="utf-8")


def _manage(**params):
    from tui_gateway import server
    return server.handle_request({"id": "1", "method": "plugins.manage", "params": params})


def test_plugins_manage_list_and_settings_round_trip(plugins_home, monkeypatch):
    """The RPC surface carries the schema on list and writes through it on settings."""
    monkeypatch.setenv("DEMO_PLUGIN_API_KEY", "shh")

    rows = _manage(action="list")["result"]["plugins"]
    row = next(r for r in rows if r["key"] == "demo-plugin")
    fields = {f["key"]: f for f in row["settings_schema"]}
    assert fields["retries"]["value"] == 7
    assert fields["api_key"]["type"] == "secret" and fields["api_key"]["has_value"] is True
    assert "value" not in fields["api_key"]  # the secret itself never leaves the backend

    resp = _manage(action="settings", key="demo-plugin",
                   values={"api_url": "https://real.invalid", "retries": 2, "mode": "careful"})
    assert resp["result"]["ok"] is True
    assert sorted(resp["result"]["written"]) == ["api_url", "mode", "retries"]

    from anakot_cli.config import load_config_readonly
    assert load_config_readonly()["plugins"]["entries"]["demo-plugin"]["settings"] == {
        "api_url": "https://real.invalid", "retries": 2, "mode": "careful"}
    # A secret can never be written through this route — it lives in .env, not config.yaml.
    assert _manage(action="settings", key="demo-plugin",
                   values={"api_key": "leak"})["error"]["code"] == 4021
    assert "api_key" not in (plugins_home / "config.yaml").read_text(encoding="utf-8")
