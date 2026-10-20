"""Publish/read back all hosted Template versions and voice-test each default."""
from __future__ import annotations

import argparse
import asyncio
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import quote, urlencode, urlsplit
import uuid

import requests
from websockets.asyncio.client import connect


TEMPLATES = (
    "finance-example-realtime",
    "finance-example-cascade-luna",
    "finance-with-otp-and-officer-search",
    "elevator-service-example",
    "frontdesk-receptionist-example",
    "customer-support-example",
    "appointment-setter-example",
    "receptionist-messaging-example",
)
FORBIDDEN_TOOL_KEYS = {"authorization", "headers", "project_connection_id", "connection_id"}


def iter_mcp_tools(value):
    if isinstance(value, dict):
        if value.get("type") == "mcp":
            yield value
        for child in value.values():
            yield from iter_mcp_tools(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_mcp_tools(child)


def json_request(session, method, url, **kwargs):
    response = session.request(method, url, timeout=120, **kwargs)
    try:
        body = response.json()
    except ValueError as error:
        raise RuntimeError(f"{method} {url} returned non-JSON HTTP {response.status_code}") from error
    if not response.ok:
        raise RuntimeError(f"{method} {url} failed HTTP {response.status_code}: {body}")
    return response, body


async def voice_probe(base, session, api_version, agent):
    cookie = "; ".join(f"{item.name}={item.value}" for item in session.cookies)
    assert "__Host-voice_playground_access=" in cookie
    parsed = urlsplit(base)
    query = urlencode({
        "api-version": api_version,
        "agent_session_id": f"accept-{uuid.uuid4().hex[:12]}",
        "store": "false",
    })
    url = (
        f"wss://{parsed.netloc}/agents/{quote(agent, safe='')}"
        f"/endpoint/protocols/voice?{query}"
    )
    started = time.monotonic()
    result = {
        "sessionCreated": False,
        "responseCreated": False,
        "responseDone": False,
        "audioEvents": 0,
        "audioBytes": 0,
        "transcriptCharacters": 0,
        "eventTypes": [],
        "errors": [],
    }
    async with connect(
        url,
        origin=base,
        additional_headers={"Cookie": cookie, "X-MS-Synthetic-Source": "playground-acceptance"},
        max_size=16 * 1024 * 1024,
        open_timeout=60,
        ping_interval=20,
        ping_timeout=60,
    ) as websocket:
        sent = False
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            try:
                message = await asyncio.wait_for(
                    websocket.recv(), timeout=min(3, max(1, deadline - time.monotonic())),
                )
            except asyncio.TimeoutError:
                if result["sessionCreated"] and not result["responseCreated"] and not sent:
                    await websocket.send(json.dumps({
                        "type": "conversation.item.create",
                        "item": {
                            "type": "message",
                            "role": "user",
                            "content": [{
                                "type": "input_text",
                                "text": (
                                    "Hello. In one short sentence, tell me what this "
                                    "demo can help with. Do not ask for personal information."
                                ),
                            }],
                        },
                    }))
                    await websocket.send(json.dumps({"type": "response.create"}))
                    sent = True
                continue
            if isinstance(message, bytes):
                result["audioBytes"] += len(message)
                continue
            event = json.loads(message)
            event_type = str(event.get("type") or "")
            if len(result["eventTypes"]) < 40:
                result["eventTypes"].append(event_type)
            if event_type == "error":
                result["errors"].append(event.get("error") or event)
                break
            if event_type in {"session.created", "session.updated"}:
                result["sessionCreated"] = True
            elif event_type == "response.created":
                result["responseCreated"] = True
            elif event_type in {"response.audio.delta", "response.output_audio.delta"}:
                result["audioEvents"] += 1
                delta = event.get("delta")
                if isinstance(delta, str):
                    result["audioBytes"] += len(base64.b64decode(delta, validate=True))
            elif event_type in {
                "response.audio_transcript.delta",
                "response.output_audio_transcript.delta",
                "response.output_text.delta",
            }:
                result["transcriptCharacters"] += len(str(event.get("delta") or ""))
            elif event_type == "response.done":
                response = event.get("response") or {}
                if response.get("status") not in (None, "completed"):
                    result["errors"].append({
                        "code": response.get("status"),
                        "message": str(response.get("status_details") or "response did not complete"),
                    })
                result["responseDone"] = not result["errors"]
                break
    result["elapsedSeconds"] = round(time.monotonic() - started, 3)
    assert result["sessionCreated"], result
    assert result["responseCreated"], result
    assert result["responseDone"], result
    assert result["audioEvents"] > 0 and result["audioBytes"] > 0, result
    assert result["errors"] == [], result
    return result


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--invitation-file", type=Path, required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    invitation = json.loads(args.invitation_file.read_text())
    session = requests.Session()
    session.headers["User-Agent"] = "voice-agent-playground-acceptance/1.0"
    session.headers["X-MS-Synthetic-Source"] = "playground-acceptance"
    unauthorized = requests.get(
        base + "/config",
        headers={"X-MS-Synthetic-Source": "playground-acceptance"},
        timeout=60,
    )
    assert unauthorized.status_code == 401
    assert "WWW-Authenticate" not in unauthorized.headers
    login = session.post(
        base + "/login",
        data={
            "email": args.email,
            "token": invitation["invitationCode"],
            "next": "/",
        },
        headers={"Origin": base},
        timeout=60,
        allow_redirects=False,
    )
    assert login.status_code == 303
    assert login.cookies.get("__Host-voice_playground_access")
    config_response, config = json_request(session, "GET", base + "/config")
    assert config["playground"] is True
    assert config["playgroundAuthMode"] == "invite"
    templates_response, catalog = json_request(session, "GET", base + "/api/templates")
    assert templates_response.status_code == 200
    assert [card["id"] for card in catalog["templates"]] == list(TEMPLATES)
    api_version = config["apiVersion"]
    suffix = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    report = {
        "baseUrl": base,
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "invitationExpiresUtc": invitation["expiresUtc"],
        "unauthenticatedStatus": unauthorized.status_code,
        "playgroundAuthMode": config["playgroundAuthMode"],
        "templates": {},
    }
    published = []
    cases = [
        (card["id"], version["id"])
        for card in catalog["templates"]
        for version in card["versions"]
    ]
    assert not catalog["errors"], catalog["errors"]
    for index, (template_id, version) in enumerate(cases, 1):
        parameters = {"version": version}
        _, detail = json_request(
            session, "GET", f"{base}/api/templates/{template_id}", params=parameters,
        )
        assert detail["version"] == version
        definition = detail["definition"]
        assert definition["kind"] == "voice"
        assert definition["store"] is False
        tools = list(iter_mcp_tools(definition))
        assert bool(tools) == detail["requires_mcp"], (template_id, version)
        for tool in tools:
            assert not FORBIDDEN_TOOL_KEYS.intersection(tool), (template_id, tool)
            assert tool["server_url"].startswith(
                "https://voice-agent-noauth-mcp.lemonsky-36682081.westus2.azurecontainerapps.io/mcp/"
            )
        probe = None
        if tools:
            _, probe = json_request(
                session, "GET", f"{base}/api/templates/{template_id}/mcp/probe",
                params=parameters,
            )
            assert probe["ok"] is True, probe
        configure_response, configured = json_request(
            session, "POST", f"{base}/api/templates/{template_id}/mcp/configure",
            params=parameters, json={},
        )
        assert configure_response.status_code == 200
        if tools:
            assert configured["configured"] is True
        requested = f"e2e-{index}-{suffix}"
        publish_response, publication = json_request(
            session, "POST", f"{base}/api/templates/{template_id}/publish",
            params=parameters, json={"name": requested},
        )
        assert publish_response.status_code == 201
        assert publication["source_template_version"] == version
        agent = publication["agent_name"]
        assert agent.startswith("pg-")
        _, resource = json_request(
            session, "GET", f"{base}/agents/{quote(agent, safe='')}?{urlencode({'api-version': api_version})}",
        )
        latest = (resource.get("versions") or {}).get("latest") or resource
        readback = latest["definition"]
        assert readback["kind"] == "voice" and readback["store"] is False
        readback_tools = list(iter_mcp_tools(readback))
        assert bool(readback_tools) == bool(tools)
        assert readback["model"] == definition["model"]
        assert readback["instructions"] == definition["instructions"]
        for tool in readback_tools:
            assert not FORBIDDEN_TOOL_KEYS.intersection(tool), (template_id, tool)
        voice = await voice_probe(base, session, api_version, agent) if version == "." else None
        case_id = template_id if version == "." else f"{template_id}@{version}"
        report["templates"][case_id] = {
            "cardName": detail["name"],
            "sourceTemplateVersion": version,
            "instructionsSha256": hashlib.sha256(definition["instructions"].encode()).hexdigest(),
            "model": readback["model"],
            "mcpProbeTools": len(probe["tools"]) if probe else 0,
            "publishedAgent": agent,
            "readbackVersion": str(latest.get("version") or publication.get("version") or ""),
            "mcpToolBlocks": len(readback_tools),
            "voice": voice,
        }
        published.append(agent)
    _, agents = json_request(
        session, "GET",
        f"{base}/agents?{urlencode({'api-version': api_version, 'kind': 'voice', 'limit': 100})}",
    )
    names = {item["name"] for item in agents["data"]}
    assert set(published).issubset(names)
    report["publishedAgentsVisible"] = len(set(published) & names)
    report["completedAt"] = datetime.now(timezone.utc).isoformat()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "templates": {
            key: {
                "model": value["model"],
                "mcpProbeTools": value["mcpProbeTools"],
                "publishedAgent": value["publishedAgent"],
                "readbackVersion": value["readbackVersion"],
                "sourceTemplateVersion": value["sourceTemplateVersion"],
                "audioEvents": value["voice"]["audioEvents"] if value["voice"] else None,
                "audioBytes": value["voice"]["audioBytes"] if value["voice"] else None,
                "elapsedSeconds": value["voice"]["elapsedSeconds"] if value["voice"] else None,
            }
            for key, value in report["templates"].items()
        },
        "publishedAgentsVisible": report["publishedAgentsVisible"],
        "voiceChecks": sum(value["voice"] is not None for value in report["templates"].values()),
        "invitationCodePrinted": False,
        "azureDeletes": 0,
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
