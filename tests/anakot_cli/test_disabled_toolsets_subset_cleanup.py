"""Legacy disabled toolset entries are cleared when their superset is enabled."""

from unittest.mock import patch

from anakot_cli.tools_config import _get_platform_tools, _save_platform_tools


def test_enabling_web_clears_legacy_search_subset():
    config = {
        "platform_toolsets": {"cli": ["file", "terminal", "web"]},
        "agent": {"disabled_toolsets": ["search", "browser", "memory"]},
    }
    enabled = _get_platform_tools(config, "cli", include_default_mcp_servers=False)
    with patch("anakot_cli.tools_config.save_config"):
        _save_platform_tools(config, "cli", set(enabled))
    assert config["agent"]["disabled_toolsets"] == ["browser", "memory"]
