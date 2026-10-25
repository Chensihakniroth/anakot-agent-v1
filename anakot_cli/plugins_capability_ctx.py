"""Capability-gated methods mixed into ``PluginContext``."""

from __future__ import annotations

import logging
from typing import Any, Optional

from anakot_cli.plugin_capabilities import plugin_capability_granted
from anakot_cli.plugins_loader import _plugin_home_scope

logger = logging.getLogger(__name__)


class PluginCapabilityCtxMixin:
    """Host-owned capability probes and the one-use side-question surface."""

    def has_capability(self, capability: str) -> bool:
        """Return whether this plugin's capability is live; unknown state fails closed."""
        if self.manifest.source == "bundled" and capability == "tools.override":
            return True
        try:
            from anakot_cli.config import load_config
            with _plugin_home_scope(self._manager.home_path):
                config = load_config() or {}
        except Exception:
            return False
        return plugin_capability_granted(self.plugin_id, capability, config=config)

    def _side_question_granted(self) -> bool:
        try:
            from anakot_cli.config import load_config
            with _plugin_home_scope(self._manager.home_path):
                config = load_config() or {}
        except Exception:
            return False
        return plugin_capability_granted(self.plugin_id, "llm.side_question", config=config)

    def side_question(self, token: str, prompt: str, *, timeout: float = 15.0) -> Optional[str]:
        """Ask the session's own agent one text-only question about the completed turn."""
        if not self._side_question_granted():
            logger.info("Plugin %s called side_question without consent", self.plugin_id)
            return None
        from agent.side_question_lease import redeem_side_question

        return redeem_side_question(
            token,
            prompt,
            plugin_id=self.plugin_id,
            home=self._manager.home_path,
            timeout=timeout,
        )
