# Copyright (c) Microsoft. All rights reserved.
"""Issue a private shared playground token without printing it."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import time

def issue(destination: Path, *, days: int = 7) -> dict[str, str]:
    if not 1 <= days <= 30:
        raise ValueError("Invitation validity must be between 1 and 30 days.")
    destination = destination.expanduser().absolute()
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    code = secrets.token_urlsafe(32)
    expires = int(time.time()) + days * 24 * 60 * 60
    expires_utc = datetime.fromtimestamp(expires, timezone.utc).isoformat()
    document = {
        "invitationCode": code,
        "invitationHash": hashlib.sha256(code.encode("utf-8")).hexdigest(),
        "expiresAt": expires,
        "expiresUtc": expires_utc,
    }
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(document, stream, indent=2)
        stream.write("\n")
    return {"path": str(destination), "expiresUtc": expires_utc}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    try:
        result = issue(args.destination, days=args.days)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Invitation issuance failed: {error}\n")
    print(f"Invitation saved to {result['path']}")
    print(f"Shared token expires: {result['expiresUtc']}")
    print("Keep the file private. Do not commit or paste its contents into chat.")


if __name__ == "__main__":
    main()
