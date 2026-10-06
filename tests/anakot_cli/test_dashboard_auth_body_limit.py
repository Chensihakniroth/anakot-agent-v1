"""Body budgets apply before parsing public auth requests, not to uploads."""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from starlette.types import Message, Scope

from anakot_cli import web_server


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> Iterator[FastAPI]:
    monkeypatch.setattr(web_server.app.state, "bound_host", None, raising=False)
    monkeypatch.setattr(web_server.app.state, "auth_required", False, raising=False)
    yield web_server.app


def _post(app: FastAPI, path: str, body: bytes, headers: dict[str, str] | None = None):
    from starlette.testclient import TestClient

    client = TestClient(app)
    return client.post(path, content=body, headers=headers or {})


def test_oversized_auth_body_is_rejected_before_parsing(app):
    """A >64KB POST to a public auth route returns 413, not a JSON parse error."""
    body = b'{"provider":"x","data":"' + b"x" * 70_000 + b'"}'
    resp = _post(app, "/auth/password-login", body, {"content-type": "application/json"})
    assert resp.status_code == 413
    assert resp.json()["detail"] == "Request body too large"


def test_normal_auth_body_passes_through(app):
    """A small valid auth body is not blocked by the limit."""
    body = b'{"provider":"testpw","username":"admin","password":"hunter2"}'
    resp = _post(app, "/auth/password-login", body, {"content-type": "application/json"})
    # The route itself may reject the credentials, but not with 413.
    assert resp.status_code != 413


def test_non_auth_path_is_not_limited(app):
    """The body limit only applies to /auth/ paths."""
    body = b'{"data":"' + b"x" * 70_000 + b'"}'
    resp = _post(app, "/api/status", body, {"content-type": "application/json"})
    assert resp.status_code != 413
