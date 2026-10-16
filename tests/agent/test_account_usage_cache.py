"""Cached account-usage snapshot contracts."""

from datetime import datetime, timedelta, timezone


def _snapshot(*, identity=None, fetched_at=None):
    from agent.account_usage import AccountUsageSnapshot, AccountUsageWindow

    return AccountUsageSnapshot(
        provider="openai-codex", source="test", fetched_at=fetched_at or datetime.now(timezone.utc),
        windows=(AccountUsageWindow("5h", used_percent=10),), identity=identity,
    )


def test_usage_cache_isolated_by_identity(monkeypatch, tmp_path):
    import agent.account_usage_cache as cache

    monkeypatch.setattr("anakot_constants.get_anakot_home", lambda: tmp_path)
    monkeypatch.setattr("anakot_constants.anakot_home_key", lambda path=None: str(tmp_path))
    cache._snapshots.clear()
    cache._started.clear()
    first = _snapshot(identity="codex:user:a")
    cache.remember_account_usage("openai-codex", first, identity_id="codex:user:a", started_monotonic=1)
    assert cache.cached_account_usage("openai-codex", identity_id="codex:user:a") is first
    assert cache.cached_account_usage("openai-codex", identity_id="codex:user:b") is None


def test_late_usage_fetch_cannot_replace_newer_snapshot(monkeypatch, tmp_path):
    import agent.account_usage_cache as cache

    monkeypatch.setattr("anakot_constants.get_anakot_home", lambda: tmp_path)
    monkeypatch.setattr("anakot_constants.anakot_home_key", lambda path=None: str(tmp_path))
    cache._snapshots.clear()
    cache._started.clear()
    newer = _snapshot(identity="codex:user:a")
    older = _snapshot(identity="codex:user:a")
    cache.remember_account_usage("openai-codex", newer, identity_id="codex:user:a", started_monotonic=20)
    cache.remember_account_usage("openai-codex", older, identity_id="codex:user:a", started_monotonic=10)
    assert cache.cached_account_usage("openai-codex", identity_id="codex:user:a") is newer


def test_stale_snapshots_are_not_presented_as_live():
    import agent.account_usage_cache as cache

    old = _snapshot(fetched_at=datetime.now(timezone.utc) - timedelta(minutes=16))
    fresh = _snapshot()
    assert cache.snapshot_is_stale(old) is True
    assert cache.snapshot_is_stale(fresh) is False


def test_inventory_attaches_fresh_usage_without_blocking(monkeypatch):
    from anakot_cli import inventory

    snapshot = _snapshot()
    refreshed = []
    monkeypatch.setattr("agent.account_usage_cache.has_account_usage", lambda slug: slug == "openai-codex")
    monkeypatch.setattr("agent.account_usage_cache.cached_account_usage", lambda slug: snapshot)
    monkeypatch.setattr("agent.account_usage_cache.snapshot_is_stale", lambda value: False)
    monkeypatch.setattr("agent.account_usage_cache.refresh_account_usage_async", lambda providers: refreshed.extend(providers) or [])
    rows = [{"slug": "openai-codex", "authenticated": True, "is_user_defined": False}]
    inventory._apply_usage(rows)
    assert rows[0]["usage"]["windows"][0]["label"] == "5h"
    assert refreshed == ["openai-codex"]
