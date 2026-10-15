"""Stage connector file inputs and download connector file outputs.

The model sees local paths for file inputs and local paths for returned files. Presigned storage URLs,
keys, and gateway bearer headers never reach model-visible results.
"""

from __future__ import annotations

import logging
import mimetypes
import os
import re
import tempfile
from dataclasses import replace as dataclass_replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Mapping, Optional, Sequence

from tools.connectors.gateway.errors import ToolGatewayError
from tools.connectors.gateway.merge import PlannedCall
from tools.connectors.gateway.names import parse_connector_name, vendor_slug_candidates
from tools.connectors.gateway.wire import CONNECTOR_FILE_MAX_BYTES, execute_error_family

logger = logging.getLogger(__name__)

DOWNLOAD_MAX_BYTES = 50 * 1024 * 1024
FILE_INPUT_NOTE = "Pass a local file path."
_ARRAY_ITEM = "*"
_MAX_SCHEMA_DEPTH = 32
_HOST_READABLE_BACKENDS = frozenset({"local", "docker"})
_UNSAFE_NAME_CHARS = re.compile(r"[\x00-\x1f\x7f<>:\"|?*\\/]")
_MAX_NAME_CHARS = 150
Path_ = tuple[str, ...]
_FILE_INPUTS: dict[str, tuple[Path_, ...]] = {}

__all__ = ["DOWNLOAD_MAX_BYTES", "FileInputError", "model_parameters", "save_outputs", "stage_inputs"]


class _Staged(dict):
    """Marker for a descriptor produced by this dispatch."""


class FileInputError(Exception):
    """A file input failed before the connector execute request."""

    def __init__(self, code: str, message: str, *, hint: Optional[str] = None) -> None:
        super().__init__(message)
        self.code = code
        self.hint = hint

    def result(self) -> dict[str, Any]:
        error: dict[str, Any] = {
            "code": self.code,
            "message": str(self),
            "family": execute_error_family(self.code),
        }
        if self.hint:
            error["hint"] = self.hint
        return {"data": None, "error": error}


# ── schema rewriting ────────────────────────────────────────────────────────
def model_parameters(name: str, input_schema: Any) -> dict[str, Any]:
    """Rewrite vendor file descriptors as paths and remember their argument paths."""
    if not isinstance(input_schema, dict):
        _FILE_INPUTS[name] = ()
        return {}
    _FILE_INPUTS[name] = tuple(dict.fromkeys(_file_paths(input_schema, input_schema, (), 0)))
    return _as_model_schema(input_schema)


def _as_model_schema(node: Any) -> Any:
    if isinstance(node, list):
        return [_as_model_schema(item) for item in node]
    if not isinstance(node, dict):
        return node
    if node.get("file_uploadable") is True:
        description = f"{node.get('description') or ''} {FILE_INPUT_NOTE}".strip()
        return {"type": "string", "description": description}
    return {key: _as_model_schema(value) for key, value in node.items()}


def _resolve_local_ref(node: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    ref = node.get("$ref")
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return node
    target: Any = root
    for part in ref[2:].split("/"):
        if not isinstance(target, dict):
            return node
        target = target.get(part.replace("~1", "/").replace("~0", "~"))
    return target if isinstance(target, dict) else node


def _file_paths(node: Any, root: dict[str, Any], path: Path_, depth: int) -> Iterator[Path_]:
    if not isinstance(node, dict) or depth > _MAX_SCHEMA_DEPTH:
        return
    node = _resolve_local_ref(node, root)
    if node.get("file_uploadable") is True:
        yield path
        return
    for branch in ("anyOf", "oneOf", "allOf"):
        for option in node.get(branch) or ():
            yield from _file_paths(option, root, path, depth + 1)
    properties = node.get("properties")
    if isinstance(properties, dict):
        for key, child in properties.items():
            yield from _file_paths(child, root, (*path, key), depth + 1)
    yield from _file_paths(node.get("items"), root, (*path, _ARRAY_ITEM), depth + 1)


def _known_file_inputs(client: Any, plan: PlannedCall) -> tuple[Path_, ...]:
    if plan.name in _FILE_INPUTS:
        return _FILE_INPUTS[plan.name]
    parsed = parse_connector_name(plan.name)
    if parsed is None:
        return ()
    candidates = vendor_slug_candidates(parsed.connector, parsed.tool)
    try:
        schemas = (client.schemas(list(candidates)) or {}).get("schemas") or {}
    except Exception as exc:
        logger.debug("connector %s: file-input schema lookup unavailable (%s)", plan.name, type(exc).__name__)
        return ()
    schema = next((schemas[slug] for slug in candidates if isinstance(schemas.get(slug), dict)), {})
    model_parameters(plan.name, schema.get("input_schema") or {})
    return _FILE_INPUTS[plan.name]


# ── input staging ───────────────────────────────────────────────────────────
def stage_inputs(client: Any, plan: PlannedCall, *, task_id: Optional[str]) -> PlannedCall:
    paths = _known_file_inputs(client, plan)
    if not paths:
        return plan
    arguments = plan.arguments
    for path in paths:
        arguments = _substitute(arguments, path, lambda raw: _stage_one(client, plan, raw, task_id))
    return dataclass_replace(plan, arguments=arguments)


def _substitute(value: Any, path: Sequence[str], stage) -> Any:
    if not path:
        if isinstance(value, str):
            return stage(value)
        if isinstance(value, Mapping) and not isinstance(value, _Staged) and "s3key" in value:
            raise FileInputError(
                "FILE_NOT_ALLOWED", "File inputs take a local file path, not a storage descriptor.",
                hint="Pass the path of the local file to send.",
            )
        return value
    head, rest = path[0], path[1:]
    if head == _ARRAY_ITEM:
        return [_substitute(item, rest, stage) for item in value] if isinstance(value, list) else value
    if isinstance(value, Mapping) and head in value:
        return {**value, head: _substitute(value[head], rest, stage)}
    return value


def _stage_one(client: Any, plan: PlannedCall, raw: str, task_id: Optional[str]) -> dict[str, str]:
    path = _readable_file(raw, task_id)
    data = _read_bytes(raw, path)
    filename = Path(path).name[-255:]
    mimetype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    try:
        staged = client.stage_file(
            toolkit=plan.connector.lower(), tool=plan.tool, filename=filename,
            mimetype=mimetype, size=len(data),
        )
    except ToolGatewayError as exc:
        raise FileInputError("FILE_UPLOAD_FAILED", f"The tool gateway could not stage {filename}: {exc}") from exc
    try:
        client.put_file(staged["upload_url"], staged["headers"], data)
    except ToolGatewayError as exc:
        raise FileInputError("FILE_UPLOAD_FAILED", f"Uploading {filename} to storage failed: {exc}") from exc
    return _Staged(staged["descriptor"])


def _readable_file(raw: str, task_id: Optional[str]) -> str:
    from gateway.platforms.base import validate_media_delivery_path
    from gateway.session_context import get_session_env

    candidate = _backend_path(raw, task_id)
    allowed = validate_media_delivery_path(candidate, session_key=get_session_env("ANAKOT_SESSION_KEY", ""))
    if allowed:
        return allowed
    if not Path(candidate).is_file():
        raise FileInputError("FILE_NOT_FOUND", f"{raw} is not a regular file on this machine.", hint="Pass an existing file path.")
    raise FileInputError(
        "FILE_NOT_ALLOWED", f"{raw} may not leave this machine: the file-sending policy refused it.",
        hint="Use a file under an allowed media/download directory.",
    )


def _backend_path(raw: str, task_id: Optional[str]) -> str:
    from tools.file_tools_paths import _resolve_path_for_task, _terminal_env_type_for_task

    task = task_id or "default"
    backend = _terminal_env_type_for_task(task)
    if backend not in _HOST_READABLE_BACKENDS:
        raise FileInputError(
            "FILE_NOT_ALLOWED", f"Files in the {backend} terminal backend are not on this machine.",
            hint="Use a file on this machine, or switch to local/Docker terminal execution.",
        )
    return str(_resolve_path_for_task(raw, task))


def _read_bytes(raw: str, path: str) -> bytes:
    try:
        size = os.path.getsize(path)
        if size > CONNECTOR_FILE_MAX_BYTES:
            raise FileInputError(
                "FILE_TOO_LARGE",
                f"{raw} is larger than the connector limit of {CONNECTOR_FILE_MAX_BYTES // (1024 * 1024)} MiB.",
            )
        data = Path(path).read_bytes()
    except FileInputError:
        raise
    except OSError as exc:
        raise FileInputError("FILE_NOT_FOUND", f"{raw} could not be read: {exc.strerror or exc}.") from exc
    if not data:
        raise FileInputError("FILE_NOT_FOUND", f"{raw} is empty.")
    return data


# ── output downloads ────────────────────────────────────────────────────────
def save_outputs(client: Any, result: Any) -> Any:
    if not isinstance(result, Mapping) or result.get("error") is not None or result.get("data") is None:
        return result
    return {**result, "data": _saved(client, result["data"])}


def _saved(client: Any, value: Any) -> Any:
    if isinstance(value, list):
        return [_saved(client, item) for item in value]
    if not isinstance(value, Mapping):
        return value
    if _is_file_output(value):
        return _download(client, value)
    return {key: _saved(client, item) for key, item in value.items()}


def _is_file_output(value: Mapping[str, Any]) -> bool:
    return all(isinstance(value.get(key), str) for key in ("name", "mimetype", "url")) and value["url"].startswith(("https://", "http://"))


def _download(client: Any, file: Mapping[str, Any]) -> dict[str, Any]:
    kept = {key: item for key, item in file.items() if key not in ("url", "expiresAt", "expires_at")}
    try:
        kept["path"] = _fetch_to_downloads(client, file["url"], file["name"])
    except (ToolGatewayError, OSError) as exc:
        logger.warning("connector file download of %s failed: %s", _safe_name(file["name"]), type(exc).__name__)
        kept["error"] = f"download failed: {exc}"
    return kept


def _fetch_to_downloads(client: Any, url: str, name: str) -> str:
    from anakot_constants import CONNECTOR_DOWNLOADS_SUBDIR, get_anakot_home, mkdir_under_anakot_home

    folder = mkdir_under_anakot_home(get_anakot_home() / CONNECTOR_DOWNLOADS_SUBDIR)
    handle = tempfile.NamedTemporaryFile(dir=folder, prefix=".partial-", delete=False)
    try:
        with handle:
            client.get_file(url, handle.write, max_bytes=DOWNLOAD_MAX_BYTES)
        target = _reserve_name(folder, _safe_name(name))
        os.replace(handle.name, target)
        return str(target)
    finally:
        Path(handle.name).unlink(missing_ok=True)


def _reserve_name(folder: Path, name: str) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    stem, suffix = os.path.splitext(name)
    for attempt in range(1000):
        target = folder / (f"{stamp}-{name}" if attempt == 0 else f"{stamp}-{stem}-{attempt}{suffix}")
        try:
            target.open("xb").close()
        except FileExistsError:
            continue
        return target
    raise FileExistsError(f"no free name for {name}")


def _safe_name(name: str) -> str:
    base = re.split(r"[\\/]", name)[-1]
    cleaned = _UNSAFE_NAME_CHARS.sub("_", base).strip().strip(".")
    return cleaned[-_MAX_NAME_CHARS:] or "file"
