# Copyright (c) Microsoft. All rights reserved.
"""Optional legacy bearer-MCP connection setup; not used by the public profile."""
from __future__ import annotations

import argparse
import os
import re
from urllib.parse import quote, urlsplit

import requests
from azure.identity import AzureCliCredential

ARM_SCOPE = "https://management.azure.com/.default"
API_VERSION = "2025-04-01-preview"
CONNECTIONS = {
    "voice-agent-playground-finance-handoff": "/mcp/finance-handoff",
    "voice-agent-playground-finance-otp-officer": "/mcp/finance-otp-officer",
    "voice-agent-playground-elevator-service": "/mcp/elevator-service",
}


def validate_account_id(value: str) -> str:
    value = value.rstrip("/")
    if not re.fullmatch(
        r"/subscriptions/[0-9a-fA-F-]{36}/resourceGroups/[^/]+"
        r"/providers/Microsoft\.CognitiveServices/accounts/[^/]+",
        value,
    ):
        raise ValueError("Invalid Cognitive Services account resource ID.")
    return value


def validate_base_url(value: str) -> str:
    value = value.rstrip("/")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("MCP base URL must be an HTTPS origin.")
    return value


def configure(
    *,
    account_id: str,
    mcp_base_url: str,
    bearer_token: str,
) -> list[dict[str, str | int]]:
    account_id = validate_account_id(account_id)
    mcp_base_url = validate_base_url(mcp_base_url)
    bearer_token = bearer_token.strip()
    if len(bearer_token) < 32:
        raise ValueError("SHARED_MCP_TOKEN must contain at least 32 characters.")
    credential = AzureCliCredential(process_timeout=30)
    results = []
    try:
        arm_token = credential.get_token(ARM_SCOPE).token
        headers = {
            "Authorization": f"Bearer {arm_token}",
            "Content-Type": "application/json",
        }
        for connection_name, route in CONNECTIONS.items():
            server_url = mcp_base_url + route
            response = requests.put(
                (
                    f"https://management.azure.com{account_id}/connections/"
                    f"{quote(connection_name, safe='')}"
                ),
                params={"api-version": API_VERSION},
                headers=headers,
                json={
                    "properties": {
                        "category": "RemoteTool",
                        "target": server_url,
                        "authType": "CustomKeys",
                        "isDefault": False,
                        "isSharedToAll": False,
                        "credentials": {
                            "keys": {"Authorization": f"Bearer {bearer_token}"}
                        },
                        "metadata": {
                            "displayName": connection_name,
                            "source": "voice-agent-playground-hosted-profile",
                        },
                    }
                },
                timeout=60,
            )
            if not response.ok:
                raise RuntimeError(
                    f"Connection {connection_name} failed with HTTP "
                    f"{response.status_code} ({response.reason})."
                )
            body = response.json()
            target = str((body.get("properties") or {}).get("target") or "")
            if target != server_url:
                raise RuntimeError(f"Connection {connection_name} target readback mismatched.")
            results.append({
                "name": connection_name,
                "server_url": server_url,
                "status": response.status_code,
            })
    finally:
        credential.close()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--mcp-base-url", required=True)
    args = parser.parse_args()
    try:
        results = configure(
            account_id=args.account_id,
            mcp_base_url=args.mcp_base_url,
            bearer_token=os.environ.get("SHARED_MCP_TOKEN", ""),
        )
    except (OSError, ValueError, RuntimeError, requests.RequestException) as error:
        parser.exit(1, f"Connection configuration failed: {error}\n")
    for result in results:
        print(
            f"configured {result['name']} -> {result['server_url']} "
            f"(HTTP {result['status']})"
        )


if __name__ == "__main__":
    main()
