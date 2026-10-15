"""Nemotron Super 3.5 model defaults from the Hermes parity port."""


def test_nemotron_super35_has_one_million_context_fallback():
    from agent.model_metadata import DEFAULT_CONTEXT_LENGTHS, _longest_key_match

    key, context = _longest_key_match(DEFAULT_CONTEXT_LENGTHS, "nvidia/nemotron-3.5-super-120b-a12b")

    assert key == "nemotron-3.5-super"
    assert context == 1_000_000


def test_nemotron_super35_gets_the_long_reasoning_stale_timeout_floor():
    from agent.reasoning_timeouts import get_reasoning_stale_timeout_floor

    assert get_reasoning_stale_timeout_floor("nvidia/nemotron-3.5-super-120b-a12b") == 600.0
