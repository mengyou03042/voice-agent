"""End-to-end acceptance for the no-auth /mcp/mock-tool-call route.

Runs initialize, notifications/initialized, tools/list and tools/call without an
Authorization header and checks business JSON, MCP error flags and that writes are not stored.

    python accept_mock_tool_call.py https://<host>/mcp/mock-tool-call
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from typing import Any

import requests

PROTOCOL_VERSION = "2025-06-18"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


class Client:
    def __init__(self, url: str) -> None:
        self.url = url
        self.headers = dict(HEADERS)
        self.next_id = 1

    def _post(self, body: dict[str, Any]) -> requests.Response:
        response = requests.post(self.url, json=body, headers=self.headers, timeout=30, allow_redirects=False)
        response.raise_for_status()
        return response

    @staticmethod
    def _decode(response: requests.Response) -> dict[str, Any]:
        if response.headers.get("content-type", "").startswith("text/event-stream"):
            for line in response.text.splitlines():
                if line.startswith("data:"):
                    return json.loads(line[5:])
            raise AssertionError("SSE response carried no data frame")
        return response.json()

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        body = {"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params}
        self.next_id += 1
        return self._decode(self._post(body))

    def initialize(self) -> dict[str, Any]:
        response = self._post({
            "jsonrpc": "2.0",
            "id": self.next_id,
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "mock-tool-call-acceptance", "version": "1"},
            },
        })
        self.next_id += 1
        result = self._decode(response)["result"]
        self.headers["MCP-Protocol-Version"] = result["protocolVersion"]
        if response.headers.get("mcp-session-id"):
            self.headers["Mcp-Session-Id"] = response.headers["mcp-session-id"]
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return result

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.request("tools/call", {"name": name, "arguments": arguments})


def business(response: dict[str, Any]) -> dict[str, Any]:
    result = response.get("result")
    assert result is not None, response
    assert not result.get("isError"), result
    structured = result["structuredContent"]
    text = json.loads(result["content"][0]["text"])
    assert text == structured, (text, structured)
    return structured


def rejected(response: dict[str, Any]) -> bool:
    return "error" in response or bool(response.get("result", {}).get("isError"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    args = parser.parse_args()
    client = Client(args.url)
    checks: list[str] = []

    server = client.initialize()
    checks.append(f"initialize server={server['serverInfo']['name']} protocol={server['protocolVersion']}")

    listed = client.request("tools/list", {})["result"]["tools"]
    tools = {tool["name"]: tool for tool in listed}
    assert all(name.startswith("mock_tool_call_") for name in tools), sorted(tools)
    echo = tools["mock_tool_call_echo"]
    assert set(echo["inputSchema"]["required"]) == {"request_id", "text"}
    assert echo["inputSchema"]["properties"]["mode"]["enum"] == ["success", "business_error"]
    assert echo["outputSchema"]["required"]
    checks.append(f"tools/list tools={len(tools)}")

    arguments = {"request_id": "mock-demo-001", "text": "hello shared mcp", "mode": "success"}
    success = business(client.call("mock_tool_call_echo", arguments))
    assert success == {
        "mock": True, "tool": "mock_tool_call_echo", "request_id": "mock-demo-001",
        "status": "succeeded", "data": {"text": "hello shared mcp"}, "error": None,
    }, success
    assert business(client.call("mock_tool_call_echo", arguments)) == success
    failure = business(client.call("mock_tool_call_echo", {**arguments, "mode": "business_error"}))
    assert failure["status"] == "failed" and failure["data"] is None
    assert failure["error"]["code"] == "MOCK_BUSINESS_ERROR"
    assert rejected(client.call("mock_tool_call_echo", {**arguments, "mode": "other"}))
    assert rejected(client.call("mock_tool_call_echo", {"text": "missing id"}))
    assert rejected(client.call("mock_tool_call_echo", {"request_id": "   ", "text": "x"}))
    checks.append("echo success, business_error, invalid input")

    marker = uuid.uuid4().hex[:8]
    created = business(client.call("mock_tool_call_zendesk_create_ticket", {
        "subject": f"Acceptance {marker}", "description": "Mock acceptance ticket", "priority": "low",
    }))
    assert created["mock"] and created["ok"] and created["status"] == "new"
    ticket_id = str(created["ticket_id"])
    commented = business(client.call("mock_tool_call_zendesk_add_comment", {
        "ticket_id": ticket_id, "comment": "Acceptance comment",
    }))
    assert commented["ok"], commented
    searched = business(client.call("mock_tool_call_zendesk_search", {"query": f"Acceptance {marker}", "type": "tickets"}))
    assert searched["ok"] and searched["count"] == 0, searched
    checks.append(f"zendesk create/comment ticket={ticket_id}; the ticket is not stored or searchable")

    found = business(client.call("mock_tool_call_find_meeting_times", {
        "meetingDuration": "PT30M", "startDateTime": "2030-01-08T09:00:00",
        "endDateTime": "2030-01-08T17:00:00", "timeZone": "Pacific Standard Time", "maxCandidates": 3,
    }))
    assert found["ok"] and found["meetingTimeSuggestions"], found
    sms = business(client.call("mock_tool_call_twilio_send_message", {"to": "+15005550001", "body": "x"}))
    assert sms["ok"] is False and sms["error"]["code"] == "21211"
    checks.append("calendar search, sms business failure")

    for line in checks:
        print("PASS", line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
