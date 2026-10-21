"""Check every pack route of a no-auth MCP deployment against a contract.

Each route must answer initialize and tools/list without an Authorization header
and expose its contract's required tools.

    python check_routes.py https://<host> contracts.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from accept_mock_tool_call import Client


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    parser.add_argument("contract", type=Path)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    failures = 0
    for pack in contract["packs"]:
        client = Client(f"{args.base_url.rstrip('/')}/mcp/{pack['name']}")
        try:
            client.initialize()
            names = {tool["name"] for tool in client.request("tools/list", {})["result"]["tools"]}
            missing = sorted(set(pack.get("required_tools") or []) - names)
        except Exception as error:  # noqa: BLE001 - report every route, then fail
            print(f"FAIL /mcp/{pack['name']}: {error}")
            failures += 1
            continue
        if missing:
            print(f"FAIL /mcp/{pack['name']}: missing {missing}")
            failures += 1
        else:
            print(f"PASS /mcp/{pack['name']} tools={len(names)}")
    print(f"{len(contract['packs']) - failures}/{len(contract['packs'])} routes passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
