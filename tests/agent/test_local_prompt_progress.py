"""Prompt-prefill progress keeps local-model watchdogs alive without faking output chunks."""

from types import SimpleNamespace

from agent import local_prompt_progress as progress


def _chunk(*, content=None, prompt_progress=None):
    extra = {"prompt_progress": prompt_progress} if prompt_progress is not None else None
    delta = SimpleNamespace(content=content, tool_calls=None, reasoning_content=None,
                            reasoning=None, refusal=None)
    return SimpleNamespace(model_extra=extra, choices=[SimpleNamespace(
        finish_reason=None, delta=delta)])


def test_progress_request_merges_extra_body_without_overwriting_operator_fields():
    result = progress.with_prompt_progress({"model": "local", "extra_body": {"seed": 7}})
    assert result["extra_body"] == {"seed": 7, "return_progress": True}
    assert progress.with_prompt_progress({"extra_body": {"return_progress": False}})["extra_body"] == {
        "return_progress": False,
    }


def test_progress_chunk_requires_an_empty_assistant_delta():
    payload = {"processed": 25, "total": 100, "time_ms": 200}
    assert progress.prompt_progress(_chunk(prompt_progress=payload)) == payload
    assert progress.prompt_progress(_chunk(content="real output", prompt_progress=payload)) is None


def test_prompt_reading_clock_counts_only_newly_read_tokens(monkeypatch):
    now = [10.0]
    monkeypatch.setattr(progress.time, "monotonic", lambda: now[0])
    seen = []
    clock = progress.PromptReadingClock(10.0)
    with progress.prompt_reading_hook(seen.append):
        now[0] = 11.0
        assert clock.tick({"processed": 10, "time_ms": 1000}) is True
        now[0] = 12.0
        assert clock.tick({"processed": 10, "time_ms": 1000}) is False
        now[0] = 13.0
        assert clock.tick({"processed": 20, "time_ms": 2000}) is True
    assert clock.seconds == 2.0
    assert seen == [1.0, 1.0]
