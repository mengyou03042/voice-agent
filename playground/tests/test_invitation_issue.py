# Copyright (c) Microsoft. All rights reserved.
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from issue_invitation import issue


class InvitationIssuanceTests(unittest.TestCase):
    def test_issues_high_entropy_code_hash_and_private_file(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "access/invitation.local.json"
            before = int(time.time())
            result = issue(destination)
            document = json.loads(destination.read_text())
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)
            self.assertEqual(len(document["invitationCode"]), 43)
            self.assertEqual(
                document["invitationHash"],
                hashlib.sha256(document["invitationCode"].encode()).hexdigest(),
            )
            self.assertGreaterEqual(document["expiresAt"], before + 7 * 86400)
            self.assertNotIn("invitationCode", result)
            self.assertNotIn("invitationHash", result)

    def test_does_not_overwrite_an_existing_invitation(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "invitation.local.json"
            issue(destination)
            previous = destination.read_bytes()
            with self.assertRaises(FileExistsError):
                issue(destination)
            self.assertEqual(destination.read_bytes(), previous)

    def test_rejects_invalid_validity_without_creating_file(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "invitation.local.json"
            for days in (0, -1, 31):
                with self.subTest(days=days), self.assertRaises(ValueError):
                    issue(destination, days=days)
            self.assertFalse(destination.exists())

if __name__ == "__main__":
    unittest.main()
