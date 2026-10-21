---
title: User Playground usage telemetry and recent statistics
status: implemented-and-live-verified
verified: 2026-10-16
keywords: [playground, telemetry, users, login, active-users, agent-create, kusto, statistics]
---

# User Playground usage telemetry

## Purpose and current evidence

This design covers this independently hosted Playground, not the Foundry UI:

```text
https://voice-agent-playground.blackground-c889ecc7.westus2.azurecontainerapps.io
```

The primary questions are how many users sign in, how many return, and how many
Agents they create. Voice latency and dependency health are secondary to this
first implementation.

Before this change, the hosted login issued a signed cookie without emitting
login statistics. HTTP access logging was disabled. Foundry Agent lifecycle
analytics could count successful first versions, but could not count users who
only signed in or failures rejected before publication.

A read-only query at 2026-10-16 15:48 UTC found 38 first-version Agents in the
Playground Project over the preceding seven days: nine in one email namespace,
26 in legacy workspace namespaces, and three with other names. These include
possible acceptance traffic. The latest observed creation was 14:49 UTC.
This is historical evidence, not a login-user count or a live baseline.

## Implementation and ownership

The hosted runtime emits bounded JSON usage records to the existing
`voice_agent_portal` logger. Container Apps collects its console output into:

| Setting | Value |
| --- | --- |
| Subscription | `f6e76fc8-e9fc-435f-982a-9007a547ea2d` |
| Resource group | `voice-agent-portal-hosting-dev` |
| Log Analytics workspace | `voice-agent-portal-logs` |
| Workspace ID | `9db726b4-4f06-4a94-bebd-5cf7542cbd38` |
| Table | `ContainerAppConsoleLogs_CL` |
| Container App filter | `ContainerAppName_s == "voice-agent-playground"` |
| Retention at design time | 30 days |

This reuses the existing ingestion path and Azure CLI read access. It does not
introduce an Aria event/table, a second analytics store, per-replica usage
counters, or customer-facing analytics endpoints.

The implementation stays in this deployment directory. The public Portal
checkout is not edited. `build_context.py` stages the telemetry module and the
hosting adapter installs it only for the hosted Playground.

## Event contract

Each console record contains the marker `PLAYGROUND_USAGE ` followed by one
JSON object. The schema version is `1`.

Common fields:

- `event_id`: server-generated UUID for ingestion deduplication.
- `occurred_at`: server UTC timestamp, used for reporting windows.
- `event_name`: one of the event names below.
- `schema_version`: integer schema version.
- `request_id`: existing Portal request ID when applicable.
- `user_id`: existing opaque namespace subject, after authentication only.
- `traffic_type`: `customer` or `synthetic`.
- `outcome`, `http_status`, `duration_ms`: bounded request outcome and timing
  when applicable.

No email address, invitation, cookie, authorization header, IP address,
user-agent string, full URL, customer Agent name, definition, transcript,
request body, exception text, or audio enters the usage record.

| Event | Boundary | Additional fields |
| --- | --- | --- |
| `heartbeat` | Startup and every 60 seconds while the process is running | None; not user traffic |
| `login` | Terminal response to `POST /login`, including rejected forms | `outcome`; failed logins have no attributed user |
| `activity` | Authenticated document/config/API requests, excluding static assets and health probes | Bounded request category, not the raw route |
| `agent_publish` | Terminal response for direct version publication or Template publication | Hashed `agent_id`, numeric `version`, `change`, allowlisted `template_id`, `metadata_status` |

An outer hosted middleware observes the final response, including failures
converted by the existing boundary. It does not change authentication,
exception handling, API payloads, cookies, or response status.

For publication, `change` is `created` only for a successful, identified Agent
whose returned version is `1`. A higher version is `version_published`.
Successful publication with missing or invalid identity/version metadata is
`unknown`, not a fabricated creation. Those rows are counted explicitly.

Creating a local blank working copy is **not** a persisted Agent creation.
This first implementation measures successful server-side first publication,
not local drafts. A downstream creation followed by a lost/failed response can
also be absent from the observed successful-create count; Foundry lifecycle
analytics remains the reconciliation source.

## User identity and test traffic

Invite login already normalizes the email and derives a stable opaque subject.
Reuse that subject so the same email has one identity across browsers, replicas,
and releases. Do not introduce another user identifier or log the raw email.
An email is self-asserted; counts describe namespaces, not verified people.

The access cookie lasts 365 days by default. Therefore login submissions are
not an active-user measure. Successful authenticated activity and publication
must also contribute to active users.

Requests with a nonempty `X-MS-Synthetic-Source` header are marked `synthetic`.
Acceptance scripts set that header for their whole HTTP/browser context.
All other requests are `customer`. This is an observability convention, not an
authentication or billing boundary. Historical unmarked tests cannot be
retroactively distinguished from customer activity.

## Metric definitions

All time ranges are explicit UTC half-open intervals `[start, end)`. Event IDs
are deduplicated across both replicas before aggregation.

| Metric | Definition |
| --- | --- |
| Login successes / failures | Terminal `login` events by outcome |
| Unique signed-in users | Distinct nonempty `user_id` on successful login |
| Active users | Distinct authenticated subjects on login, activity or publication in the window |
| Created Agents | Distinct hashed `agent_id` on successful `agent_publish` with `change == "created"` |
| Agent creators | Distinct `user_id` contributing to Created Agents |
| Successful publications | All successful publication results, including later versions |
| Failed publications | Failed publication results, including pre-publication validation failures |
| Later-version publications | Successful results with `change == "version_published"` |
| Unknown publication metadata | Successful publication results that cannot classify creation versus update |
| Daily usage | Same definitions grouped by UTC event day |
| Creator distribution | Created Agents and publication counts per anonymous user |

The reporting command defaults to the last 24 hours and excludes synthetic
events. It supports explicit UTC bounds and an opt-in synthetic selection for
verification. Counts use distinct identities rather than approximate user
counts. Do not add the native Foundry creation totals to Portal creation totals:
they can describe the same Agents.

Registration count and all-time new/returning users are not available from a
30-day log store. "First observed in retained history" is not registration or
first-ever use. Current retained inventory is also different from creations in
a time window; deletion does not erase a historical creation.

## Querying recent statistics

From the canonical workspace root:

```bash
python docs/voice_agent/03_user_playground/scripts/usage_stats.py --hours 24
python docs/voice_agent/03_user_playground/scripts/usage_stats.py --hours 168
python docs/voice_agent/03_user_playground/scripts/usage_stats.py \
  --hours 1 --traffic synthetic
python docs/voice_agent/03_user_playground/scripts/usage_stats.py \
  --start 2026-10-16T16:12:00Z --end 2026-10-16T16:15:00Z
```

The command obtains a token through the signed-in Azure CLI identity without
printing or storing it. It reads the checked-in `queries/usage.kql`, performs
read-only Log Analytics queries and prints structured JSON. Permission or
query errors are failures, not zero usage.

When the user asks "recent users and Agent create", run the 24-hour command
unless they specify a different period. Answer with the actual UTC window,
active users, signed-in users, login successes/failures, created Agents,
creators, publication failures and telemetry freshness. Include the daily or
creator breakdown if useful. Never reuse numbers from this document as live
statistics.

## Data coverage and freshness

The report includes collection start, latest heartbeat, latest event/ingestion
times and a coverage status.

- No heartbeat: metrics are unavailable, not healthy zero traffic.
- Latest heartbeat more than ten minutes old: telemetry is stale.
- Requested start before the first retained heartbeat: partial coverage;
  pre-instrumentation login/activity cannot be recovered.
- Fresh heartbeat with no matching user events: observed usage can be zero.
- Missing publication metadata: expose it as unknown; do not silently classify
  it as a create or update.

Heartbeat freshness is evidence that the process's telemetry arrives, not a
guarantee of lossless delivery. Reports remain observed statistics and can
change as late records arrive. Container logs have finite retention and are
not a durable identity registry or a billing ledger.

## Verification and release gate

Before deploying:

1. Verify login success, invalid/expired input, returning cookie activity,
   anonymous isolation, and no authenticated attribution on failed admission.
2. Verify both publication paths, first versus later versions, missing
   metadata and failed validation.
3. Assert privacy allowlists and exclusion of probes/static assets.
4. Test query parsing, explicit bounds, empty/stale/partial windows,
   synthetic exclusion, distinct users/Agents and duplicate ingestion.
5. Execute the production KQL against fixed fixture rows in authorized Kusto.

Release through the existing image-only workflow in `STARTUP.md`, preserving
the signing key, invitation, runtime identity and scale settings. Verify a
fresh heartbeat and marked synthetic login/activity/publication in the actual
Log Analytics workspace. Preserve an immutable previous image for rollback.
Do not call local tests proof that cloud ingestion is working.

## Verified release: 2026-10-16

- ACR build `cct` succeeded.
- Immutable image:
  `vaportall3hddama.azurecr.io/voice-agent-playground@sha256:65abc1e96c22eb2032cd351df7d097e35abba907d01f0a8955c6172f43e77a29`.
- Revision `voice-agent-playground--0000018` received 100% of traffic. Both
  replicas were Running and ready with zero restarts; min/max remained two.
- Signing secrets, invitation, managed identity, MCP deployment and scale
  configuration were not changed.
- Collection began at `2026-10-16T16:11:37.786822Z`.
- All 43 focused unit/integration tests passed. The opt-in Kusto test executed
  this exact query body against fixture-only datatables for customer,
  synthetic, combined and zero-usage windows, including duplicate ingestion,
  repeated first-version records and the exclusive end boundary.

Run the same tests from the workspace root using the existing Portal environment:

```bash
RUN_PLAYGROUND_USAGE_KQL=1 voice-agent/portal/.venv/bin/python \
  -m unittest discover -s docs/voice_agent/03_user_playground/tests -q
```

The flag enables only fixed-fixture, read-only Kusto queries. Without it, the
live KQL test is skipped and the other tests remain local.

An actual synthetic probe ran from `16:14:20.646726Z` to `16:14:33.476507Z`.
At `16:16:41.678819Z`, the production Log Analytics query returned:

| Metric | Expected and observed |
| --- | ---: |
| Active users / signed-in users | 1 / 1 |
| Successful / failed logins | 2 / 1 |
| Created Agents / creators | 1 / 1 |
| Successful publications | 2 |
| Later-version publications | 1 |
| Failed publications | 1 |
| Unknown publication metadata | 0 |

The daily and per-creator aggregates also matched. The heartbeat was four
seconds old, and malformed/unsupported-schema records were zero. The synthetic
Agent was deleted through the Foundry API after verification. The native
version-publication endpoint returned HTTP 200 while Template publication
returned 201; telemetry correctly accepts both as successful results.

These are acceptance measurements, not customer adoption. The default customer
report excluded them and initially showed zero observed users/creations, with
partial coverage because the requested 24-hour window predates collection.
Never present that as zero usage for the full pre-instrumentation day.

## Current-release follow-up: revision 0000019

A concurrent Editor UI release superseded revision `0000018` with
`voice-agent-playground--0000019`, using image
`sha256:8ca1e029c7caa9b883e8d8746cdfb888d8d9876472e3097deb4a470b0cb041e4`.
It retained this telemetry implementation; it was not rolled back to the
telemetry-only image.

Both `0000019` replicas independently emitted usage heartbeats to the actual
workspace. A second isolated synthetic probe ran from
`2026-10-16T16:21:55.278340Z` to `16:22:09.225061Z`. At `16:23:05.047343Z`,
the production query exactly matched every count in the preceding acceptance
table, including one distinct signed-in user, one new Agent, one later version
and one failed publication. Coverage was `observed`, the heartbeat was 13
seconds old, and the synthetic Agent was deleted.

The 43-test suite, including all fixture-only live KQL cases, passed again.
The ignored private deployment parameters matched the actual `0000019` image,
and min/max replicas remained two. Default queries continue to exclude all
marked synthetic acceptance traffic.

## 结论

This implementation makes recent Playground users, logins and Agent creations
queryable from one repeatable command. It deliberately separates first
creation from version publication, and missing data from zero use. Historical
login data is unavailable; the report must always show its collection coverage.
