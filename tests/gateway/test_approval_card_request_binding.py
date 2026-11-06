"""A native approval card answers only the request it was rendered for.

Two approvals can share one chat session: the first card's request ends (timeout, ``/approve``
from another client) while a newer request is queued behind it. A press on the first card must
not resolve the newer request, which the user has not seen yet — upstream ``5ab58da1``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from gateway.config import PlatformConfig
from plugins.platforms.telegram.adapter import TelegramAdapter
from tools import approval
from tools.approval_gateway_wait import _ApprovalEntry

SESSION = "agent:main:telegram:dm:1"


@pytest.fixture
def newer_request_pending():
    """Request ``req-old`` already settled; ``req-new`` is the one still waiting."""
    entry = _ApprovalEntry({"command": "rm -rf build", "request_id": "req-new"})
    with approval._lock:
        approval._gateway_queues[SESSION] = [entry]
    yield entry
    with approval._lock:
        approval._gateway_queues.pop(SESSION, None)


def test_a_settled_request_id_resolves_nothing(newer_request_pending):
    assert approval.resolve_gateway_approval_card(SESSION, "once", "req-old") == 0
    assert not newer_request_pending.event.is_set()
    assert approval._gateway_queues[SESSION] == [newer_request_pending]


def test_a_matching_request_id_resolves_that_request(newer_request_pending):
    assert approval.resolve_gateway_approval_card(SESSION, "once", "req-new") == 1
    assert newer_request_pending.event.is_set()
    assert newer_request_pending.result == "once"


def test_a_card_without_a_request_id_keeps_the_fifo_fallback(newer_request_pending):
    """Older cards carry no id; they must keep resolving the oldest queued request."""
    assert approval.resolve_gateway_approval_card(SESSION, "deny", None) == 1
    assert newer_request_pending.result == "deny"


def _make_adapter():
    adapter = TelegramAdapter(PlatformConfig(enabled=True, token="test-token"))
    adapter._bot = AsyncMock()
    adapter._app = MagicMock()
    adapter._bot.send_message = AsyncMock(return_value=SimpleNamespace(message_id=42))
    return adapter


async def _press_telegram_card(request_id):
    adapter = _make_adapter()
    await adapter.send_exec_approval(
        chat_id="12345", command="rm -rf build", session_key=SESSION, request_id=request_id)
    approval_id = next(iter(adapter._approval_state))
    query = AsyncMock()
    query.data = f"ea:once:{approval_id}"
    query.message = MagicMock()
    query.message.chat_id = 12345
    query.from_user = MagicMock()
    query.from_user.id = 12345
    query.from_user.first_name = "Alice"
    with patch.dict(os.environ, {"TELEGRAM_ALLOWED_USERS": "*"}):
        await adapter._handle_callback_query(SimpleNamespace(callback_query=query), MagicMock())


@pytest.mark.asyncio
async def test_telegram_card_for_a_settled_request_does_not_touch_the_next_one(newer_request_pending):
    await _press_telegram_card("req-old")

    assert not newer_request_pending.event.is_set()
    assert approval._gateway_queues[SESSION] == [newer_request_pending]


@pytest.mark.asyncio
async def test_telegram_card_resolves_its_own_request(newer_request_pending):
    await _press_telegram_card("req-new")

    assert newer_request_pending.event.is_set()
    assert newer_request_pending.result == "once"
