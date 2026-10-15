"""Connector file inputs and outputs: paths are staged locally and returned files are downloaded safely."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

GATEWAY = "https://tool-gateway.test"
UPLOAD_URL = "https://storage.test/put?signature=upload"
DOWNLOAD_URL = "https://storage.test/get?signature=download"
STAGED_KEY = "project/gmail/send/request/key1"
GMAIL_SCHEMA = {
    "type": "object",
    "properties": {
        "attachment": {
            "description": "File to attach.",
            "anyOf": [
                {"$ref": "#/$defs/File"},
                {"type": "array", "items": {"$ref": "#/$defs/File"}},
            ],
        },
    },
    "$defs": {
        "File": {
            "type": "object", "file_uploadable": True, "description": "A file.",
            "properties": {"name": {"type": "string"}, "mimetype": {"type": "string"}, "s3key": {"type": "string"}},
        }
    },
}


class Response:
    def __init__(self, status_code: int, body=None, content: bytes = b""):
        self.status_code = status_code
        self._body = body
        self._content = content
        self.headers = {"x-request-id": "request-1"}
        self.text = json.dumps(body)

    def json(self):
        return self._body

    def iter_content(self, chunk_size):
        for start in range(0, len(self._content), chunk_size):
            yield self._content[start:start + chunk_size]

    def close(self):
        pass


class Gateway:
    def __init__(self, *, data=None, schema=GMAIL_SCHEMA):
        self.data = data if data is not None else {"sent": True}
        self.schema = schema
        self.requests: list[dict] = []

    def request(self, method, url, *, headers=None, json=None, timeout=None):
        self.requests.append({"method": method, "url": url, "headers": dict(headers or {}), "json": json})
        route = url.removeprefix(f"{GATEWAY}/v1/connectors/")
        if route == "schemas":
            return Response(200, {"schemas": {"GMAIL_SEND_EMAIL": {
                "connector": "gmail", "tool": "GMAIL_SEND_EMAIL", "inputSchema": self.schema,
            }}})
        if route == "files/upload":
            return Response(200, {"uploadUrl": UPLOAD_URL, "headers": {"Content-Type": json["mimetype"]},
                                  "descriptor": {"name": json["filename"], "mimetype": json["mimetype"], "s3key": STAGED_KEY},
                                  "expiresAt": "2026-10-15T00:05:00Z"})
        return Response(200, {"results": [{"connector": "gmail", "tool": json["tools"][0]["tool"], "data": self.data}]})


class Storage:
    def __init__(self, *, content: bytes = b"downloaded", status: int = 200):
        self.content = content
        self.status = status
        self.requests: list[dict] = []

    def request(self, method, url, *, headers=None, data=None, timeout=None, stream=False):
        self.requests.append({"method": method, "url": url, "headers": dict(headers or {}), "data": data})
        return Response(self.status, content=self.content if method == "GET" else b"")


@pytest.fixture(autouse=True)
def _reset_file_inputs(monkeypatch, tmp_path):
    monkeypatch.setenv("ANAKOT_HOME", str(tmp_path / ".anakot"))
    from tools.connectors.gateway import files
    from gateway.platforms import base

    files._FILE_INPUTS.clear()
    monkeypatch.setattr(base, "validate_media_delivery_path", lambda path, session_key="": str(Path(path).resolve()) if Path(path).is_file() else None)


def _client(gateway, storage):
    from tools.connectors.gateway.client import ConnectorClient

    return ConnectorClient(
        transport=gateway, storage=storage, endpoint_resolver=lambda: GATEWAY,
        header_provider=lambda url: {"Authorization": "Bearer gateway-token"},
    )


def _execute(gateway, storage, arguments):
    from tools.connectors.gateway.bridge import run_remote
    from tools.connectors.gateway.merge import partition_calls

    planned = partition_calls([{"name": "connectors__gmail__SEND_EMAIL", "arguments": arguments}]).remote
    return run_remote(planned, "call-1", availability=lambda: True,
                      client_factory=lambda: _client(gateway, storage))[0]


def _file(path: Path, body: bytes = b"local file") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path


def test_media_delivery_allowlist_includes_connector_downloads_root():
    from anakot_constants import CONNECTOR_DOWNLOADS_SUBDIR, get_anakot_home
    from gateway.platforms.base import _profile_cache_roots

    assert get_anakot_home() / CONNECTOR_DOWNLOADS_SUBDIR in _profile_cache_roots()


def test_describe_replaces_file_schema_with_path_and_remembers_array_paths():
    from tools.connectors.gateway import files
    from tools.connectors.gateway.bridge import connector_describe

    result = connector_describe(
        ["connectors__gmail__SEND_EMAIL"], availability=lambda: True,
        client_factory=lambda: type("Client", (), {"schemas": lambda self, _: {
            "schemas": {"GMAIL_SEND_EMAIL": {"connector": "gmail", "input_schema": GMAIL_SCHEMA}}
        }})(),
    )

    parameters = result["tools"]["connectors__gmail__SEND_EMAIL"]["parameters"]
    assert parameters["$defs"]["File"] == {"type": "string", "description": "A file. Pass a local file path."}
    assert "s3key" not in json.dumps(parameters)
    assert files._FILE_INPUTS["connectors__gmail__SEND_EMAIL"] == (("attachment",), ("attachment", "*"))


def test_local_file_is_staged_uploaded_without_gateway_auth_and_executed(tmp_path):
    gateway, storage = Gateway(), Storage()
    local = _file(tmp_path / "report.pdf", b"pdf bytes")

    result = _execute(gateway, storage, {"attachment": str(local)})

    assert result["response"] == {"sent": True}
    assert [request["url"].split("/connectors/")[-1] for request in gateway.requests] == ["schemas", "files/upload", "execute"]
    assert gateway.requests[1]["json"]["filename"] == "report.pdf"
    assert gateway.requests[2]["json"]["tools"][0]["arguments"]["attachment"] == {
        "name": "report.pdf", "mimetype": "application/pdf", "s3key": STAGED_KEY,
    }
    assert storage.requests == [{"method": "PUT", "url": UPLOAD_URL, "headers": {"Content-Type": "application/pdf"}, "data": b"pdf bytes"}]


def test_every_array_path_is_staged_and_schema_lookup_is_cached(tmp_path):
    gateway, storage = Gateway(), Storage()
    first = _file(tmp_path / "a.txt", b"a")
    second = _file(tmp_path / "b.txt", b"b")

    _execute(gateway, storage, {"attachment": [str(first), str(second)]})
    _execute(gateway, storage, {"attachment": str(first)})

    assert [request["url"].split("/connectors/")[-1] for request in gateway.requests] == [
        "schemas", "files/upload", "files/upload", "execute", "files/upload", "execute",
    ]
    assert [request["data"] for request in storage.requests] == [b"a", b"b", b"a"]


@pytest.mark.parametrize("bad_path,code", [
    ("missing.pdf", "FILE_NOT_FOUND"),
    (".", "FILE_NOT_FOUND"),
])
def test_refused_or_missing_path_never_reaches_upload(tmp_path, bad_path, code):
    gateway, storage = Gateway(), Storage()

    result = _execute(gateway, storage, {"attachment": str(tmp_path / bad_path)})

    assert result["error"]["code"] == code
    assert result["error"]["family"] == "product"
    assert not any(request["url"].endswith("files/upload") for request in gateway.requests)
    assert storage.requests == []


def test_file_over_gateway_cap_is_rejected_before_upload(tmp_path, monkeypatch):
    from tools.connectors.gateway import files

    monkeypatch.setattr(files, "CONNECTOR_FILE_MAX_BYTES", 2)
    gateway, storage = Gateway(), Storage()

    result = _execute(gateway, storage, {"attachment": str(_file(tmp_path / "large.bin", b"123"))})

    assert result["error"]["code"] == "FILE_TOO_LARGE"
    assert storage.requests == []


def test_returned_file_is_downloaded_to_profile_connector_folder_and_url_is_removed():
    gateway = Gateway(data={"attachment": {"name": "invoice.pdf", "mimetype": "application/pdf", "url": DOWNLOAD_URL}})
    storage = Storage(content=b"received bytes")

    result = _execute(gateway, storage, {})

    saved = result["response"]["attachment"]
    path = Path(saved["path"])
    assert set(saved) == {"name", "mimetype", "path"}
    assert path.parent.name == "connectors" and path.read_bytes() == b"received bytes"
    assert storage.requests == [{"method": "GET", "url": DOWNLOAD_URL, "headers": {}, "data": None}]
    assert "signature" not in json.dumps(result)


def test_failed_storage_upload_prevents_execute(tmp_path):
    gateway, storage = Gateway(), Storage(status=403)

    result = _execute(gateway, storage, {"attachment": str(_file(tmp_path / "report.txt"))})

    assert result["error"]["code"] == "FILE_UPLOAD_FAILED"
    assert not any(request["url"].endswith("/execute") for request in gateway.requests)


def test_storage_descriptor_from_model_is_rejected():
    result = _execute(Gateway(), Storage(), {"attachment": {"name": "x", "mimetype": "text/plain", "s3key": "secret"}})

    assert result["error"]["code"] == "FILE_NOT_ALLOWED"
    assert "path" in result["error"]["hint"]
