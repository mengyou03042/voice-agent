"""Privacy-bounded usage telemetry for the independently hosted Playground."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Collection
from contextlib import suppress
from datetime import datetime, timezone
import hashlib
import json
import logging
import re
import time
from typing import Literal
import uuid

from aiohttp import web

try:
    from .playground import AGENT_PATTERN, USER_KEY
except ImportError:
    from playground import AGENT_PATTERN, USER_KEY


LOGGER = logging.getLogger("voice_agent_portal")
LOG_MARKER = "PLAYGROUND_USAGE "
HEARTBEAT_SECONDS = 60
UsageEvent = Literal["heartbeat", "login", "activity", "agent_publish"]
UsageValue = str | int | None
Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]


def _emit(event_name: UsageEvent, fields: dict[str, UsageValue]) -> None:
    record = {
        "schema_version": 1,
        "event_id": uuid.uuid4().hex,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "event_name": event_name,
        **fields,
    }
    LOGGER.info("%s%s", LOG_MARKER, json.dumps(record, separators=(",", ":"), sort_keys=True))


def _publication_metadata(
    request: web.Request,
    response: web.StreamResponse,
    template_ids: Collection[str],
) -> dict[str, UsageValue]:
    fields: dict[str, UsageValue] = {
        "agent_id": None, "version": None, "change": "unknown",
        "metadata_status": "not_available",
    }
    template = request.match_info.get("template_id", "")
    fields["template_id"] = template if template in template_ids else None
    if not 200 <= response.status < 300:
        return fields
    if not isinstance(response, web.Response) or not isinstance(response.body, bytes):
        fields["metadata_status"] = "missing"
        return fields
    try:
        payload = json.loads(response.body)
    except (ValueError, UnicodeError):
        fields["metadata_status"] = "invalid"
        return fields
    if not isinstance(payload, dict):
        fields["metadata_status"] = "invalid"
        return fields
    name = payload.get("name") or payload.get("agent_name")
    version = payload.get("version")
    if (
        not isinstance(name, str)
        or not AGENT_PATTERN.fullmatch(name)
        or not name.startswith(f"pg-{request.get(USER_KEY, '')}-")
        or isinstance(version, bool)
        or not isinstance(version, (str, int))
        or not re.fullmatch(r"[1-9][0-9]{0,8}", str(version))
    ):
        fields["metadata_status"] = "missing"
        return fields
    fields.update({
        "agent_id": hashlib.sha256(name.encode("utf-8")).hexdigest(),
        "version": int(version),
        "change": "created" if int(version) == 1 else "version_published",
        "metadata_status": "complete",
    })
    return fields


def _record_response(
    request: web.Request,
    response: web.StreamResponse,
    *,
    started: float,
    request_id_key: web.RequestKey[str],
    template_ids: Collection[str],
) -> None:
    user = request.get(USER_KEY, "")
    fields: dict[str, UsageValue] = {
        "request_id": request.get(request_id_key, ""),
        "traffic_type": (
            "synthetic" if request.headers.get("X-MS-Synthetic-Source", "").strip()
            else "customer"
        ),
        "http_status": response.status,
        "duration_ms": max(0, round((time.monotonic() - started) * 1000)),
        "outcome": "success" if response.status < 400 else "failure",
        "user_id": user or None,
    }
    if request.path == "/login":
        if request.method == "POST":
            fields["outcome"] = "success" if response.status == 303 and user else "failure"
            if fields["outcome"] == "failure":
                fields["user_id"] = None
            _emit("login", fields)
        return
    if (
        not user or request.path == "/healthz"
        or request.path.startswith("/static/")
        or request.headers.get("Upgrade", "").lower() == "websocket"
    ):
        return
    is_publication = request.method == "POST" and (
        bool(re.fullmatch(r"/agents/[^/]+/versions", request.path))
        or bool(re.fullmatch(r"/api/templates/[^/]+/publish", request.path))
    )
    if is_publication:
        fields.update(_publication_metadata(request, response, template_ids))
        fields["outcome"] = "success" if 200 <= response.status < 300 else "failure"
        _emit("agent_publish", fields)
    else:
        fields["category"] = "document" if request.path in {
            "/", "/editor", "/editor/", "/handoff", "/handoff/",
            "/demo", "/demo/", "/templates", "/templates/",
        } else "api"
        _emit("activity", fields)


async def _heartbeat_context(app: web.Application) -> AsyncIterator[None]:
    async def heartbeat() -> None:
        while True:
            _emit("heartbeat", {})
            await asyncio.sleep(HEARTBEAT_SECONDS)

    task = asyncio.create_task(heartbeat(), name="playground-usage-heartbeat")
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


def install_usage_telemetry(
    app: web.Application,
    *,
    request_id_key: web.RequestKey[str],
    template_ids: Collection[str],
) -> None:
    """Observe hosted outcomes without changing the existing admission or API contract."""
    approved_templates = frozenset(template_ids)

    @web.middleware
    async def usage(request: web.Request, handler: Handler) -> web.StreamResponse:
        started = time.monotonic()
        response = None
        try:
            response = await handler(request)
            return response
        except web.HTTPException as error:
            response = error
            raise
        finally:
            if response is not None:
                _record_response(
                    request, response, started=started,
                    request_id_key=request_id_key, template_ids=approved_templates,
                )

    app.middlewares.insert(0, usage)
    app.cleanup_ctx.append(_heartbeat_context)
