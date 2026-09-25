"""Free Model Suite plugin API.

A thin namespace around Anakot's canonical model inventory and assignment paths,
plus a stateless one-shot completion used to test a candidate before applying it.
The plugin owns no model/provider policy of its own.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent.auxiliary_client import resolve_provider_client
from anakot_cli.inventory import build_model_options_payload, load_picker_context
from anakot_cli.web_models import ModelAssignment
from anakot_cli.web_routers.models import set_model_assignment
from anakot_cli.web_server_profiles import _config_profile_scope

log = logging.getLogger(__name__)
router = APIRouter()


class ApplyModelRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=200)
    model: str = Field(min_length=1, max_length=300)
    confirm_expensive_model: bool = False


class ProbeRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=200)
    model: str = Field(min_length=1, max_length=300)
    prompt: str = Field(min_length=1, max_length=1000)
    system: Optional[str] = Field(default=None, max_length=4000)
    max_tokens: Optional[int] = Field(default=1024, ge=1, le=4096)
    timeout_s: Optional[float] = Field(default=30.0, ge=1, le=120)


@router.get("/catalog")
async def catalog(refresh: bool = False, profile: Optional[str] = None) -> dict[str, Any]:
    """Configured providers and their current inventory, under the requested profile."""
    def build() -> dict[str, Any]:
        with _config_profile_scope(profile):
            return build_model_options_payload(
                load_picker_context(),
                explicit_only=False,
                include_unconfigured=False,
                refresh=bool(refresh),
            )

    return await asyncio.to_thread(build)


@router.post("/models")
async def apply_model(
    body: ApplyModelRequest,
    profile: Optional[str] = None,
) -> dict[str, Any]:
    """Apply a provider/model through the same guarded contract as core Settings."""
    provider = body.provider.strip()
    model = body.model.strip()
    if not provider or not model:
        raise HTTPException(status_code=400, detail="provider and model are required")

    assignment = ModelAssignment(
        scope="main",
        provider=provider,
        model=model,
        confirm_expensive_model=body.confirm_expensive_model,
    )
    return await set_model_assignment(assignment, profile=profile)


@router.post("/probe")
async def probe(body: ProbeRequest, profile: Optional[str] = None) -> dict[str, Any]:
    """Run one stateless completion against an explicit provider/model pair."""
    provider = body.provider.strip().lower()
    model = body.model.strip()
    prompt = body.prompt.strip()
    if not provider or not model or not prompt:
        raise HTTPException(status_code=400, detail="provider, model, and prompt are required")

    with _config_profile_scope(profile):
        try:
            client, resolved_model = resolve_provider_client(provider, model=model, async_mode=True)
        except Exception as exc:
            log.exception("free-model-suite: failed to resolve provider")
            raise HTTPException(status_code=502, detail=f"failed to resolve provider: {exc}") from exc

        if client is None or not resolved_model:
            raise HTTPException(
                status_code=400,
                detail=f"provider '{provider}' is not configured — check its API key or sign-in",
            )

        messages = ([{"role": "system", "content": body.system}] if body.system else []) + [
            {"role": "user", "content": prompt}
        ]
        timeout_s = max(1.0, float(body.timeout_s or 30.0))
        request = {
            "model": resolved_model,
            "messages": messages,
            "max_tokens": max(1, int(body.max_tokens or 256)),
            "stream": False,
        }

        try:
            result = await asyncio.wait_for(
                client.chat.completions.create(**request),
                timeout=timeout_s,
            )
        except asyncio.TimeoutError as exc:
            raise HTTPException(status_code=504, detail=f"probe timed out after {timeout_s:.0f}s") from exc
        except httpx.ConnectError as exc:
            raise HTTPException(status_code=502, detail=f"cannot connect to provider: {exc}") from exc
        except HTTPException:
            raise
        except Exception as exc:
            message = str(exc)
            detail = message.rsplit("Error: ", 1)[-1] if "Error: " in message else message
            log.exception("free-model-suite: provider probe failed")
            raise HTTPException(status_code=502, detail=f"provider error: {detail or exc!r}") from exc

    try:
        choice = result.choices[0]
        message = choice.message
        content = message.content or ""
        if not isinstance(content, str):
            content = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )

        reasoning_parts: list[str] = []
        for field in ("reasoning", "reasoning_content"):
            value = getattr(message, field, None)
            if isinstance(value, str) and value.strip() and value.strip() not in reasoning_parts:
                reasoning_parts.append(value.strip())
        details = getattr(message, "reasoning_details", None)
        if isinstance(details, list):
            for detail in details:
                if not isinstance(detail, dict):
                    continue
                value = detail.get("summary") or detail.get("content") or detail.get("text")
                text = value.strip() if isinstance(value, str) else str(value) if value else ""
                if text and text not in reasoning_parts:
                    reasoning_parts.append(text)

        tool_calls = []
        for call in getattr(message, "tool_calls", None) or []:
            function = getattr(call, "function", None)
            tool_calls.append({
                "name": getattr(function, "name", "") or "",
                "arguments": getattr(function, "arguments", "") or "",
            })

        return {
            "ok": True,
            "provider": provider,
            "model": resolved_model,
            "content": content,
            "reasoning": "\n\n".join(reasoning_parts),
            "finish_reason": getattr(choice, "finish_reason", None),
            "tool_calls": tool_calls,
        }
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("free-model-suite: could not parse provider response")
        raise HTTPException(status_code=502, detail=f"unparseable provider response: {exc}") from exc
