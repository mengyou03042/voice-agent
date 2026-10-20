# Copyright (c) Microsoft. All rights reserved.
"""Staged playground HTTP/WebSocket tests with synthetic identities and Azure."""
from __future__ import annotations

import asyncio
import ast
import base64
import hashlib
import inspect
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from aiohttp import WSMsgType, WSServerHandshakeError, web
from aiohttp.test_utils import TestClient, TestServer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from build_context import DEFAULT_PORTAL_SOURCE, stage

PORTAL_SOURCE = Path(os.getenv("VOICE_PLAYGROUND_PORTAL_SOURCE", DEFAULT_PORTAL_SOURCE))
_SOURCE_EXPORT = tempfile.TemporaryDirectory(prefix="voice-playground-tests-")
_CONTEXT = Path(_SOURCE_EXPORT.name) / "context"
stage(_CONTEXT, portal_source=PORTAL_SOURCE)
ROOT = _CONTEXT / "portal"
sys.path.insert(0, str(ROOT))
import demo_server as server
import template_portal
from playground_usage import LOG_MARKER, install_usage_telemetry
from playground import (
    ACCESS_COOKIE, HOSTING_ROOT, OBJECT_CLAIM, USER_KEY, WORKSPACE_COOKIE,
    TENANT_CLAIM, PlaygroundPolicy,
)
import requests


def tearDownModule():
    _SOURCE_EXPORT.cleanup()


ENDPOINT = "https://sample.services.ai.azure.com/api/projects/playground"
ORIGIN = "https://playground.example"
TENANT = "11111111-1111-4111-8111-111111111111"
ALICE = "22222222-2222-4222-8222-222222222222"
BOB = "33333333-3333-4333-8333-333333333333"
INVITATION = "synthetic-invitation-for-private-runtime-tests"
INVITATION_HASH = hashlib.sha256(INVITATION.encode()).hexdigest()
INVITATION_EXPIRES = int(time.time()) + 24 * 60 * 60
ALICE_EMAIL = "alice@example.com"
BOB_EMAIL = "bob@example.com"
ALICE_TOKEN = INVITATION
BOB_TOKEN = INVITATION
PROFILE = HOSTING_ROOT / "profile.json"
TEMPLATE_ID = "finance-example-realtime"
os.environ.setdefault(
    "VOICE_PLAYGROUND_MCP_BASE_URL",
    "https://voice-agent-playground-mcp.example",
)
CATALOG = template_portal.TemplateCatalog(
    template_portal.DEFAULT_TEMPLATE_CONFIG,
    profile_path=PROFILE,
)
SOURCE = CATALOG.source(TEMPLATE_ID)
DOCUMENT = CATALOG.document(TEMPLATE_ID)
assert SOURCE is not None and DOCUMENT is not None
MCP = SOURCE.mcp_server_url
CONNECTION = SOURCE.mcp_connection_id
DEFINITION = template_portal.materialize_template(
    DOCUMENT,
    model="",
    voice="",
    mcp_server_url=MCP,
    mcp_connection_id=CONNECTION,
    mcp_public=True,
)
EXPECTED_TOOLS = frozenset(
    name
    for tool in template_portal.iter_mcp_tools(DEFINITION)
    for name in tool.get("allowed_tools") or []
)


def configured_policy(**overrides):
    values = {
        "origin": ORIGIN,
        "tenant_id": TENANT,
        "mcp_url": "",
        **overrides,
    }
    result = PlaygroundPolicy(**values)
    result.configure_catalog(CATALOG)
    return result


def headers(subject=ALICE, tenant=TENANT, *, long_claims=False):
    claims = [
        {"typ": TENANT_CLAIM if long_claims else "tid", "val": tenant},
        {"typ": OBJECT_CLAIM if long_claims else "oid", "val": subject},
    ]
    encoded = base64.b64encode(json.dumps({"auth_typ": "aad", "claims": claims}).encode()).decode()
    return {
        "Host": "playground.example", "Origin": ORIGIN,
        "X-MS-CLIENT-PRINCIPAL": encoded,
    }


def prefix(subject=ALICE):
    return "pg-" + hashlib.sha256(f"{TENANT}:{subject}".encode()).hexdigest()[:16] + "-"


def email_prefix(email=ALICE_EMAIL):
    subject = hashlib.sha256(f"email:{email}".encode()).hexdigest()[:24]
    return f"pg-{subject}-"


class PlaygroundPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = configured_policy()

    def test_origin_and_bounds_fail_closed(self):
        for origin in ("http://playground.example", ORIGIN + "/", ORIGIN + "?token=x",
                       "https://user:password@playground.example"):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                PlaygroundPolicy(origin=origin, tenant_id=TENANT, mcp_url="")
        with self.assertRaises(ValueError):
            PlaygroundPolicy(
                origin=ORIGIN, tenant_id=TENANT, mcp_url="", session_seconds=0,
            )
        with self.assertRaises(ValueError):
            PlaygroundPolicy(
                origin=ORIGIN, auth_mode="anonymous", cookie_key="short", mcp_url="",
            )
        for days in (0, 401):
            with self.subTest(access_cookie_days=days), self.assertRaises(ValueError):
                PlaygroundPolicy(
                    origin=ORIGIN,
                    tenant_id=TENANT,
                    mcp_url="",
                    access_cookie_days=days,
                )

    def test_only_supported_managed_definitions_and_shared_tools(self):
        self.policy.validate_definition(DEFINITION)
        for change in (
            {"store": True}, {"store": "false"}, {"model_type": "self_deployed"},
            {"model": "expensive-unapproved-model"},
            {"tools": [{"type": "mcp", "server_url": MCP,
                        "project_connection_id": "another-project-connection",
                        "allowed_tools": list(EXPECTED_TOOLS)}]},
            {"target_agent": {"name": "other-user"}},
            {"subagent_config": {"subagents": [{"name": "other-user"}]}},
            {"avatar": {"character": "expensive-avatar"}},
            {"tools": [{"type": "openapi", "server_url": MCP}]},
            {"tools": [{"type": "mcp", "server_url": "http://other.example",
                        "project_connection_id": CONNECTION,
                        "allowed_tools": list(EXPECTED_TOOLS)}]},
            {"tools": [{"type": "mcp", "server_url": "https://other.example",
                        "project_connection_id": "other-project-connection",
                        "allowed_tools": list(EXPECTED_TOOLS)}]},
            {"tools": [{"type": "mcp", "server_url": "https://user:secret@other.example/mcp",
                        "allowed_tools": ["lookup"]}]},
            {"tools": [{"type": "mcp", "server_url": "https://other.example/mcp",
                        "allowed_tools": []}]},
            {"tools": [{"type": "mcp", "server_url": MCP,
                        "project_connection_id": CONNECTION,
                        "allowed_tools": ["unapproved_admin_tool"]}]},
            {"tools": [{"type": "mcp", "server_url": MCP,
                        "project_connection_id": CONNECTION,
                        "allowed_tools": list(EXPECTED_TOOLS), "headers": {"Authorization": "secret"}}]},
            {"handoff": {"nodes": [{"id": "expensive", "model": "other-model"}]}},
        ):
            with self.subTest(change=change), self.assertRaises(web.HTTPBadRequest):
                self.policy.validate_definition({**DEFINITION, **change})

    def test_users_may_bind_their_own_public_mcp_server_unless_disabled(self):
        custom = {"tools": [{"type": "mcp", "server_label": "custom_mcp",
                             "server_url": "https://tools.example/mcp",
                             "require_approval": "never",
                             "allowed_tools": ["lookup_order"]}]}
        self.policy.validate_definition({**DEFINITION, **custom})
        locked = configured_policy(allow_custom_mcp=False)
        with self.assertRaises(web.HTTPBadRequest):
            locked.validate_definition({**DEFINITION, **custom})
        self.assertTrue(locked.allows_mcp(MCP, CONNECTION, sorted(EXPECTED_TOOLS)))

    def test_invitation_mode_requires_signing_hash_and_expiry(self):
        values = {
            "auth_mode": "invite",
            "cookie_key": "synthetic-cookie-signing-key-with-32-bytes",
            "invitation_hash": INVITATION_HASH,
            "invitation_expires_at": INVITATION_EXPIRES,
        }
        configured_policy(**values)
        for change in (
            {"cookie_key": "short"},
            {"invitation_hash": ""},
            {"invitation_hash": INVITATION},
            {"invitation_expires_at": 0},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                configured_policy(**{**values, **change})

    def test_workspace_namespace_shortens_long_names_deterministically(self):
        request = {server.REQUEST_ID_KEY: "test", USER_KEY: "a" * 16}
        long_name = "local-only-finance-with-otp-and-officer-search-12345678"
        first = self.policy.agent_name(request, long_name)
        second = self.policy.agent_name(request, long_name)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 63)
        self.assertTrue(first.startswith("pg-" + "a" * 16 + "-local-only-"))

    def test_voice_frames_cannot_change_model_tools_or_storage(self):
        for frame in (
            {"type": "session.update", "session": {"store": True}},
            {"type": "response.create", "response": {"tools": [{"type": "mcp"}]}},
            {"type": "conversation.item.create", "item": {"type": "message", "role": "system"}},
            {"type": "conversation.item.create", "item": {"type": "function_call_output"}},
            {"type": "session.avatar.connect"}, [], "not-an-object",
        ):
            with self.subTest(frame=frame), self.assertRaises(ValueError):
                self.policy.validate_frame(json.dumps(frame))
        with self.assertRaises(ValueError):
            self.policy.validate_frame(b"binary")
        for frame in (
            {"type": "response.create"},
            {"type": "input_audio_buffer.append", "audio": "AAAA"},
            {"type": "rtc.call.sdp.create", "sdp_offer": "test-sdp"},
            {"type": "conversation.item.create", "item": {
                "type": "message", "role": "user", "content": [{"type": "input_text", "text": "Hello"}],
            }},
        ):
            self.policy.validate_frame(json.dumps(frame))

    def test_hosted_profile_reuses_default_catalog_with_public_mcp(self):
        catalog = template_portal.TemplateCatalog(
            template_portal.DEFAULT_TEMPLATE_CONFIG,
            profile_path=PROFILE,
        )
        self.assertEqual(catalog.errors, [])
        configured = json.loads(
            template_portal.DEFAULT_TEMPLATE_CONFIG.read_text(encoding="utf-8")
        )["templates"]
        self.assertEqual(
            [card["id"] for card in catalog.cards()],
            [entry["id"] for entry in configured if entry.get("enabled", True)],
        )
        detail = catalog.detail(TEMPLATE_ID)
        self.assertFalse(detail["mcp"]["configuration_required"])
        document = catalog.document(TEMPLATE_ID)
        next(template_portal.iter_mcp_tools(document["definition"]))[
            "project_connection_id"
        ] = "old-connection"
        result = template_portal.materialize_template(
            document, model="", voice="", mcp_server_url=MCP,
            mcp_connection_id=CONNECTION,
            mcp_public=True,
        )
        tool = next(template_portal.iter_mcp_tools(result))
        self.assertEqual(tool["server_url"], MCP)
        for key in ("project_connection_id", "authorization", "headers"):
            self.assertNotIn(key, tool)

    def test_catalog_policy_includes_models_and_tools_from_backup_versions(self):
        backup = json.loads(json.dumps(DOCUMENT))
        backup["definition"]["model"] = "gpt-realtime-mini"
        next(template_portal.iter_mcp_tools(backup["definition"]))[
            "allowed_tools"
        ].append("backup_only_tool")
        catalog = SimpleNamespace(
            cards=lambda: [{
                "id": TEMPLATE_ID,
                "name": "Versioned template",
                "versions": [{"id": "."}, {"id": "backups/original"}],
            }],
            source=lambda template_id, version: SOURCE,
            document=lambda template_id, version: DOCUMENT if version == "." else backup,
        )
        policy = PlaygroundPolicy(origin=ORIGIN, tenant_id=TENANT, mcp_url="")
        policy.configure_catalog(catalog)
        self.assertIn("gpt-realtime-mini", policy.models)
        self.assertTrue(policy.allows_mcp(MCP, "", ["backup_only_tool"]))
        self.assertEqual(1, len(policy.mcp_presets))

    def test_container_upgrades_pip_before_installing_dependencies(self):
        dockerfile = (_CONTEXT / "portal/hosting/Dockerfile").read_text(encoding="utf-8")
        upgrade = 'python -m pip install --no-cache-dir --upgrade "pip==26.2"'
        install = "python -m pip install --no-cache-dir -r /app/portal/requirements.txt"
        self.assertLess(dockerfile.index(upgrade), dockerfile.index(install))
        self.assertIn("rm -r /usr/local/lib/python3.12/ensurepip", dockerfile)
        self.assertIn("assert importlib.metadata.version('pip') == '26.2'", dockerfile)
        self.assertIn("assert importlib.util.find_spec('ensurepip') is None", dockerfile)
        self.assertIn("python -m pip check", dockerfile)
        self.assertIn("USER 10001", dockerfile)
        self.assertIn("assert {card['id'] for card in catalog.cards()} == expected", dockerfile)

    def test_container_context_excludes_credentials_state_and_dependencies(self):
        portal_server = PORTAL_SOURCE / "portal/demo_server.py"
        public_source = portal_server.read_bytes()
        self.assertNotIn(b"from .playground", public_source)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "context"
            files = stage(root, portal_source=PORTAL_SOURCE)
            self.assertIn("portal/playground_server.py", files)
            self.assertIn("portal/playground_usage.py", files)
            self.assertIn("portal/templates.config.json", files)
            local_config = PORTAL_SOURCE / "portal/templates.local.config.json"
            if local_config.is_file():
                self.assertIn("portal/templates.local.config.json", files)
                self.assertEqual(
                    (root / "portal/templates.local.config.json").read_bytes(),
                    local_config.read_bytes(),
                )
            self.assertIn(
                "samples/example1_finance_with_handoff_realtime/agent.json",
                files,
            )
            self.assertIn("samples/voice_agent_definition.py", files)
            self.assertIn(
                "samples/example4_frontdesk_with_fluency_and_handoff/agent.json",
                files,
            )
            staged_catalog = template_portal.TemplateCatalog(
                root / "portal/templates.config.json",
                root / "samples",
                root / "shared_mcp",
                profile_path=root / "portal/hosting/profile.json",
            )
            self.assertEqual(staged_catalog.errors, [])
            self.assertEqual(
                [card["id"] for card in staged_catalog.cards()],
                [card["id"] for card in CATALOG.cards()],
            )
            staged_policy = PlaygroundPolicy(
                origin=ORIGIN, tenant_id=TENANT, mcp_url="",
            )
            staged_policy.configure_catalog(staged_catalog)
            for card in staged_catalog.cards():
                self.assertEqual(
                    card["versions"],
                    CATALOG.detail(card["id"])["versions"],
                )
                for version in card["versions"]:
                    source = staged_catalog.source(card["id"], version["id"])
                    document = staged_catalog.document(card["id"], version["id"])
                    relative = source.path.relative_to(root)
                    self.assertIn(relative.as_posix(), files)
                    self.assertEqual(
                        source.path.read_bytes(),
                        (PORTAL_SOURCE / relative).read_bytes(),
                    )
                    definition = template_portal.materialize_template(
                        document, model="", voice="",
                        mcp_server_url=source.mcp_server_url,
                        mcp_connection_id="", mcp_public=True,
                    )
                    staged_policy.validate_definition(definition)
                    self.assertFalse(definition["store"])
                    if card["id"] == "frontdesk-receptionist-example" and version["id"] == ".":
                        self.assertTrue(source.mcp_server_url.endswith("/mcp/frontdesk"))
                        self.assertEqual(len(definition["handoff"]["nodes"]), 8)
                        self.assertEqual(len(definition["handoff"]["edges"]), 16)
            self.assertFalse(any(
                part in {".env", ".venv", ".git", ".run", "state", "node_modules"}
                for name in files for part in Path(name).parts
            ))
            self.assertEqual(
                sorted(files), sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()),
            )
            self.assertIn(
                "from .playground",
                (root / "portal/demo_server.py").read_text(encoding="utf-8"),
            )
            self.assertEqual(portal_server.read_bytes(), public_source)
            self.assertFalse((PORTAL_SOURCE / "portal/playground.py").exists())
            with self.assertRaises(ValueError):
                stage(root, portal_source=PORTAL_SOURCE)

    def test_staging_requires_a_complete_portal_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(FileNotFoundError, "Required build input"):
                stage(root / "context", portal_source=root / "missing")
            self.assertFalse((root / "context").exists())

    def test_staging_keeps_patched_inputs_readable_under_a_private_umask(self):
        previous = os.umask(0o077)
        try:
            with tempfile.TemporaryDirectory() as directory:
                destination = Path(directory) / "context"
                names = stage(destination, portal_source=PORTAL_SOURCE)
                self.assertEqual(0o700, destination.stat().st_mode & 0o777)
                for name in names:
                    with self.subTest(name=name):
                        self.assertEqual(
                            0o644, (destination / name).stat().st_mode & 0o777,
                        )
        finally:
            os.umask(previous)

    def test_staging_rejects_an_incompatible_portal_adapter(self):
        with tempfile.TemporaryDirectory() as directory:
            failure = subprocess.CalledProcessError(
                1, ["git", "apply"], stderr="patch does not apply",
            )
            with patch("build_context.subprocess.run", side_effect=failure):
                with self.assertRaisesRegex(ValueError, "incompatible with the hosted adapter"):
                    stage(Path(directory) / "context", portal_source=PORTAL_SOURCE)

    def test_staging_requires_native_public_mcp_support(self):
        old_api = ast.parse("def materialize_template(document):\n    return document\n")
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "context"
            with patch("build_context.ast.parse", return_value=old_api):
                with self.assertRaisesRegex(ValueError, "native public-MCP support"):
                    stage(destination, portal_source=PORTAL_SOURCE)
            self.assertFalse(destination.exists())

    def test_staged_hosted_entrypoint_boots_locked_without_the_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "context"
            stage(root, portal_source=PORTAL_SOURCE)
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            environment = {
                **os.environ,
                "PYTHON_DOTENV_DISABLED": "1", "PYTHONPATH": "",
                "VOICE_DEMO_VOICE_WS_BASE": "", "DEMO_PORT": str(port),
                "AZURE_VOICE_AGENTS_ENDPOINT": ENDPOINT,
                "VOICE_PLAYGROUND_ORIGIN": ORIGIN, "VOICE_PLAYGROUND_TENANT_ID": TENANT,
                "VOICE_PLAYGROUND_ENABLED": "false",
                "VOICE_PORTAL_DATA_DIR": str(Path(directory) / "runtime"),
            }
            with subprocess.Popen(
                [sys.executable, "-m", "portal.playground_server"],
                cwd=root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            ) as process:
                try:
                    base = f"http://127.0.0.1:{port}"
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline and process.poll() is None:
                        try:
                            response = requests.get(base + "/healthz", timeout=0.2)
                            break
                        except requests.ConnectionError:
                            time.sleep(0.05)
                    else:
                        self.fail("Staged playground failed to become ready.")
                    self.assertEqual(response.json(), {"status": "ok"})
                    response = requests.get(base + "/config", headers=headers(), timeout=2)
                    self.assertEqual(response.status_code, 503)
                    self.assertIsNone(process.poll())
                finally:
                    process.terminate()
                    process.wait(timeout=5)


class PlaygroundHTTPTests(unittest.IsolatedAsyncioTestCase):
    def use_invitation_mode(self):
        self.policy.auth_mode = "invite"
        self.policy.cookie_key = "synthetic-cookie-signing-key-with-32-bytes"
        self.policy.invitation_hash = INVITATION_HASH
        self.policy.invitation_expires_at = INVITATION_EXPIRES

    async def asyncSetUp(self):
        self.calls = []
        self.ws_calls = []
        self.response_version = "1"
        self.response_status = None
        self.policy = configured_policy(enabled=True)

        async def http_fixture(request):
            raw = await request.read()
            self.calls.append({
                "path": request.path, "query": dict(request.query),
                "body": json.loads(raw) if raw else None,
                "headers": dict(request.headers),
            })
            if request.path.endswith("/agents"):
                return web.json_response({
                    "data": [
                        {"name": prefix() + "mine", "definition": DEFINITION},
                        {"name": prefix(BOB) + "private-bob", "definition": DEFINITION},
                        {"name": "owner-private-agent", "definition": DEFINITION},
                    ],
                    "has_more": "after" not in request.query,
                    "first_id": "owner-private-agent",
                    "last_id": "another-private-name",
                })
            return web.json_response({
                "name": request.path.split("/agents/")[1].split("/")[0],
                "version": self.response_version, "definition": DEFINITION,
            }, status=self.response_status or (201 if request.method == "POST" else 200))

        async def voice_fixture(request):
            self.ws_calls.append({"path": request.path, "query": dict(request.query)})
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            await ws.send_json({"type": "session.created", "session": {"id": "synthetic"}})
            async for message in ws:
                if message.type == WSMsgType.TEXT:
                    await ws.send_str(message.data)
            return ws

        upstream = web.Application()
        upstream.router.add_get(
            "/api/projects/playground/agents/{agent}/endpoint/protocols/voice", voice_fixture,
        )
        upstream.router.add_route("*", "/{tail:.*}", http_fixture)
        self.upstream = TestServer(upstream, host="127.0.0.1")
        await self.upstream.start_server()
        self.addAsyncCleanup(self.upstream.close)
        args = server.parse_args([
            "--project-endpoint", ENDPOINT, "--no-record-sessions",
            "--template-profile", str(PROFILE),
        ])
        with patch.object(server, "ManagedIdentityCredential", return_value=Mock()):
            self.app = server.build_app(args, playground=self.policy)
        install_usage_telemetry(
            self.app, request_id_key=server.REQUEST_ID_KEY,
            template_ids=[card["id"] for card in CATALOG.cards()],
        )
        cfg = self.app[server.DEFAULT_CONFIG_KEY]
        cfg.host = str(self.upstream.make_url("/api/projects/playground"))
        cfg._credential.get_token.return_value = SimpleNamespace(
            token="synthetic-service-token", expires_on=time.time() + 3600,
        )
        self.client = TestClient(TestServer(self.app, host="127.0.0.1"))
        await self.client.start_server()
        self.addAsyncCleanup(self.client.close)

    async def login(self, *, email=ALICE_EMAIL, token=ALICE_TOKEN, next_path="/"):
        return await self.client.post(
            "/login",
            headers={
                "Host": "playground.example",
                "Origin": ORIGIN,
                "Sec-Fetch-Site": "same-origin",
            },
            data={"email": email, "token": token, "next": next_path},
            allow_redirects=False,
        )

    @staticmethod
    def usage_records(captured):
        return [
            json.loads(record.getMessage().split(LOG_MARKER, 1)[1])
            for record in captured.records if LOG_MARKER in record.getMessage()
        ]

    async def test_login_usage_and_returning_activity_are_private_and_stable(self):
        self.use_invitation_mode()
        with self.assertLogs("voice_agent_portal", level="INFO") as captured:
            failed = await self.login(token="invalid-secret-invitation")
            first = await self.login(email=" Alice@Example.COM ")
            second = await self.login()
            cookie = f"{ACCESS_COOKIE}={first.cookies[ACCESS_COOKIE].value}"
            response = await self.client.get("/config", headers={
                "Host": "playground.example", "Cookie": cookie,
            })
        self.assertEqual(failed.status, 401)
        self.assertEqual(first.status, 303)
        self.assertEqual(second.status, 303)
        self.assertEqual(response.status, 200)
        records = self.usage_records(captured)
        logins = [row for row in records if row["event_name"] == "login"]
        self.assertEqual([row["outcome"] for row in logins], ["failure", "success", "success"])
        self.assertIsNone(logins[0]["user_id"])
        self.assertEqual(logins[1]["user_id"], logins[2]["user_id"])
        activity = [row for row in records if row["event_name"] == "activity"]
        self.assertEqual(activity[0]["user_id"], logins[1]["user_id"])
        serialized = json.dumps(records)
        for secret in (
            ALICE_EMAIL, "Alice@Example.COM", INVITATION,
            "invalid-secret-invitation", first.cookies[ACCESS_COOKIE].value,
        ):
            self.assertNotIn(secret, serialized)
        self.assertEqual(len({row["event_id"] for row in records}), len(records))

    async def test_usage_excludes_probes_static_assets_and_unauthenticated_requests(self):
        self.use_invitation_mode()
        login = await self.login()
        cookie = f"{ACCESS_COOKIE}={login.cookies[ACCESS_COOKIE].value}"
        with self.assertLogs("voice_agent_portal", level="INFO") as captured:
            await self.client.get("/healthz")
            await self.client.get("/config", headers={"Host": "playground.example"})
            await self.client.get("/static/demo/nonexistent.js", headers={
                "Host": "playground.example", "Cookie": cookie,
            })
            await self.client.get("/config", headers={
                "Host": "playground.example", "Cookie": cookie,
                "X-MS-Synthetic-Source": "synthetic-test-source",
            })
        records = [row for row in self.usage_records(captured) if row["event_name"] != "heartbeat"]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["event_name"], "activity")
        self.assertEqual(records[0]["traffic_type"], "synthetic")
        self.assertNotIn("synthetic-test-source", json.dumps(records))

    async def test_publication_usage_distinguishes_creates_versions_and_validation_failures(self):
        with self.assertLogs("voice_agent_portal", level="INFO") as captured:
            created = await self.client.post(
                "/agents/my-agent/versions", headers=headers(), json={"definition": DEFINITION},
            )
            self.response_version = "2"
            self.response_status = 200
            updated = await self.client.post(
                "/agents/my-agent/versions", headers=headers(), json={"definition": DEFINITION},
            )
            rejected = await self.client.post(
                "/agents/my-agent/versions", headers=headers(),
                json={"definition": {**DEFINITION, "store": True}},
            )
        self.assertEqual((created.status, updated.status, rejected.status), (201, 200, 400))
        rows = [row for row in self.usage_records(captured) if row["event_name"] == "agent_publish"]
        self.assertEqual([row["change"] for row in rows], ["created", "version_published", "unknown"])
        self.assertEqual([row["outcome"] for row in rows], ["success", "success", "failure"])
        self.assertEqual(rows[0]["agent_id"], rows[1]["agent_id"])
        self.assertEqual(len(rows[0]["agent_id"]), 64)
        self.assertNotIn("my-agent", json.dumps(rows))
        self.assertNotIn("definition", json.dumps(rows))

    async def test_template_publication_usage_reports_missing_metadata_and_failures(self):
        with patch.object(template_portal, "validate_mcp_probe_url"), \
                patch.object(template_portal, "publish_agent") as publish, \
                self.assertLogs("voice_agent_portal", level="INFO") as captured:
            publish.return_value = {"name": prefix() + "test", "version": "1"}
            first = await self.client.post(
                f"/api/templates/{TEMPLATE_ID}/publish", json={"name": "test"}, headers=headers(),
            )
            publish.return_value = {"name": prefix() + "test"}
            missing = await self.client.post(
                f"/api/templates/{TEMPLATE_ID}/publish", json={"name": "test"}, headers=headers(),
            )
            publish.side_effect = RuntimeError("private exception content")
            failed = await self.client.post(
                f"/api/templates/{TEMPLATE_ID}/publish", json={"name": "test"}, headers=headers(),
            )
        self.assertEqual((first.status, missing.status, failed.status), (201, 201, 502))
        rows = [row for row in self.usage_records(captured) if row["event_name"] == "agent_publish"]
        self.assertEqual(rows[0]["template_id"], TEMPLATE_ID)
        self.assertEqual(rows[0]["change"], "created")
        self.assertEqual(rows[1]["change"], "unknown")
        self.assertEqual(rows[1]["metadata_status"], "missing")
        self.assertEqual(rows[2]["outcome"], "failure")
        self.assertNotIn("private exception content", json.dumps(rows))

    async def test_missing_wrong_tenant_and_malformed_principals_are_denied(self):
        for path in ("/", "/config", "/api/templates", "/static/demo/bundle.js", "/agents"):
            response = await self.client.get(path, headers={"Host": "playground.example"})
            self.assertEqual(response.status, 401, path)
        invalid = headers(tenant=BOB)
        response = await self.client.get("/config", headers=invalid)
        self.assertEqual(response.status, 401)
        for principal in ("not-base64", base64.b64encode(b"null").decode(),
                          base64.b64encode(b'{"auth_typ":"aad","claims":[null]}').decode()):
            response = await self.client.get("/config", headers={
                "Host": "playground.example", "X-MS-CLIENT-PRINCIPAL": principal,
            })
            self.assertEqual(response.status, 401)
        response = await self.client.get("/healthz")
        self.assertEqual(await response.json(), {"status": "ok"})
        self.assertEqual(self.calls, [])

    async def test_invitation_blocks_all_privileged_surfaces_without_code(self):
        self.use_invitation_mode()
        for path in ("/", "/config", "/agents", "/api/templates", "/static/demo/bundle.js"):
            response = await self.client.get(path, headers=headers())
            self.assertEqual(response.status, 401, path)
            self.assertNotIn(WORKSPACE_COOKIE, response.cookies)
            self.assertNotIn(ACCESS_COOKIE, response.cookies)
            self.assertNotIn("WWW-Authenticate", response.headers)
        response = await self.client.get(
            "/",
            headers={**headers(), "Accept": "text/html"},
            allow_redirects=False,
        )
        self.assertEqual(response.status, 303)
        self.assertTrue(response.headers["Location"].startswith("/login?next="))
        response = await self.client.get("/login", headers={
            **headers(), "Accept": "text/html,application/xhtml+xml",
        })
        self.assertEqual(response.status, 200)
        login_html = await response.text()
        self.assertIn('name="token"', login_html)
        self.assertIn('name="email"', login_html)
        self.assertNotIn(INVITATION, login_html)
        for email, token in (
            (ALICE_EMAIL, "wrong-invitation-code"),
            ("not-an-email", ALICE_TOKEN),
        ):
            response = await self.login(email=email, token=token)
            self.assertEqual(response.status, 401)
            self.assertNotIn(ACCESS_COOKIE, response.cookies)
            error_html = await response.text()
            self.assertIn('role="alert"', error_html)
            self.assertIn(f'value="{email}"', error_html)
            self.assertNotIn(token, error_html)
        response = await self.client.post(
            "/login",
            headers={"Host": "playground.example", "Origin": "https://evil.example"},
            data={"email": ALICE_EMAIL, "token": ALICE_TOKEN},
        )
        self.assertEqual(response.status, 403)
        response = await self.client.post(
            "/login",
            headers={"Host": "playground.example", "Origin": "null"},
            data={"email": ALICE_EMAIL, "token": ALICE_TOKEN},
        )
        self.assertEqual(response.status, 403)
        self.assertEqual(self.calls, [])
        response = await self.client.get("/healthz")
        self.assertEqual(await response.json(), {"status": "ok"})

    async def test_invitation_login_form_shows_both_fields_and_contact(self):
        self.use_invitation_mode()
        response = await self.client.get(
            "/login",
            headers={**headers(), "Accept": "text/html"},
        )
        self.assertEqual(response.status, 200)
        login_html = await response.text()
        self.assertEqual(login_html.count('<form method="post" action="/login">'), 1)
        self.assertEqual(login_html.count('name="token"'), 1)
        self.assertEqual(login_html.count('name="email"'), 1)
        self.assertEqual(login_html.count('type="submit"'), 1)
        self.assertNotIn(" hidden", login_html)
        self.assertNotIn('type="button"', login_html)
        self.assertNotIn("<script", login_html)
        self.assertIn(
            '<a href="mailto:yiwenrong@microsoft.com">yiwenrong@microsoft.com</a>',
            login_html,
        )
        self.assertNotIn(INVITATION, login_html)
        self.assertEqual(self.calls, [])

    async def test_invitation_login_rejects_untrusted_origins(self):
        self.use_invitation_mode()
        for origin, fetch_site in (
            ("https://evil.example", "same-origin"),
            ("null", ""),
            ("null", "same-site"),
            ("null", "cross-site"),
            (ORIGIN, "cross-site"),
        ):
            with self.subTest(origin=origin, fetch_site=fetch_site):
                response = await self.client.post(
                    "/login",
                    headers={
                        "Host": "playground.example",
                        "Origin": origin,
                        "Sec-Fetch-Site": fetch_site,
                    },
                    data={"email": ALICE_EMAIL, "token": ALICE_TOKEN},
                    allow_redirects=False,
                )
                self.assertEqual(response.status, 403)
                self.assertNotIn(ACCESS_COOKIE, response.cookies)
        self.assertEqual(self.calls, [])

    async def test_invitation_sets_persistent_email_scoped_access_cookie(self):
        self.use_invitation_mode()
        response = await self.client.post(
            "/login",
            headers={
                "Host": "playground.example",
                "Origin": "null",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "navigate",
            },
            data={
                "email": ALICE_EMAIL,
                "token": ALICE_TOKEN,
                "next": "/templates/",
            },
            allow_redirects=False,
        )
        self.assertEqual(response.status, 303)
        self.assertEqual(response.headers["Location"], "/templates/")
        access = response.cookies[ACCESS_COOKIE]
        self.assertTrue(access["secure"])
        self.assertTrue(access["httponly"])
        self.assertEqual(access["samesite"], "Lax")
        self.assertEqual(access["path"], "/")
        self.assertEqual(access["domain"], "")
        self.assertGreater(int(access["max-age"]), 300 * 24 * 60 * 60)
        cookie = f"{ACCESS_COOKIE}={access.value}"
        response = await self.client.get("/config", headers={
            **headers(), "Cookie": cookie,
        })
        self.assertEqual(response.status, 200)
        self.assertEqual((await response.json())["playgroundAuthMode"], "invite")
        response = await self.client.get("/agents/mine", headers={
            **headers(), "Cookie": cookie,
        })
        self.assertEqual(response.status, 200)
        self.assertTrue((await response.json())["name"].startswith(email_prefix()))
        self.assertEqual(
            self.calls[-1]["headers"]["Authorization"],
            "Bearer synthetic-service-token",
        )

        response = await self.login(next_path="//evil.example")
        self.assertEqual(response.headers["Location"], "/")

    async def test_invitation_access_survives_token_rotation_but_rejects_tampering(self):
        self.use_invitation_mode()
        response = await self.login()
        cookie = f"{ACCESS_COOKIE}={response.cookies[ACCESS_COOKIE].value}"
        for token in ("invalid", response.cookies[ACCESS_COOKIE].value + "tampered", "v2.invalid"):
            response = await self.client.get("/config", headers={
                **headers(), "Cookie": f"{ACCESS_COOKIE}={token}",
            })
            self.assertEqual(response.status, 401)
        self.policy.invitation_hash = hashlib.sha256(b"rotated-invitation").hexdigest()
        response = await self.client.get("/config", headers={**headers(), "Cookie": cookie})
        self.assertEqual(response.status, 200)
        self.policy.invitation_expires_at = int(time.time()) - 1
        response = await self.client.get("/config", headers={**headers(), "Cookie": cookie})
        self.assertEqual(response.status, 200)

    async def test_invitation_websocket_requires_email_access_cookie(self):
        self.use_invitation_mode()
        path = "/agents/test/endpoint/protocols/voice"
        with self.assertRaises(WSServerHandshakeError) as rejected:
            await self.client.ws_connect(path, headers=headers())
        self.assertEqual(rejected.exception.status, 401)
        self.assertEqual(self.ws_calls, [])
        response = await self.login()
        cookie = f"{ACCESS_COOKIE}={response.cookies[ACCESS_COOKIE].value}"
        ws = await self.client.ws_connect(path, headers={**headers(), "Cookie": cookie})
        self.assertEqual((await ws.receive_json())["type"], "session.created")
        await ws.close()

    async def test_shared_token_uses_stable_distinct_email_namespaces(self):
        self.use_invitation_mode()
        paths = []
        for _ in range(2):
            login = await self.login()
            cookie = f"{ACCESS_COOKIE}={login.cookies[ACCESS_COOKIE].value}"
            response = await self.client.get("/agents/mine", headers={
                **headers(), "Cookie": cookie,
            })
            self.assertEqual(response.status, 200)
            paths.append(self.calls[-1]["path"])
        self.assertEqual(paths[0], paths[1])
        self.assertIn(email_prefix(), paths[0])
        bob_login = await self.login(email=BOB_EMAIL, token=BOB_TOKEN)
        bob_cookie = f"{ACCESS_COOKIE}={bob_login.cookies[ACCESS_COOKIE].value}"
        response = await self.client.get("/agents/mine", headers={
            **headers(), "Cookie": bob_cookie,
        })
        self.assertEqual(response.status, 200)
        self.assertNotEqual(paths[0], self.calls[-1]["path"])

    async def test_first_stage_is_locked_even_with_a_principal_header(self):
        self.policy.enabled = False
        response = await self.client.get("/config", headers=headers())
        self.assertEqual(response.status, 503)
        response = await self.client.get("/healthz")
        self.assertEqual(response.status, 200)
        self.assertEqual(self.calls, [])

    async def test_anonymous_cookie_creates_isolated_temporary_workspaces(self):
        self.policy.auth_mode = "anonymous"
        self.policy.cookie_key = "synthetic-cookie-signing-key-with-32-bytes"
        anonymous_headers = {"Host": "playground.example", "Origin": ORIGIN}

        first = await self.client.get("/config", headers=anonymous_headers)
        self.assertEqual(first.status, 200)
        self.assertIn("Anonymous shared playground", (await first.json())["notice"])
        first_cookie = first.cookies[WORKSPACE_COOKIE].value
        self.assertTrue(first.cookies[WORKSPACE_COOKIE]["secure"])
        self.assertTrue(first.cookies[WORKSPACE_COOKIE]["httponly"])

        second = await self.client.get("/config", headers=anonymous_headers)
        second_cookie = second.cookies[WORKSPACE_COOKIE].value
        self.assertNotEqual(first_cookie, second_cookie)

        first_headers = {
            **anonymous_headers, "Cookie": f"{WORKSPACE_COOKIE}={first_cookie}",
        }
        second_headers = {
            **anonymous_headers, "Cookie": f"{WORKSPACE_COOKIE}={second_cookie}",
        }
        response = await self.client.post(
            "/agents/test/versions", headers=first_headers, json={"definition": DEFINITION},
        )
        self.assertEqual(response.status, 201)
        first_path = self.calls[-1]["path"]
        response = await self.client.post(
            "/agents/test/versions", headers=second_headers, json={"definition": DEFINITION},
        )
        self.assertEqual(response.status, 201)
        self.assertNotEqual(first_path, self.calls[-1]["path"])

        response = await self.client.get(
            "/agents/test/versions/1",
            headers={**second_headers, "Cookie": f"{WORKSPACE_COOKIE}={first_cookie}tampered"},
        )
        self.assertEqual(response.status, 200)
        self.assertIn(WORKSPACE_COOKIE, response.cookies)
        self.assertNotEqual(response.cookies[WORKSPACE_COOKIE].value, first_cookie)

        with self.assertRaises(WSServerHandshakeError) as failed:
            await self.client.ws_connect(
                "/agents/test/endpoint/protocols/voice", headers=anonymous_headers,
            )
        self.assertEqual(failed.exception.status, 401)
        ws = await self.client.ws_connect(
            "/agents/test/endpoint/protocols/voice", headers=first_headers,
        )
        self.addAsyncCleanup(ws.close)
        self.assertEqual((await ws.receive_json())["type"], "session.created")

    async def test_fixed_project_config_origin_and_disabled_surfaces(self):
        response = await self.client.get("/config", headers=headers(long_claims=True))
        data = await response.json()
        self.assertTrue(data["playground"])
        self.assertEqual(
            response.headers["Strict-Transport-Security"],
            "max-age=31536000; includeSubDomains",
        )
        self.assertEqual(
            set(data["models"]),
            {"gpt-realtime"} | {
                CATALOG.document(card["id"], version["id"])["definition"]["model"]
                for card in CATALOG.cards()
                for version in card["versions"]
            },
        )
        self.assertFalse(data["defaultStore"])
        self.assertEqual(data["mcpAuthPresets"][0]["server_url"], MCP)
        self.assertEqual(data["mcpAuthPresets"][0]["mode"], "url")
        self.assertNotIn("synthetic-service-token", json.dumps(data))
        for changed in (
            {**headers(), "Origin": "https://evil.example"},
            {**headers(), "Host": "evil.example"},
            {**headers(), "Sec-Fetch-Site": "cross-site"},
        ):
            response = await self.client.get("/config", headers=changed)
            self.assertEqual(response.status, 403)
        response = await self.client.post("/api/project", headers=headers(), json={"endpoint": ENDPOINT})
        self.assertEqual(response.status, 403)
        with patch.object(template_portal, "discover_projects") as discover:
            response = await self.client.get("/api/projects", headers=headers())
            self.assertEqual(response.status, 200)
            discover.assert_not_called()
        for path, method in (("/foundry-trace", "GET"), ("/agents:generate", "POST")):
            response = await self.client.request(method, path, headers=headers(), json={})
            self.assertEqual(response.status, 403)
        response = await self.client.get("/api/demo/sessions", headers=headers())
        self.assertFalse((await response.json())["available"])
        response = await self.client.get("/api/demo/sessions/other/events", headers=headers())
        self.assertEqual(response.status, 404)

    async def test_agent_namespace_removes_cross_workspace_pagination(self):
        response = await self.client.get("/agents?kind=voice&limit=25", headers=headers())
        data = await response.json()
        self.assertEqual([item["name"] for item in data["data"]], [prefix() + "mine"])
        self.assertNotIn("private-bob", json.dumps(data))
        self.assertNotIn("owner-private-agent", json.dumps(data))
        self.assertNotIn("another-private-name", json.dumps(data))
        self.assertFalse(data["has_more"])
        self.assertEqual(data["last_id"], prefix() + "mine")
        response = await self.client.get(
            "/agents",
            params={"after": "another-private-name"},
            headers=headers(),
        )
        self.assertEqual(response.status, 400)
        response = await self.client.get("/agents/hello/versions/1", headers=headers())
        self.assertEqual(response.status, 200)
        self.assertIn("/agents/" + prefix() + "hello/versions/1", self.calls[-1]["path"])
        count = len(self.calls)
        for suffix in ("", "/versions/1", "/endpoint/protocols/voice/conversations",
                       "/endpoint/protocols/voice/conversations/conv/audio/content"):
            response = await self.client.get("/agents/" + prefix(BOB) + "private-bob" + suffix,
                                             headers=headers())
            self.assertEqual(response.status, 404)
        self.assertEqual(len(self.calls), count)

    async def test_publication_is_scoped_and_validated_before_azure(self):
        response = await self.client.post("/agents/my-agent/versions", headers={
            **headers(), "X-MS-Voice-Session-Override": '{"store":true}',
        }, json={"definition": DEFINITION})
        self.assertEqual(response.status, 201)
        self.assertEqual((await response.json())["name"], prefix() + "my-agent")
        self.assertNotIn("X-MS-Voice-Session-Override", self.calls[-1]["headers"])
        count = len(self.calls)
        for change in ({"store": True}, {"model_type": "hosted_agent"},
                       {"tools": [{"type": "mcp", "server_url": "https://evil.example"}]}):
            response = await self.client.post("/agents/my-agent/versions", headers=headers(),
                                             json={"definition": {**DEFINITION, **change}})
            self.assertEqual(response.status, 400, change)
        self.assertEqual(len(self.calls), count)
        response = await self.client.post("/agents/my-agent/versions", headers=headers(), json=[])
        self.assertEqual(response.status, 400)

    async def test_template_publish_configure_and_probe_use_no_arm_or_secret(self):
        with patch.object(template_portal, "validate_mcp_probe_url"), \
             patch.object(template_portal, "create_mcp_connection") as create_connection, \
             patch.object(template_portal, "publish_agent", return_value={"name": prefix() + "test", "version": "1"}) as publish:
            response = await self.client.post(
                f"/api/templates/{TEMPLATE_ID}/mcp/configure", json={}, headers=headers(),
            )
            self.assertTrue((await response.json())["configured"])
            response = await self.client.post(
                f"/api/templates/{TEMPLATE_ID}/publish", json={"name": "test"}, headers=headers(),
            )
            self.assertEqual(response.status, 201)
            kwargs = publish.call_args.kwargs
            self.assertEqual(kwargs["name"], prefix() + "local-only-test")
            self.assertFalse(kwargs["definition"]["store"])
            self.assertNotIn(
                "project_connection_id",
                next(template_portal.iter_mcp_tools(kwargs["definition"])),
            )
            create_connection.assert_not_called()
        handshake_signature = inspect.signature(template_portal.mcp_handshake)
        with patch.object(template_portal, "mcp_handshake", return_value={
            "tools": list(EXPECTED_TOOLS), "latency_ms": 1,
        }) as handshake:
            response = await self.client.get(
                f"/api/templates/{TEMPLATE_ID}/mcp/probe", headers=headers(),
            )
            self.assertTrue((await response.json())["ok"])
            self.assertEqual(handshake.call_args.args, (MCP, ""))
            handshake_signature.bind(
                *handshake.call_args.args, **handshake.call_args.kwargs,
            )
        with patch.object(template_portal, "get_agent") as get_agent:
            response = await self.client.post("/api/mcp/probe", headers=headers(),
                                             json={"agent": prefix(BOB) + "private"})
            self.assertEqual(response.status, 404)
            get_agent.assert_not_called()

    async def test_requests_and_publications_have_no_replica_local_limits(self):
        for _ in range(3):
            self.assertEqual(
                (await self.client.get("/config", headers=headers())).status,
                200,
            )
        for _ in range(2):
            response = await self.client.post(
                "/agents/test/versions",
                headers=headers(),
                json={"definition": DEFINITION},
            )
            self.assertEqual(response.status, 201)

    async def test_voice_uses_scoped_agent_fresh_session_and_no_storage(self):
        ws = await self.client.ws_connect(
            "/agents/test/endpoint/protocols/voice?store=true&agent_session_id=guessed",
            headers=headers(),
        )
        self.addAsyncCleanup(ws.close)
        self.assertEqual((await ws.receive_json())["type"], "session.created")
        call = self.ws_calls[-1]
        self.assertIn("/agents/" + prefix() + "test/", call["path"])
        self.assertEqual(call["query"]["store"], "false")
        self.assertNotEqual(call["query"]["agent_session_id"], "guessed")
        self.assertIsNone(self.app[server.SESSION_LOG_ROOT])
        await ws.send_json({"type": "response.create"})
        self.assertEqual(await ws.receive_json(), {"type": "response.create"})
        await ws.send_json({"type": "session.update", "session": {"tools": []}})
        error = await ws.receive_json()
        self.assertEqual(error["type"], "error")
        self.assertIn("disabled in the playground", error["error"]["message"])

    async def test_voice_duration_is_connection_local_without_capacity_state(self):
        self.policy.session_seconds = 1
        first = await self.client.ws_connect(
            "/agents/test/endpoint/protocols/voice",
            headers=headers(),
        )
        second = await self.client.ws_connect(
            "/agents/test/endpoint/protocols/voice",
            headers=headers(),
        )
        self.addAsyncCleanup(first.close)
        self.addAsyncCleanup(second.close)
        await first.receive_json()
        await second.receive_json()
        for websocket in (first, second):
            error = await asyncio.wait_for(websocket.receive_json(), timeout=3)
            self.assertEqual(error["error"]["code"], "playground_session_limit")


if __name__ == "__main__":
    unittest.main()
