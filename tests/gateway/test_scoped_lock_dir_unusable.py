"""Shared token-lock directories that an elevated process left unusable must fail clearly and retry."""

import logging
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from gateway import status
from gateway.platforms.base import BasePlatformAdapter


class _StubAdapter(BasePlatformAdapter):
    platform = MagicMock(value="telegram")

    async def connect(self, *, is_reconnect: bool = False) -> bool:
        return True

    async def disconnect(self) -> None:
        pass

    async def send(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def get_chat_info(self, chat_id: str) -> dict[str, Any]:
        return {}


@pytest.fixture()
def adapter():
    obj = _StubAdapter.__new__(_StubAdapter)
    obj._running = True
    obj._fatal_error_code = None
    obj._fatal_error_message = None
    obj._fatal_error_retryable = True
    obj._fatal_error_handler = None
    obj._platform_lock_scope = None
    obj._platform_lock_identity = None
    obj._platform_lock_takeover_allowed = False
    obj._platform_lock_takeover_attempted = False
    obj._status_write_logged = None
    return obj


@pytest.fixture(autouse=True)
def clear_lock_warning_state():
    status._warned_unusable_lock_dirs.clear()
    yield
    status._warned_unusable_lock_dirs.clear()


def test_permission_failure_is_named_once_and_recovers_without_restart(tmp_path, monkeypatch, caplog):
    lock_dir = tmp_path / "gateway-locks"
    monkeypatch.setenv("ANAKOT_GATEWAY_LOCK_DIR", str(lock_dir))
    real_mkdir = Path.mkdir

    def deny_lock_dir(self, *args, **kwargs):
        if Path(self) == lock_dir:
            raise PermissionError(13, "access denied")
        return real_mkdir(self, *args, **kwargs)

    with monkeypatch.context() as denied:
        denied.setattr(Path, "mkdir", deny_lock_dir)
        with caplog.at_level(logging.DEBUG, logger="gateway.status"):
            with pytest.raises(status.ScopedLockDirUnusable) as first:
                status.acquire_scoped_lock("telegram-bot-token", "token")
            with pytest.raises(status.ScopedLockDirUnusable):
                status.acquire_scoped_lock("telegram-bot-token", "token")

    assert first.value.filename == str(lock_dir)
    assert "not usable" in str(first.value)
    warnings = [
        record for record in caplog.records
        if record.levelno == logging.WARNING and "not usable" in record.getMessage()
    ]
    assert len(warnings) == 1
    assert str(lock_dir) in warnings[0].getMessage()
    assert ("icacls" if os.name == "nt" else "chown") in warnings[0].getMessage()

    acquired, existing = status.acquire_scoped_lock("telegram-bot-token", "token")
    assert acquired is True and existing is None
    assert lock_dir not in status._warned_unusable_lock_dirs
    status.release_scoped_lock("telegram-bot-token", "token")


def test_unreadable_existing_token_lock_is_not_reported_as_a_holder(tmp_path, monkeypatch):
    lock_dir = tmp_path / "gateway-locks"
    lock_dir.mkdir()
    lock_path = lock_dir / "telegram-bot-token-locked.lock"
    lock_path.write_text("{\"pid\": 1}", encoding="utf-8")
    monkeypatch.setenv("ANAKOT_GATEWAY_LOCK_DIR", str(lock_dir))
    monkeypatch.setattr(status, "_get_scope_lock_path", lambda _scope, _identity: lock_path)
    real_open = Path.open

    def deny_lock_read(self, *args, **kwargs):
        if Path(self) == lock_path:
            raise PermissionError(13, "access denied")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", deny_lock_read)
    with pytest.raises(status.ScopedLockDirUnusable) as exc_info:
        status.acquire_scoped_lock("telegram-bot-token", "locked")

    assert exc_info.value.filename == str(lock_dir)


def test_adapter_parks_lock_directory_error_but_keeps_it_retryable(adapter, tmp_path, monkeypatch):
    lock_dir = tmp_path / "gateway-locks"
    error = status.ScopedLockDirUnusable(13, "gateway lock directory is not usable", str(lock_dir))
    monkeypatch.setattr("gateway.status.acquire_scoped_lock", MagicMock(side_effect=error))
    monkeypatch.setattr(adapter, "_write_runtime_status_safe", MagicMock())

    result = adapter._acquire_platform_lock("telegram-bot-token", "token", "Telegram bot token")

    assert result is False
    assert adapter._fatal_error_code == "lock_dir_unusable"
    assert adapter._fatal_error_retryable is True
    assert str(lock_dir) in adapter._fatal_error_message
    assert ("icacls" if os.name == "nt" else "chown") in adapter._fatal_error_message
    assert adapter._platform_lock_identity is None
