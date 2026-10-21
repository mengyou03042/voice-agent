"""Statistics-contract tests, including opt-in fixture-only live KQL execution."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("playground_usage_stats", ROOT / "scripts/usage_stats.py")
stats = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stats)
NOW = datetime(2026, 10, 16, 16, tzinfo=timezone.utc)
METRICS = {
    "login_successes": 2, "login_failures": 1, "active_users": 2,
    "signed_in_users": 1, "created_agents": 2, "agent_creators": 2,
    "successful_publications": 5, "failed_publications": 1,
    "later_version_publications": 1, "unknown_publication_metadata": 1,
}


def report() -> dict:
    return {
        "window_start_utc": (NOW - timedelta(days=1)).isoformat(),
        "window_end_utc": NOW.isoformat(), "queried_at_utc": NOW.isoformat(),
        "first_heartbeat_utc": (NOW - timedelta(days=2)).isoformat(),
        "last_heartbeat_utc": (NOW - timedelta(minutes=1)).isoformat(),
        "summary": {name: 0 for name in METRICS},
        "daily": [], "creators": [],
        "malformed_records": 0, "unsupported_schema_records": 0,
    }


def fixture_query(traffic: str = "customer", *, start: datetime | None = None) -> str:
    rows = []

    def add(event_id, event_name, *, hours=1, app="voice-agent-playground", **values):
        instant = NOW - timedelta(hours=hours)
        data = {
            "event_id": event_id, "schema_version": 1, "occurred_at": instant.isoformat(),
            "event_name": event_name, "traffic_type": "customer", **values,
        }
        rows.append(
            f"datetime({instant.isoformat()}), {json.dumps(app)}, "
            + json.dumps("prefix PLAYGROUND_USAGE " + json.dumps(data))
        )

    add("h-first", "heartbeat", hours=30)
    add("h-last", "heartbeat", hours=1 / 60)
    add("login-a", "login", user_id="alice", outcome="success")
    add("login-a", "login", user_id="alice", outcome="success")
    add("login-a2", "login", user_id="alice", outcome="success")
    add("login-failed", "login", outcome="failure")
    add("bob-activity", "activity", user_id="bob", outcome="success")
    for event_id, user, agent, change in (
        ("p-a", "alice", "agent-a", "created"),
        ("p-a", "alice", "agent-a", "created"),
        ("p-a-repeat", "alice", "agent-a", "created"),
        ("p-a-v2", "alice", "agent-a", "version_published"),
        ("p-b", "bob", "agent-b", "created"),
    ):
        add(event_id, "agent_publish", user_id=user, agent_id=agent,
            outcome="success", change=change, metadata_status="complete")
    add("p-missing", "agent_publish", user_id="alice",
        outcome="success", change="unknown", metadata_status="missing")
    add("p-failed", "agent_publish", user_id="alice", outcome="failure")
    add("s-login", "login", user_id="synthetic", outcome="success", traffic_type="synthetic")
    add("s-p", "agent_publish", user_id="synthetic", agent_id="s-agent",
        outcome="success", change="created", metadata_status="complete", traffic_type="synthetic")
    add("wrong-app", "login", app="another-app", user_id="wrong-app", outcome="success")
    add("at-end", "login", hours=0, user_id="at-end", outcome="success")
    add("before-start", "login", hours=25, user_id="before-start", outcome="success")
    body = stats.build_query(start or NOW - timedelta(days=1), NOW, NOW, traffic)
    if body.count("ContainerAppConsoleLogs_CL") != 2:
        raise AssertionError("Update fixture substitution for the changed query contract.")
    body = body.replace("ContainerAppConsoleLogs_CL", "_TestLogs")
    fixture = (
        "let _TestLogs = datatable(TimeGenerated:datetime, ContainerAppName_s:string, Log_s:string) [\n"
        + ",\n".join(rows) + "\n];\n"
    )
    return fixture + body


class UsageStatsTests(unittest.TestCase):
    def test_bounds_and_traffic_are_validated(self):
        for start, end, traffic in (
            (NOW, NOW, "customer"),
            (NOW - timedelta(days=31), NOW, "customer"),
            (NOW - timedelta(days=1), NOW + timedelta(seconds=1), "customer"),
            (NOW - timedelta(days=1), NOW, 'customer"; print Secret=1;'),
        ):
            with self.subTest(start=start, end=end, traffic=traffic), self.assertRaises(ValueError):
                stats.build_query(start, end, NOW, traffic)
        with self.assertRaises(ValueError):
            stats.parse_utc("2026-10-16T16:00:00")
        self.assertEqual(stats.parse_utc("2026-10-16T18:00:00+02:00"), NOW)

    def test_empty_results_are_not_converted_to_zero(self):
        for payload in ({}, {"tables": []}, {"tables": [{"name": "PrimaryResult", "rows": []}]}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                stats.parse_result(payload)

    def test_dynamic_fields_are_parsed_and_invalid_counts_fail(self):
        original = report()
        columns = [{"name": key} for key in original]
        values = [json.dumps(value) if isinstance(value, (dict, list)) else value for value in original.values()]
        parsed = stats.parse_result({"tables": [{"name": "PrimaryResult", "columns": columns, "rows": [values]}]})
        self.assertEqual(parsed, original)
        original["summary"]["created_agents"] = -1
        with self.assertRaises(ValueError):
            stats.parse_result({"tables": [{
                "name": "PrimaryResult", "columns": columns, "rows": [list(original.values())],
            }]})

    def test_no_heartbeat_means_unknown_not_zero(self):
        value = report()
        value["first_heartbeat_utc"] = None
        value["last_heartbeat_utc"] = None
        result = stats.annotate_coverage(value)
        self.assertEqual(result["coverage_status"], "unavailable")
        self.assertTrue(all(count is None for count in result["summary"].values()))

    def test_fresh_zero_partial_stale_and_unknown_metadata_are_explicit(self):
        self.assertEqual(stats.annotate_coverage(report())["coverage_status"], "observed")
        boundary = report()
        boundary["last_heartbeat_utc"] = (NOW - timedelta(minutes=10)).isoformat()
        self.assertEqual(stats.annotate_coverage(boundary)["coverage_status"], "observed")
        boundary["last_heartbeat_utc"] = (NOW - timedelta(seconds=601)).isoformat()
        self.assertEqual(stats.annotate_coverage(boundary)["coverage_status"], "stale")
        value = report()
        value["first_heartbeat_utc"] = (NOW - timedelta(hours=1)).isoformat()
        self.assertEqual(stats.annotate_coverage(value)["coverage_status"], "partial")
        value["last_heartbeat_utc"] = (NOW - timedelta(minutes=11)).isoformat()
        self.assertEqual(stats.annotate_coverage(value)["coverage_status"], "stale")
        value = report()
        value["summary"]["unknown_publication_metadata"] = 1
        self.assertIn("lack create/version metadata", " ".join(stats.annotate_coverage(value)["warnings"]))

    def test_collection_start_at_window_end_has_no_coverage(self):
        value = report()
        value["first_heartbeat_utc"] = value["window_end_utc"]
        result = stats.annotate_coverage(value)
        self.assertEqual(result["coverage_status"], "unavailable")
        self.assertIsNone(result["summary"]["created_agents"])

    def test_query_failure_cannot_return_a_success_shaped_report(self):
        with patch.object(stats.subprocess, "run", return_value=type("Token", (), {"stdout": "synthetic-token"})()), \
                patch.object(stats.urllib.request, "urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = b'{"error":{"code":"PartialError"}}'
            with self.assertRaisesRegex(RuntimeError, "failed or partial"):
                stats.execute_query("print Test=1")
        with patch.object(stats.subprocess, "run", side_effect=subprocess.CalledProcessError(1, ["az"])), \
                self.assertRaises(subprocess.CalledProcessError):
            stats.execute_query("print Test=1")


@unittest.skipUnless(os.getenv("RUN_PLAYGROUND_USAGE_KQL") == "1", "Opt-in fixture-only Kusto validation")
class UsageKqlTests(unittest.TestCase):
    def test_production_query_with_duplicates_boundaries_and_synthetic_traffic(self):
        token = subprocess.run(
            ["az", "account", "get-access-token", "--resource", "https://kusto.kusto.windows.net",
             "--query", "accessToken", "--output", "tsv"],
            check=True, capture_output=True, text=True, timeout=60,
        ).stdout.strip()
        for traffic, start in (
            ("customer", None), ("synthetic", None), ("all", None),
            ("customer", NOW - timedelta(minutes=10)),
        ):
            with self.subTest(traffic=traffic, start=start):
                request = urllib.request.Request(
                    "https://speech.kusto.windows.net/v1/rest/query",
                    data=json.dumps({"db": "Speech Services - TTS Prod", "csl": fixture_query(traffic, start=start)}).encode(),
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=120) as response:
                    payload = json.load(response)
                table = payload["Tables"][0]
                row = dict(zip([column["ColumnName"] for column in table["Columns"]], table["Rows"][0], strict=True))
                summary = row["summary"]
                if isinstance(summary, str):
                    summary = json.loads(summary)
                if start is not None:
                    self.assertTrue(all(value == 0 for value in summary.values()))
                    daily = row["daily"]
                    self.assertEqual(json.loads(daily) if isinstance(daily, str) else daily, [])
                elif traffic == "customer":
                    self.assertEqual(summary, METRICS)
                    daily = row["daily"]
                    daily = json.loads(daily) if isinstance(daily, str) else daily
                    self.assertEqual(len(daily), 1)
                    self.assertEqual(daily[0]["created_agents"], 2)
                    self.assertEqual(daily[0]["active_users"], 2)
                elif traffic == "synthetic":
                    self.assertEqual(summary["created_agents"], 1)
                    self.assertEqual(summary["active_users"], 1)
                    self.assertEqual(summary["login_successes"], 1)
                else:
                    self.assertEqual(summary["created_agents"], 3)
                    self.assertEqual(summary["active_users"], 3)
                    self.assertEqual(summary["login_successes"], 3)


if __name__ == "__main__":
    unittest.main()
