"""Portal tool-list cache revalidation.

The cache exists so a Connectors page can render an app's tools without a portal round trip
per render. Its failure modes are asymmetric and security-relevant: a revoked authorization
must never be papered over by a cached copy, while a portal outage must not blank the page.
"""

from __future__ import annotations

import base64
import json
from typing import Any, List

import pytest

from tools.connectors.gateway.errors import (
    GatewayAuthError,
    GatewayUnavailable,
    ToolGatewayError,
)
from tools.connectors.portal import tools_cache
from tools.connectors.portal.client import NotModified
from tools.connectors.portal.errors import PortalToolsUnavailable
from tools.connectors.portal.wire import ConnectorTool, ConnectorToolsListing


def _listing(etag: str = "v1", version: str = "1.0.0") -> ConnectorToolsListing:
    return ConnectorToolsListing(
        connector="gmail", toolkitVersion=version, etag=etag,
        tools=[ConnectorTool(
            slug="gmail", name="GMAIL_SEND_EMAIL", description="Send",
            facet="write", hints=[], categories=["Email"],
            noAuth=False, deprecated=False,
        )],
    )


def _jwt(sub: str) -> str:
    """A minimal three-part JWT; only the `sub` claim is read."""
    encode = lambda raw: base64.urlsafe_b64encode(raw).decode().rstrip("=")  # noqa: E731
    return f"{encode(json.dumps({'alg': 'none'}).encode())}." \
           f"{encode(json.dumps({'sub': sub}).encode())}.sig"


class Client:
    """Stands in for PortalConnectorClient; `reply` is what the next fetch does."""

    def __init__(self, reply: Any) -> None:
        self.reply = reply
        self.calls: List[str | None] = []
        self.calls_made = 0

    def origin(self) -> str:
        return "https://portal.test"

    def authorization_token(self) -> str | None:
        # The cache namespaces entries by the JWT's sub claim, not the token bytes: a refresh for
        # the same member keeps the cache, and two members can never read each other's copy.
        return _jwt("member-1")

    def tools(self, slug: str, if_none_match: str | None = None) -> Any:
        self.calls.append(if_none_match)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


@pytest.fixture
def cache(tmp_path, monkeypatch):
    """A private cache root so the real ~/.anakot is never written."""
    monkeypatch.setattr(tools_cache, "_cache_path",
                        lambda origin, member, slug: tmp_path / f"{member}-{slug}.json")
    return tmp_path


def test_fresh_within_ttl_is_served_without_a_round_trip(cache):
    client = Client(_listing())
    first = tools_cache.read_tools("gmail", client=client)
    second = tools_cache.read_tools("gmail", client=client)

    assert second.tools == first.tools
    assert len(client.calls) == 1, "a fresh entry must not revalidate"


def test_304_keeps_cached_tools_and_sends_the_etag(cache):
    client = Client(_listing())
    tools_cache.read_tools("gmail", client=client)
    client.reply = NotModified()

    revalidated = tools_cache.read_tools("gmail", client=client, refresh=True)

    assert revalidated.tools[0].name == "GMAIL_SEND_EMAIL"
    assert revalidated.source == "revalidated"
    assert revalidated.stale is False
    assert client.calls[-1] == "v1", "revalidation must present the stored ETag"


def test_401_never_serves_the_cache(cache):
    """A revoked authorization must fail closed, not render from a cached copy."""
    client = Client(_listing())
    tools_cache.read_tools("gmail", client=client)
    client.reply = GatewayAuthError("token revoked", status=401)

    with pytest.raises(GatewayAuthError):
        tools_cache.read_tools("gmail", client=client, refresh=True)


def test_401_does_not_evict_the_cache(cache):
    """A transient 401 must not destroy a good copy the user still holds."""
    client = Client(_listing())
    tools_cache.read_tools("gmail", client=client)
    client.reply = GatewayAuthError("token revoked", status=401)

    with pytest.raises(GatewayAuthError):
        tools_cache.read_tools("gmail", client=client, refresh=True)

    client.reply = _listing()
    assert tools_cache.read_tools("gmail", client=client, refresh=True).tools


def test_outage_serves_stale_cache_marked_stale(cache):
    """A retryable 5xx must degrade to a labelled stale copy, not blank the page."""
    client = Client(_listing())
    tools_cache.read_tools("gmail", client=client)
    client.reply = ToolGatewayError("portal 503", retryable=True, status=503)

    served = tools_cache.read_tools("gmail", client=client, refresh=True)

    assert served.stale is True, "an outage fallback must be labelled stale, never presented as fresh"
    assert served.tools[0].name == "GMAIL_SEND_EMAIL"


def test_outage_with_no_cache_raises(cache):
    with pytest.raises(ToolGatewayError):
        tools_cache.read_tools("gmail", client=Client(ToolGatewayError("503", retryable=True, status=503)))


def test_unavailable_evicts_the_cache(cache):
    """The gateway reports the app as unavailable: leaving it cached would resurrect it."""
    client = Client(_listing())
    tools_cache.read_tools("gmail", client=client)
    client.reply = GatewayUnavailable("no such connector", status=404)

    with pytest.raises(GatewayUnavailable):
        tools_cache.read_tools("gmail", client=client, refresh=True)

    assert not list(cache.glob("*.json")), "a 404 must delete the cached app"
