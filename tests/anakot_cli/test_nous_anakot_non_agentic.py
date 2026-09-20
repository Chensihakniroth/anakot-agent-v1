"""Tests for the Nous-Anakot-3/4 non-agentic warning detector.

Prior to this check, the warning fired on any model whose name contained
``"anakot"`` anywhere (case-insensitive). That false-positived on unrelated
local Modelfiles such as ``anakot-brain:qwen3-14b-ctx16k`` — a tool-capable
Qwen3 wrapper that happens to live under the "anakot" tag namespace.

``is_nous_anakot_non_agentic`` should only match the actual Nous Research
Anakot-3 / Anakot-4 chat family.
"""

from __future__ import annotations

import pytest

from anakot_cli.model_switch import (
    _ANAKOT_MODEL_WARNING,
    _check_anakot_model_warning,
    is_nous_anakot_non_agentic,
)


@pytest.mark.parametrize(
    "model_name",
    [
        "NousResearch/Anakot-3-Llama-3.1-70B",
        "NousResearch/Anakot-3-Llama-3.1-405B",
        "anakot-3",
        "Anakot-3",
        "anakot-4",
        "anakot-4-405b",
        "anakot_4_70b",
        "openrouter/anakot3:70b",
        "openrouter/nousresearch/anakot-4-405b",
        "NousResearch/Anakot3",
        "anakot-3.1",
    ],
)
def test_matches_real_nous_anakot_chat_models(model_name: str) -> None:
    assert is_nous_anakot_non_agentic(model_name), (
        f"expected {model_name!r} to be flagged as Nous Anakot 3/4"
    )
    assert _check_anakot_model_warning(model_name) == _ANAKOT_MODEL_WARNING


