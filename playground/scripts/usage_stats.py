"""Read recent Playground users, logins and Agent creations from Log Analytics."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ID = "9db726b4-4f06-4a94-bebd-5cf7542cbd38"
SUBSCRIPTION = "f6e76fc8-e9fc-435f-982a-9007a547ea2d"
QUERY_PATH = ROOT / "queries/usage.kql"
STALE_AFTER_SECONDS = 600
SUMMARY_FIELDS = frozenset({
    "active_users", "signed_in_users", "login_successes", "login_failures",
    "created_agents", "agent_creators", "successful_publications",
    "failed_publications", "later_version_publications", "unknown_publication_metadata",
})


def parse_utc(value: str) -> datetime:
    """Require an explicit timezone and normalize an ISO timestamp to UTC."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("UTC bounds must include Z or an explicit timezone offset.")
    return parsed.astimezone(timezone.utc)


def build_query(start: datetime, end: datetime, now: datetime, traffic: str) -> str:
    """Bind a frozen UTC reporting window to the checked-in query body."""
    if traffic not in {"customer", "synthetic", "all"}:
        raise ValueError("Traffic must be customer, synthetic, or all.")
    if not now - timedelta(days=30) <= start < end <= now:
        raise ValueError("Window must be nonempty, within the last 30 days, and not in the future.")
    bindings = [
        f"let {name} = datetime({value.isoformat()});"
        for name, value in (
            ("_WindowStart", start), ("_WindowEnd", end), ("_QueryNow", now),
        )
    ]
    bindings.append(f"let _TrafficType = {json.dumps(traffic)};")
    return "\n".join(bindings) + "\n" + QUERY_PATH.read_text(encoding="utf-8")


def execute_query(query: str) -> dict:
    """Execute one read-only query without printing or persisting credentials."""
    token = subprocess.run(
        [
            "az", "account", "get-access-token", "--subscription", SUBSCRIPTION,
            "--resource", "https://api.loganalytics.io",
            "--query", "accessToken", "--output", "tsv",
        ],
        check=True, capture_output=True, text=True, timeout=60,
    ).stdout.strip()
    if not token:
        raise RuntimeError("Azure CLI returned no Log Analytics token.")
    request = urllib.request.Request(
        f"https://api.loganalytics.azure.com/v1/workspaces/{WORKSPACE_ID}/query",
        data=json.dumps({"query": query, "timespan": "P30D"}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "x-ms-client-request-id": "playground-usage-stats",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Log Analytics query failed with HTTP {error.code}.") from error
    if payload.get("error") or payload.get("partialError"):
        raise RuntimeError("Log Analytics returned a failed or partial query; counts are unavailable.")
    return payload


def parse_result(payload: dict) -> dict:
    """Validate the one-row report rather than treating an empty result as zero."""
    tables = payload.get("tables", [])
    primary = [table for table in tables if table.get("name") == "PrimaryResult"]
    if len(primary) != 1 or len(primary[0].get("rows", [])) != 1:
        raise ValueError("Expected exactly one primary report row from Log Analytics.")
    table = primary[0]
    report = dict(zip(
        [column["name"] for column in table["columns"]], table["rows"][0], strict=True,
    ))
    for field, expected in (("summary", dict), ("daily", list), ("creators", list)):
        value = report.get(field)
        if isinstance(value, str):
            value = json.loads(value)
        if not isinstance(value, expected):
            raise ValueError(f"Query result has an invalid {field} shape.")
        report[field] = value
    if set(report["summary"]) != SUMMARY_FIELDS or any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in report["summary"].values()
    ):
        raise ValueError("Query summary must contain nonnegative integer counts.")
    return report


def annotate_coverage(report: dict) -> dict:
    """Make absent, partial or stale collection explicit in the report."""
    report = dict(report)
    warnings = []
    now = parse_utc(report["queried_at_utc"])
    start = parse_utc(report["window_start_utc"])
    end = parse_utc(report["window_end_utc"])
    first = parse_utc(report["first_heartbeat_utc"]) if report.get("first_heartbeat_utc") else None
    last = parse_utc(report["last_heartbeat_utc"]) if report.get("last_heartbeat_utc") else None
    report["heartbeat_age_seconds"] = round((now - last).total_seconds()) if last else None
    if first is None or last is None or first >= end:
        status = "unavailable"
        warnings.append("No collection heartbeat covers this window; usage is unknown, not zero.")
        report["summary"] = dict.fromkeys(report["summary"])
        report["daily"] = []
        report["creators"] = []
    elif (now - last).total_seconds() > STALE_AFTER_SECONDS:
        status = "stale"
        warnings.append("Latest heartbeat is older than ten minutes; telemetry may be delayed.")
    elif first > start:
        status = "partial"
        warnings.append("Collection began after the requested start; earlier usage cannot be reconstructed.")
    else:
        status = "observed"
    if report.get("malformed_records", 0) or report.get("unsupported_schema_records", 0):
        warnings.append("Unrecognized usage records exist; inspect telemetry schema coverage.")
        if status == "observed":
            status = "degraded"
    if report["summary"].get("unknown_publication_metadata"):
        warnings.append("Some successful publications lack create/version metadata and are not counted as creates.")
    report["coverage_status"] = status
    report["warnings"] = warnings
    report["source"] = {
        "workspace_id": WORKSPACE_ID,
        "table": "ContainerAppConsoleLogs_CL",
        "container_app": "voice-agent-playground",
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    window = parser.add_mutually_exclusive_group()
    window.add_argument("--hours", type=float, default=None)
    window.add_argument("--start", type=parse_utc)
    parser.add_argument("--end", type=parse_utc)
    parser.add_argument("--traffic", choices=("customer", "synthetic", "all"), default="customer")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    end = args.end or now
    try:
        start = args.start or end - timedelta(hours=args.hours if args.hours is not None else 24)
        query = build_query(start, end, now, args.traffic)
        report = annotate_coverage(parse_result(execute_query(query)))
    except (OSError, ValueError, OverflowError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Playground usage query failed: {error}\n")
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
