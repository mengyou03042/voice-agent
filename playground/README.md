---
title: User Playground - 使用团队 Azure 资源的邀请码 Voice Agent 体验服务
status: active
verified: 2026-10-20
keywords: [playground, portal, hosting, invitation, managed-identity, workspace]
---

# User Playground

中文操作入口：[部署与本地调试 Guide](GUIDE.md)，包含本地 UI 启动、端口转发、Debug mode、镜像发布及回滚。

## Purpose

This directory owns the hosted Portal deployment. The checked-in source uses a
custom sign-in page instead of browser Basic authentication. One shared
high-entropy token may be distributed to multiple trusted users. Each user
enters that token and their email; a successful sign-in creates a long-lived
signed access cookie, and the normalized email deterministically selects the
user's private Agent namespace. The browser never receives Azure credentials.
The backend uses a team-owned managed identity and a fixed Foundry Project.

The active cloud revision uses this custom sign-in page and email namespace.
The two live replicas share the same signing secret and require no sticky
session.

The login page displays the access token and email fields together with one
**Sign in** button; no JavaScript or intermediate step is required. Users can
request an access token or help through the
[yiwenrong@microsoft.com](mailto:yiwenrong@microsoft.com) contact link.

The no-auth MCP service is a separate deployment owned by
`docs/voice_agent/12_noauth_mcp`. This directory consumes its public base URL
but does not build or deploy its Container App.

## Current deployment

```text
Subscription:
Speech Services - DEV - Synthesis
f6e76fc8-e9fc-435f-982a-9007a547ea2d

Resource group:
voice-agent-portal-hosting-dev

Region:
West US 2

Portal:
https://voice-agent-playground.blackground-c889ecc7.westus2.azurecontainerapps.io

MCP consumed by Portal:
https://voice-agent-noauth-mcp.lemonsky-36682081.westus2.azurecontainerapps.io
```

Azure resources:

| Resource | Name |
| --- | --- |
| Foundry account | `voice-agent-portal-l3hddama` |
| Foundry Project | `voice-agent-playground` |
| Portal Container App | `voice-agent-playground` |
| Portal environment | `voice-agent-portal-dev-env` |
| Runtime identity | `voice-agent-playground-runtime` |
| ACR | `vaportall3hddama` |
| Log Analytics | `voice-agent-portal-logs` |
| Portal replicas | `2` (`min=2`, `max=2`) |

Active Portal image:

```text
vaportall3hddama.azurecr.io/voice-agent-playground@sha256:932691d8bc193bbd762c4b832cbd91b7d7a3290fc684fc01f57cfa90ab9f971f
```

Access state:

```text
active cloud revision: voice-agent-playground--0000026
access mode: invite
custom login and email namespace deployed: yes
100% traffic: revision 0000026
sticky sessions: disabled
current shared invitation expires: 2026-10-23T09:01:49Z
```

Revision `0000026` publishes the Portal working-copy snapshot based on commit
`8c41ae3`, including Template version selection and all eight configured cards.
ACR build `cc13` succeeded on 2026-10-20. The packaged catalog has 17 versions:
eight defaults and nine backups. The image-only rollout preserved the runtime
identity, ingress, invitation and both signing/admission secrets, verified by
before/after configuration and secret fingerprints. `min=2`/`max=2` is unchanged;
both replicas are ready with zero restarts and 100% traffic.

Live acceptance published and read back all 17 versions, checked the selected
instructions, and completed eight real Voice sessions with nonempty audio and
no protocol errors. Public-MCP checks passed for the five MCP-backed defaults;
the other three samples and their backups need no MCP. Hosted browser acceptance
matched 11 deployed asset hashes, loaded an original backup at desktop and mobile
widths, checked all displayed backup versions and the login, and reported no
page errors. Fresh telemetry observed all 17 synthetic publications with zero
publication failures.

Revision `0000025` is the preferred rollback image, retaining the preceding
Portal playback and UI fixes. Revision `0000024` is the older security-fixed
fallback. It was the pip-only remediation for
[IcM 887686614](https://portal.microsofticm.com/imp/v5/incidents/details/887686614/summary).
The new image retains pip `26.2` and removal of the old `ensurepip` bootstrap
wheel, verified during the build. A passing build is not a clean vulnerability
scan or proof of automatic IcM closure. See
[build and rollback guidance](STARTUP.md).

The obsolete Princeton URL
`https://voice-agent-playground.mangomushroom-bf4e76a2.westus2.azurecontainerapps.io`
is stopped and returns 404.

## Request path

```text
invited browser
  -> custom shared-token and email sign-in
  -> Portal Container App
  -> signed persistent email access cookie
  -> deterministic email Agent namespace
  -> user-assigned managed identity
  -> voice-agent-playground Foundry Project
  -> direct no-auth MCP server_url
  -> docs/voice_agent/12_noauth_mcp Container App
```

The `__Host-voice_playground_access` cookie is `HttpOnly`, `Secure`,
`SameSite=Lax`, signed by the server and valid for 365 days by default. A user
does not enter the token again unless the cookie expires or is cleared.

`.run/access/invitation.local.json` contains the shared high-entropy token and
uses mode `0600`. Only its SHA-256 hash and expiry are deployed. Give the same
raw token to each trusted user through an approved secret channel. Do not put
the token in Git, URLs, command lines, logs, screenshots or chat.

Every Agent name is prefixed with a deterministic hash of the normalized email.
The Agent list, read, publish, MCP probe and Voice WebSocket paths use the same
ownership check. The same email sees the same Agents from another authenticated
browser. The shared token can establish multiple email namespaces. Once a
browser has selected an email, cross-email Agent access returns 404 before a
request reaches Foundry.

The email is a self-asserted namespace key, not a verified identity. Any person
who possesses the shared token can enter another known email and receive that
email's namespace. Use this mode only for a trusted evaluation group. Inbox
verification, Microsoft Entra authentication or per-user credentials are
required if the email boundary must resist intentional impersonation.

The first deployment of this policy invalidates the previous Basic-auth access
cookie and stops using the random workspace cookie as identity. Existing
random-workspace Agents remain in Foundry but cannot be attributed to an email
automatically; treat them as pre-migration demo data and clean them up through a
separate bounded operation.

## Source and ownership boundaries

| Location | Responsibility |
| --- | --- |
| `voice-agent/portal` | Public Portal UI and generic local runtime |
| `voice-agent/samples` | Eight configured Template cards across seven sample projects, including their backup versions |
| `docs/voice_agent/03_user_playground` | Hosted Portal runtime policy, image adaptation, Portal IaC and operations |
| `docs/voice_agent/12_noauth_mcp` | Public MCP composition, contracts, MCP IaC and canonical live integration test |
| `docs/voice_agent/11_mcp_server` | Existing deployed multi-pack MCP; not modified by the playground |
| `voice-agent/shared_mcp` | Canonical P0 sample business packs; not modified by the playground |

`build_context.py` stages an allowlisted copy of the public Portal and applies
`patches/portal-hosting.patch`, `runtime/` and `profile.json` in a new build
directory. It does not modify the public checkout.
The configured Agent filenames and matching nested backup files are copied
from each sample folder; unrelated files, credentials and local state are not
added to the image. Patched source files retain mode `0644` even when staging
runs under a private `umask`, so the non-root image can read them.

The public checkout carries native public no-auth Template bindings and an
optional `templates.local.config.json` override for local managed connections.
The staged hosting package owns invitation admission, email namespace policy,
managed identity and hosted policy.

## Editor experience

The default entry is **Editor** at `/editor/`; existing `/handoff/` links
redirect there with their query parameters preserved. AgentRuntime remains
at `/demo/`, including existing root links with an `agent` query.

- The sidebar shows searchable Agent cards and **Nodes / Edges** navigation.
  Project selection, duplicate New Agent actions and parameter forms are omitted.
  Agent cards use a white surface and mint selection treatment instead of a
  native gray list box.
- **Create blank**, **Load from templates** and the green **Try it now** action
  share the top row. Template loading and Try it now have animated color borders.
- For an existing Agent loaded from the sidebar, **Try it now** opens that
  Agent in Runtime and starts its voice session. An unchanged published
  definition is not republished; local edits or a draft are published and
  verified first. The browser may request microphone permission.
- New working copies still validate, publish and read back before opening
  Runtime, where **Connect & start session** starts the microphone. Ordinary
  Runtime links and reloads never carry the Editor's one-shot start request.
- **Export** and **Format view** are on the canvas.
- Node costs use US cents per minute; complete latency ranges use one blue
  text style. Expanding the metrics shows a short disclaimer, not methodology.
- Resizing the canvas preserves the current graph center and zoom.
- Costs use the [audited conservative budget](../cost/04_node_model_cost_quick_reference.md):
  full audio minutes, context/reasoning reserves, no cache discount, and higher
  explicitly identified allowances for unverified rates.
- Desktop AgentRuntime defaults to equal graph/debug and conversation widths.
  Dragging remains available; Home or a double-click returns to 50/50.
- Completed node visits have a large green COMPLETED badge and checkmark.
  Re-entry restores LIVE; interrupted visits show STOPPED instead of a false
  completion. A completed visit is not a claim that every business operation
  succeeded.

## Runtime restrictions

- Fixed Foundry Project; browser Project switching is disabled.
- Managed models are restricted to the hosted catalog.
- `store=false`; Portal session recording is disabled.
- Arbitrary MCP URL, bearer, Project connection, BYOM, hosted Agent, subagent,
  Toolbox and avatar configuration are rejected.
- 300 seconds maximum per Voice session.
- Agent-list pagination is disabled after the filtered current Foundry page;
  no cursor is stored or returned.
- API, publication, invitation-attempt and Voice-concurrency limits are not
  enforced inside the Portal.

The signed access cookie, deterministic email Agent namespace and Foundry
storage are replica independent. The code and Bicep support multiple replicas
without sticky sessions. The accepted live revision runs two ready replicas.

Before increasing public traffic, add shared abuse controls at ingress if
needed, daily cost alerts, Agent TTL cleanup and a kill switch. Do not add
replica-local counters and describe them as global limits.

## Templates and MCP

The hosted catalog retains all 35 configured Portal cards. Each card offers
**Default** plus its discovered backup versions, named by the `/`-joined
relative folders. The current Customer Support, Appointment Setter and
Receptionist and Messaging samples each expose `original`, `revised` and
`shared_prompt_v1` backups in addition to Default.

The hosted profile applies `store=false` to every version. For the 32
MCP-backed cards (the five shared-MCP examples and the 27 ElevenLabs-converted
examples on the `mock-tool-call` route) it also applies:

```text
store=false
connection_mode=public
server_url=${VOICE_PLAYGROUND_MCP_BASE_URL}/mcp/<template-route>
```

Front Desk is defined in the public source's
[`example4_frontdesk_with_fluency_and_handoff`](../../../voice-agent/samples/example4_frontdesk_with_fluency_and_handoff/README.md).
This directory adds only its profile binding to `/mcp/frontdesk`; the build
reads the Agent files named by the Portal catalog. The shared prompt, workflow, and business
tool behavior are not copied into the hosted runtime.

No Agent definition contains `project_connection_id`, bearer, Authorization
header or custom credential header.

When a working copy in the Editor uses mock tools, a banner names their systems and
**Connect my tools** connects one system at a time (Salesforce, Zendesk, Twilio
SMS, and others) to the user's own public HTTPS MCP server: the Editor discovers
the server's tools, maps the system's tools to them, and rewrites the working
copy, leaving other systems on mock data. Microsoft 365 (Work IQ) tools stay on
mock data because they act as the signed-in user. The hosted policy accepts such a
server only without credentials, user info, query, or Project connection, and
only after the Portal's private-address check. Set
`VOICE_PLAYGROUND_ALLOW_CUSTOM_MCP=false` to allow only catalog bindings. The
banner links `/guide/real-tools`
([Connect real tools](../docs/05_connect_real_tools.md)).
Hosted model and MCP-tool approvals include all packaged versions, while
publication continues to enforce the same no-credentials and no-storage policy.

The profile owns the hosted Template-to-route bindings. MCP route inventories
and deployment integration tests are owned by
`docs/voice_agent/12_noauth_mcp/contracts.json`; Front Desk reuses the existing
`frontdesk` pack without adding or changing a deployed MCP route.

## Validation ownership

Component tests:

- `03_user_playground/tests/test_playground.py` validates the custom sign-in
  page, shared-token email namespaces, persistent cookies, hosted policy, packaging,
  namespaces and WebSocket guards with synthetic Azure fixtures.
- Public Portal and business-pack repositories retain their own unit tests.

Deployment/integration test:

```text
scripts/accept_live.py
scripts/accept_browser.mjs
docs/voice_agent/12_noauth_mcp/scripts/validate_live.py
```

The MCP validator owns live route inventory. The playground validators own the shared-token email sign-in flow, browser pages, all
four Template publications/readbacks and real audio-producing Voice sessions.

The initial 2026-10-16 validation published all four Templates to the actual
Project. Every readback retained `store=false`, public MCP URLs and no
connection/credential fields. Every Voice session reached `session.created`,
`response.created` and `response.done`, produced audio and emitted no error.
Detailed evidence is in [acceptance results](ACCEPTANCE_2026-10-16.md).
The subsequent login-only release was verified with real browser form
submission, desktop/mobile field visibility, secure cookies and Studio pages;
it did not republish Agents or rerun Voice sessions.

## Operations

- Deployment and local debugging guide (Chinese): [GUIDE.md](GUIDE.md)
- Usage telemetry design and recent user/Agent statistics: [TELEMETRY.md](TELEMETRY.md)
- Build, start, stop and rollback: `STARTUP.md`
- Portal/Foundry/Voice troubleshooting: `DEBUGGING.md`
- Replica model and HA prerequisites: `SCALING.md`
- MCP deployment and protocol troubleshooting:
  `../12_noauth_mcp/README.md` and `../12_noauth_mcp/DEBUGGING.md`
- Historical experiments and superseded deployment plans: `history/`

Files under `history/` are evidence only. Do not execute their commands as the
current runbook.

For "recent users and Agent create", query the last 24 hours by default:

```bash
python docs/voice_agent/03_user_playground/scripts/usage_stats.py --hours 24
```

Run this from the workspace root with an Azure CLI identity that can read
`voice-agent-portal-logs`. Use `--hours 168` for seven days or explicit
`--start` / `--end` UTC bounds. The JSON reports users, successful/failed
logins, first-created Agents, creators, version publications, daily usage and
collection freshness. Synthetic acceptance traffic is excluded by default;
`--traffic synthetic` selects it explicitly. Missing telemetry is unknown,
not zero. Before collection started, login/activity history cannot be recovered.

## Security boundary

The Portal requires an invitation, but the MCP is intentionally public no-auth.
Both must contain only fictional sample data. Portal invitation admission does
not authenticate direct MCP callers and does not make the public MCP suitable
for real customer data.
