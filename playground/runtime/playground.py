# Copyright (c) Microsoft. All rights reserved.
"""Deployment-owned Portal access, workspace isolation, and usage limits."""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import html
import json
import re
import secrets
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

from aiohttp import web

USER_KEY = web.RequestKey("playground_user", str)
NEW_COOKIE_KEY = web.RequestKey("playground_new_cookie", str)
NEW_ACCESS_COOKIE_KEY = web.RequestKey("playground_new_access_cookie", str)
WORKSPACE_COOKIE = "voice_playground_workspace"
ACCESS_COOKIE = "__Host-voice_playground_access"
AGENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$")
EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)
TENANT_CLAIM = "http://schemas.microsoft.com/identity/claims/tenantid"
OBJECT_CLAIM = "http://schemas.microsoft.com/identity/claims/objectidentifier"
HOSTING_ROOT = Path(__file__).parent / "hosting"


def policy(request: web.Request) -> PlaygroundPolicy | None:
    return request.app[POLICY_KEY] if POLICY_KEY in request.app else None


def scoped_agent_name(request: web.Request, name: str) -> str:
    configured = policy(request)
    return configured.agent_name(request, name) if configured else name


@dataclass
class PlaygroundPolicy:
    origin: str
    mcp_url: str
    auth_mode: str = "tenant"
    tenant_id: str = ""
    cookie_key: str = ""
    invitation_hash: str = ""
    invitation_expires_at: int = 0
    model: str = "gpt-realtime"
    session_seconds: int = 300
    access_cookie_days: int = 365
    allow_custom_mcp: bool = True
    enabled: bool = False
    _allowed_models: set[str] = field(default_factory=set, init=False, repr=False)
    _mcp_bindings: dict[tuple[str, str], set[str]] = field(
        default_factory=dict, init=False, repr=False,
    )
    _mcp_presets: list[dict[str, str]] = field(
        default_factory=list, init=False, repr=False,
    )

    def __post_init__(self) -> None:
        parsed = urlsplit(self.origin)
        if (
            parsed.scheme != "https" or not parsed.hostname
            or parsed.username or parsed.password or parsed.path
            or parsed.query or parsed.fragment or parsed.port not in (None, 443)
        ):
            raise ValueError("Playground origin must be an HTTPS origin without a path.")
        if self.auth_mode not in {"tenant", "anonymous", "invite"}:
            raise ValueError("Playground auth mode must be tenant, anonymous, or invite.")
        if self.auth_mode == "tenant":
            self.tenant_id = str(uuid.UUID(self.tenant_id))
        elif len(self.cookie_key.encode("utf-8")) < 32:
            raise ValueError("Playground cookie key must be at least 32 bytes.")
        if self.auth_mode == "invite":
            self.invitation_hash = self.invitation_hash.strip().lower()
            if not re.fullmatch(r"[0-9a-f]{64}", self.invitation_hash):
                raise ValueError("Invitation mode requires a SHA-256 invitation hash.")
            if self.invitation_expires_at <= 0:
                raise ValueError("Invitation mode requires a positive expiry timestamp.")
        if self.mcp_url:
            self._validate_mcp_url(self.mcp_url)
        if not 1 <= self.session_seconds <= 600:
            raise ValueError("Playground sessions must last 1-600 seconds.")
        if not 1 <= self.access_cookie_days <= 400:
            raise ValueError("Playground access cookies must last 1-400 days.")

    @staticmethod
    def _validate_mcp_url(value: str) -> None:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https" or not parsed.hostname
            or parsed.username or parsed.password
            or parsed.query or parsed.fragment
        ):
            raise ValueError("Playground MCP must be a public HTTPS URL without credentials.")

    @staticmethod
    def _iter_mcp_tools(value: Any):
        if isinstance(value, dict):
            if value.get("type") == "mcp":
                yield value
            for child in value.values():
                yield from PlaygroundPolicy._iter_mcp_tools(child)
        elif isinstance(value, list):
            for child in value:
                yield from PlaygroundPolicy._iter_mcp_tools(child)

    def configure_catalog(self, catalog) -> None:
        bindings: dict[tuple[str, str], set[str]] = {}
        presets: dict[tuple[str, str], dict[str, str]] = {}
        models: set[str] = set()
        for card in catalog.cards():
            for version in card["versions"]:
                source = catalog.source(card["id"], version["id"])
                document = catalog.document(card["id"], version["id"])
                if source is None or document is None:
                    raise ValueError(
                        f"Hosted template '{card['id']}' version '{version['id']}' could not be loaded."
                    )
                definition = document["definition"]
                model = str(definition.get("model") or "").strip()
                if model:
                    models.add(model)
                tools = list(self._iter_mcp_tools(definition))
                if not tools:
                    continue
                self._validate_mcp_url(source.mcp_server_url)
                connection = (
                    "" if source.connection_mode == "public"
                    else source.mcp_connection_id
                )
                if source.connection_mode != "public" and not connection:
                    raise ValueError(
                        f"Hosted template '{card['id']}' requires an existing MCP connection."
                    )
                key = (source.mcp_server_url, connection)
                allowed = bindings.setdefault(key, set())
                for tool in tools:
                    allowed.update(
                        str(name) for name in tool.get("allowed_tools") or [] if name
                    )
                presets.setdefault(key, {
                    "value": f"hosted-{card['id']}",
                    "label": str(source.source_label or card["name"]),
                    "mode": "connection" if connection else "url",
                    "server_label": str(tools[0].get("server_label") or "mcp"),
                    "server_url": source.mcp_server_url,
                    "project_connection_id": connection,
                })
        if not bindings:
            raise ValueError("Hosted playground requires at least one approved MCP binding.")
        self._allowed_models = models
        self._mcp_bindings = bindings
        self._mcp_presets = list(presets.values())

    @property
    def models(self) -> list[str]:
        return list(dict.fromkeys([self.model, *sorted(self._allowed_models)]))

    @property
    def mcp_presets(self) -> list[dict[str, str]]:
        return [dict(value) for value in self._mcp_presets]

    def allows_mcp(
        self,
        server_url: str,
        connection_id: str,
        allowed_tools: list[str],
    ) -> bool:
        approved = self._mcp_bindings.get((server_url, connection_id))
        if approved:
            return bool(allowed_tools) and all(name in approved for name in allowed_tools)
        return self._allows_custom_mcp(server_url, connection_id, allowed_tools)

    def _allows_custom_mcp(
        self,
        server_url: str,
        connection_id: str,
        allowed_tools: list[str],
    ) -> bool:
        """A user's own public MCP server: HTTPS without credentials, no Project connection."""
        if not self.allow_custom_mcp or connection_id or not allowed_tools:
            return False
        try:
            self._validate_mcp_url(server_url)
        except ValueError:
            return False
        return True

    def authenticate(self, request: web.Request) -> None:
        if not self.enabled:
            raise web.HTTPServiceUnavailable(
                text="Playground ingress is locked until deployment configuration is verified.",
            )
        if request.host.lower() != urlsplit(self.origin).netloc.lower():
            raise web.HTTPForbidden(text="Unexpected playground host.")
        if self.auth_mode == "invite":
            self._authenticate_invite(request)
            return
        if self.auth_mode == "anonymous":
            self._authenticate_anonymous(request)
            return
        encoded = request.headers.get("X-MS-CLIENT-PRINCIPAL", "")
        try:
            if not encoded or len(encoded) > 32 * 1024:
                raise ValueError
            principal = json.loads(base64.b64decode(encoded, validate=True))
            if not isinstance(principal, dict) or principal.get("auth_typ") != "aad":
                raise ValueError
            raw_claims = principal.get("claims")
            if not isinstance(raw_claims, list):
                raise ValueError
            claims = {}
            for claim in raw_claims:
                if not isinstance(claim, dict):
                    raise ValueError
                key, value = claim.get("typ"), claim.get("val")
                if not isinstance(key, str) or not isinstance(value, str):
                    raise ValueError
                if key in claims and claims[key] != value:
                    raise ValueError
                claims[key] = value
            tenant = str(uuid.UUID(claims.get("tid") or claims.get(TENANT_CLAIM, "")))
            subject = str(uuid.UUID(claims.get("oid") or claims.get(OBJECT_CLAIM, "")))
            if tenant != self.tenant_id:
                raise ValueError
        except (ValueError, TypeError, binascii.Error, UnicodeError, RecursionError) as error:
            raise web.HTTPUnauthorized(
                text="Sign in with this playground's Microsoft Entra tenant.",
            ) from error
        request[USER_KEY] = hashlib.sha256(f"{tenant}:{subject}".encode()).hexdigest()[:16]

    def _access_signature(self, subject: str, expires: int) -> str:
        payload = f"email-access:v2:{self.origin}:{subject}:{expires}"
        return hmac.new(
            self.cookie_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256,
        ).hexdigest()

    def _authenticate_invite(self, request: web.Request) -> None:
        now = int(time.time())
        token = request.cookies.get(ACCESS_COOKIE, "")
        try:
            version, subject, expires_text, signature = token.split(".", 3)
            expires = int(expires_text)
            if (
                version == "v2"
                and re.fullmatch(r"[0-9a-f]{24}", subject)
                and now < expires
                and re.fullmatch(r"[0-9a-f]{64}", signature)
                and hmac.compare_digest(
                    signature, self._access_signature(subject, expires),
                )
            ):
                request[USER_KEY] = subject
                return
        except ValueError:
            pass
        if (
            request.method == "GET"
            and "text/html" in request.headers.get("Accept", "")
            and request.headers.get("Upgrade", "").lower() != "websocket"
        ):
            target = quote(request.rel_url.raw_path_qs, safe="")
            raise web.HTTPSeeOther(location=f"/login?next={target}")
        raise web.HTTPUnauthorized(
            text="Sign in with the shared playground token and your email.",
        )

    @staticmethod
    def _safe_next(value: str) -> str:
        return value if value.startswith("/") and not value.startswith("//") else "/"

    @staticmethod
    def _normalize_email(value: str) -> str:
        normalized = value.strip().casefold()
        if (
            len(normalized) > 254
            or not normalized.isascii()
            or not EMAIL_PATTERN.fullmatch(normalized)
        ):
            raise ValueError("Enter a valid email address.")
        return normalized

    def _login_html(
        self,
        *,
        email: str = "",
        next_path: str = "/",
        error: str = "",
    ) -> str:
        error_html = (
            f'<div class="error" role="alert">{html.escape(error)}</div>'
            if error else ""
        )
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sign in - Voice Agent Playground</title>
  <style>
    :root {{ color-scheme: light; font-family: "Segoe UI", system-ui, sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{
      min-height: 100vh; margin: 0; display: grid; place-items: center; padding: 24px;
      color: #172033; background:
        radial-gradient(circle at 12% 18%, #dcecff 0, transparent 34%),
        radial-gradient(circle at 86% 82%, #e6ddff 0, transparent 32%), #f7f9fc;
    }}
    main {{
      width: min(100%, 460px); padding: 38px; border: 1px solid #dfe5ef;
      border-radius: 20px; background: rgba(255,255,255,.94);
      box-shadow: 0 24px 70px rgba(37, 55, 88, .14);
    }}
    .mark {{
      width: 46px; height: 46px; display: grid; place-items: center; border-radius: 13px;
      color: white; font-size: 24px; font-weight: 700;
      background: linear-gradient(135deg, #1769e0, #7248d8);
    }}
    h1 {{ margin: 22px 0 8px; font-size: 28px; letter-spacing: -.02em; }}
    p {{ margin: 0 0 24px; color: #59657a; line-height: 1.55; }}
    label {{ display: block; margin: 0 0 8px; font-weight: 600; }}
    input {{
      width: 100%; height: 46px; padding: 0 13px; border: 1px solid #adb8ca;
      border-radius: 9px; font: inherit; outline: none;
    }}
    input:focus {{ border-color: #1769e0; box-shadow: 0 0 0 3px #1769e026; }}
    .field + .field {{ margin-top: 18px; }}
    .actions {{ display: flex; gap: 10px; margin-top: 22px; }}
    button {{
      min-height: 44px; padding: 0 18px; border: 0; border-radius: 9px;
      font: inherit; font-weight: 650; cursor: pointer;
    }}
    .primary {{ margin-left: auto; color: white; background: #1769e0; }}
    .error {{
      margin-bottom: 20px; padding: 12px 14px; border: 1px solid #e8a6a6;
      border-radius: 9px; color: #8b1f1f; background: #fff2f2;
    }}
    .hint {{ margin-top: 18px; font-size: 13px; color: #6a7588; }}
    .contact {{ margin: 18px 0 0; font-size: 14px; overflow-wrap: anywhere; }}
    .contact a {{ color: #1769e0; }}
  </style>
</head>
<body>
  <main>
    <div class="mark" aria-hidden="true">V</div>
    <h1>Voice Agent Playground</h1>
    <p>Sign in with the shared access token and your email address.</p>
    {error_html}
    <form method="post" action="/login">
      <input type="hidden" name="next" value="{html.escape(next_path, quote=True)}">
      <div class="field">
        <label for="token">Access token</label>
        <input id="token" name="token" type="password" required maxlength="256"
               autocomplete="one-time-code" autofocus>
      </div>
      <div class="field">
        <label for="email">Email address</label>
        <input id="email" name="email" type="email" required maxlength="254"
               autocomplete="email" value="{html.escape(email, quote=True)}">
      </div>
      <div class="actions">
        <button class="primary" type="submit">Sign in</button>
      </div>
    </form>
    <div class="hint">This browser stays signed in for up to {self.access_cookie_days} days.
      Clearing browser cookies requires signing in again.</div>
    <p class="contact">Need an access token or help? Contact
      <a href="mailto:yiwenrong@microsoft.com">yiwenrong@microsoft.com</a>.</p>
  </main>
</body>
</html>"""

    async def public_response(self, request: web.Request) -> web.StreamResponse:
        if request.path == "/healthz":
            return web.json_response({"status": "ok"})
        if not self.enabled:
            raise web.HTTPServiceUnavailable(
                text="Playground ingress is locked until deployment configuration is verified.",
            )
        if self.auth_mode != "invite":
            raise web.HTTPNotFound()
        if request.host.lower() != urlsplit(self.origin).netloc.lower():
            raise web.HTTPForbidden(text="Unexpected playground host.")
        origin = request.headers.get("Origin")
        fetch_site = request.headers.get("Sec-Fetch-Site", "")
        browser_same_origin = origin == "null" and fetch_site == "same-origin"
        if origin is not None and origin != self.origin and not browser_same_origin:
            raise web.HTTPForbidden(text="Cross-origin requests are not allowed.")
        if fetch_site == "cross-site":
            raise web.HTTPForbidden(text="Cross-site requests are not allowed.")

        next_path = self._safe_next(
            request.query.get("next", "/") if request.method == "GET" else "/"
        )
        if request.method == "GET":
            try:
                self._authenticate_invite(request)
            except (web.HTTPUnauthorized, web.HTTPSeeOther):
                return web.Response(
                    text=self._login_html(next_path=next_path),
                    content_type="text/html",
                )
            raise web.HTTPSeeOther(location=next_path)
        if request.method != "POST":
            raise web.HTTPMethodNotAllowed(request.method, {"GET", "POST"})
        if request.content_type != "application/x-www-form-urlencoded":
            raise web.HTTPUnsupportedMediaType(text="Login requires an HTML form.")
        form = await request.post()
        email = str(form.get("email") or "")
        token = str(form.get("token") or "")
        next_path = self._safe_next(str(form.get("next") or "/"))
        try:
            normalized = self._normalize_email(email)
            if (
                int(time.time()) >= self.invitation_expires_at
                or not 16 <= len(token) <= 256
                or not hmac.compare_digest(
                    hashlib.sha256(token.encode("utf-8")).hexdigest(),
                    self.invitation_hash,
                )
            ):
                raise ValueError
        except ValueError:
            return web.Response(
                text=self._login_html(
                    email=email,
                    next_path=next_path,
                    error="The access token is invalid or expired, or the email is not valid.",
                ),
                status=401,
                content_type="text/html",
            )
        subject = hashlib.sha256(
            f"email:{normalized}".encode("utf-8"),
        ).hexdigest()[:24]
        request[USER_KEY] = subject
        expires = int(time.time()) + self.access_cookie_days * 24 * 60 * 60
        request[NEW_ACCESS_COOKIE_KEY] = (
            f"v2.{subject}.{expires}.{self._access_signature(subject, expires)}"
        )
        response = web.HTTPSeeOther(location=next_path)
        self.set_response_cookies(request, response)
        raise response

    def _authenticate_anonymous(self, request: web.Request) -> None:
        token = request.cookies.get(WORKSPACE_COOKIE, "")
        try:
            workspace, signature = token.split(".", 1)
            if (
                not re.fullmatch(r"[A-Za-z0-9_-]{43}", workspace)
                or not re.fullmatch(r"[0-9a-f]{64}", signature)
                or not hmac.compare_digest(
                    signature,
                    hmac.new(
                        self.cookie_key.encode("utf-8"),
                        workspace.encode("ascii"),
                        hashlib.sha256,
                    ).hexdigest(),
                )
            ):
                raise ValueError
        except ValueError:
            if request.headers.get("Upgrade", "").lower() == "websocket":
                raise web.HTTPUnauthorized(text="Open the playground page before starting voice.")
            workspace = secrets.token_urlsafe(32)
            signature = hmac.new(
                self.cookie_key.encode("utf-8"),
                workspace.encode("ascii"),
                hashlib.sha256,
            ).hexdigest()
            request[NEW_COOKIE_KEY] = f"{workspace}.{signature}"
        request[USER_KEY] = hashlib.sha256(workspace.encode("ascii")).hexdigest()[:16]

    def set_response_cookies(
        self,
        request: web.Request,
        response: web.StreamResponse,
    ) -> None:
        access_token = request.get(NEW_ACCESS_COOKIE_KEY)
        if access_token and isinstance(response, web.Response):
            expires = int(access_token.split(".", 3)[2])
            response.set_cookie(
                ACCESS_COOKIE,
                access_token,
                httponly=True,
                secure=True,
                samesite="Lax",
                max_age=max(0, expires - int(time.time())),
                path="/",
            )
            if self.auth_mode == "invite":
                response.del_cookie(
                    WORKSPACE_COOKIE,
                    secure=True,
                    httponly=True,
                    samesite="Lax",
                    path="/",
                )
        token = request.get(NEW_COOKIE_KEY)
        if token and isinstance(response, web.Response):
            response.set_cookie(
                WORKSPACE_COOKIE,
                token,
                httponly=True,
                secure=True,
                samesite="Lax",
                max_age=24 * 60 * 60,
                path="/",
            )

    def prefix(self, request: web.Request) -> str:
        return f"pg-{request[USER_KEY]}-"

    def agent_name(self, request: web.Request, name: str) -> str:
        if not AGENT_PATTERN.fullmatch(name):
            raise web.HTTPBadRequest(text="Invalid Agent name.")
        prefix = self.prefix(request)
        if name.startswith("pg-") and not name.startswith(prefix):
            raise web.HTTPNotFound(text="Unknown playground Agent.")
        if name.startswith(prefix):
            return name
        available = 63 - len(prefix)
        if len(name) > available:
            digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
            name = f"{name[:available - 9].rstrip('-._')}-{digest}"
        result = prefix + name
        return result

    async def dispatch(self, request: web.Request, handler):
        if request.path in {"/agents:generate", "/foundry-trace"}:
            raise web.HTTPForbidden(text="This operation is disabled in the shared playground.")
        return await handler(request)

    def service_path(self, request: web.Request) -> str:
        name = request.match_info.get("agent")
        if not name:
            return request.rel_url.raw_path
        scoped = self.agent_name(request, name)
        suffix = request.path.split("/", 3)[3:]  # route has already validated components
        return f"/agents/{quote(scoped, safe='')}" + (
            "/" + quote(suffix[0], safe="/") if suffix else ""
        )

    def service_query(self, request: web.Request) -> dict[str, str]:
        query = dict(request.query)
        allowed = {"api-version", "backend", "kind", "limit"}
        if set(query) - allowed:
            raise web.HTTPBadRequest(text="Unsupported playground service query parameter.")
        query.pop("backend", None)
        query["api-version"] = "v1"
        if request.path == "/agents":
            query["kind"] = "voice"
            try:
                limit = int(query.get("limit", "25"))
            except ValueError as error:
                raise web.HTTPBadRequest(text="Invalid page size.") from error
            if not 1 <= limit <= 100:
                raise web.HTTPBadRequest(text="Page size must be between 1 and 100.")
            query["limit"] = str(limit)
        return query

    def filter_agents(self, request: web.Request, payload: dict) -> dict:
        data = payload.get("data")
        if not isinstance(data, list):
            raise web.HTTPBadGateway(text="Foundry returned an invalid Agent list.")
        own = [
            item for item in data
            if isinstance(item, dict)
            and str(item.get("name", "")).startswith(self.prefix(request))
        ]
        last_id = str(own[-1].get("name", "")) if own else ""
        return {
            "object": "list", "data": own, "has_more": False,
            "first_id": str(own[0].get("name", "")) if own else "",
            "last_id": last_id,
        }

    def validate_definition(self, definition: dict) -> None:
        if not isinstance(definition, dict) or definition.get("kind") != "voice":
            raise web.HTTPBadRequest(text="The playground only publishes Voice Agents.")
        if (
            definition.get("model_type") != "managed"
            or definition.get("model") not in self._allowed_models
        ):
            raise web.HTTPBadRequest(
                text="Use one of the managed models approved by the hosted Template catalog."
            )
        forbidden = {
            "authorization", "headers", "connection_id",
            "target_agent", "subagent_config", "toolbox", "avatar",
        }
        component_models = {
            "azure-speech", "whisper-1", "smart_end_of_turn_detection",
        }

        def visit(value):
            if isinstance(value, list):
                for child in value:
                    visit(child)
            elif isinstance(value, dict):
                if forbidden.intersection(value):
                    raise web.HTTPBadRequest(
                        text="Connections, credentials, external agents and avatars are disabled in the playground.",
                    )
                if "store" in value and value["store"] is not False:
                    raise web.HTTPBadRequest(text="Conversation storage must be off in the playground.")
                if "model_type" in value and value["model_type"] != "managed":
                    raise web.HTTPBadRequest(text="Only managed models are enabled in the playground.")
                if "model" in value and (
                    not isinstance(value["model"], str)
                    or value["model"] not in self._allowed_models | component_models
                ):
                    raise web.HTTPBadRequest(text="This model is not enabled in the playground.")
                if "tools" in value:
                    tools = value["tools"]
                    if not isinstance(tools, list):
                        raise web.HTTPBadRequest(text="Tools must be an array.")
                    for tool in tools:
                        if not isinstance(tool, dict):
                            raise web.HTTPBadRequest(text="Invalid tool.")
                        if tool.get("type") == "system" and tool.get("name") == "end_conversation":
                            continue
                        names = tool.get("allowed_tools")
                        if not isinstance(names, list) or any(
                            not isinstance(name, str) for name in names
                        ):
                            raise web.HTTPBadRequest(text="Invalid MCP allowed_tools.")
                        if (
                            tool.get("type") != "mcp"
                            or not self.allows_mcp(
                                str(tool.get("server_url") or ""),
                                str(tool.get("project_connection_id") or ""),
                                names,
                            )
                        ):
                            raise web.HTTPBadRequest(
                                text="Use only MCP bindings approved by the hosted Template catalog.",
                            )
                for key, child in value.items():
                    visit(child)

        visit(definition)

    def websocket_query(self, request: web.Request) -> dict[str, str]:
        allowed = {
            "api-version", "backend", "agent_session_id", "store", "transport",
            "version", "agent_version", "voiceOverride", "structured_input",
        }
        if set(request.query) - allowed:
            raise web.HTTPBadRequest(text="Unsupported playground voice query parameter.")
        return {
            **request.query, "api-version": "v1", "store": "false",
            "agent_session_id": f"pg-{uuid.uuid4().hex}",
        }

    def validate_frame(self, raw: str | bytes) -> None:
        if not isinstance(raw, str) or len(raw) > 1024 * 1024:
            raise ValueError("Playground voice frames must be JSON text of at most 1 MiB.")
        frame = json.loads(raw)
        if not isinstance(frame, dict):
            raise ValueError("Expected a voice event object.")
        fields = {
            "input_audio_buffer.append": {"audio"},
            "input_audio_buffer.commit": set(),
            "input_audio_buffer.clear": set(),
            "response.create": set(),
            "response.cancel": {"response_id"},
            "conversation.item.create": {"item", "previous_item_id"},
            "conversation.item.truncate": {"item_id", "content_index", "audio_end_ms"},
            "conversation.item.delete": {"item_id"},
            "rtc.call.sdp.create": {"sdp_offer"},
        }
        event = frame.get("type")
        if not isinstance(event, str) or event not in fields:
            raise ValueError("This voice event is disabled in the playground.")
        if set(frame) - (fields[event] | {"type", "event_id"}):
            raise ValueError("Voice configuration overrides are disabled in the playground.")
        if event == "conversation.item.create":
            item = frame.get("item")
            if not isinstance(item, dict) or not (
                (item.get("type") == "message" and item.get("role") == "user")
                or item.get("type") == "mcp_approval_response"
            ):
                raise ValueError("Only user messages and MCP approvals can be submitted.")


POLICY_KEY = web.AppKey("playground_policy", PlaygroundPolicy)
