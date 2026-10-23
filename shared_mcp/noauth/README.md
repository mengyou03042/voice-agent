# Shared no-auth MCP: `mock-tool-call` pack

The public no-auth MCP service (Container App `voice-agent-noauth-mcp`) serves the
Playground's Template tools. This directory adds the `mock-tool-call` pack to it as
a derived image: the verified base image plus
[`app/shared_mcp/mock_tool_call`](../app/shared_mcp/mock_tool_call/README.md), its
tests, and [`contracts.json`](contracts.json) with one appended pack entry. Existing
packs, routes, tools, `default_pack` and `portal_templates` are unchanged.

| Item | Value |
| --- | --- |
| Subscription | `Speech Services - DEV - Synthesis` (`f6e76fc8-e9fc-435f-982a-9007a547ea2d`) |
| Resource group / app / container | `voice-agent-portal-hosting-dev` / `voice-agent-noauth-mcp` / `noauth-mcp` |
| Registry | `vaportall3hddama.azurecr.io/voice-agent-noauth-mcp` |
| MCP URL | `https://voice-agent-noauth-mcp.lemonsky-36682081.westus2.azurecontainerapps.io/mcp/mock-tool-call` |
| Transport | Stateless Streamable HTTP, no `Authorization` header |
| Owner | yufangqin |

Agents bind the route with a direct `server_url`; no `project_connection_id`,
Authorization, or credential headers.

## Files

| File | Purpose |
| --- | --- |
| [`MockToolCall.Dockerfile`](MockToolCall.Dockerfile) | Base image digest plus the pack, test, and contract; runs every test and the pack self-check during the build |
| [`contracts.json`](contracts.json) | Live contract with the `mock-tool-call` pack appended (`P2-mock`, register `shared_mcp.mock_tool_call.pack:register`) |
| [`accept_mock_tool_call.py`](accept_mock_tool_call.py) | End-to-end acceptance: `initialize`, `tools/list`, and `tools/call` for success, business failure, invalid input, and that writes are not stored |
| [`check_routes.py`](check_routes.py) | Route regression: every contract pack answers `initialize` and `tools/list` and lists its required tools |

The base image ran its self-check as root. The derived build stays non-root and
sets `VA_MCP_OTP_STATE_DIR=/tmp/...` for that step only, because the interview pack's
default OTP directory is root-owned. A local `docker run` without Redis needs the same
variable; production uses Redis and is unaffected.

## State

The pack is stateless. Write tools (events, tickets, leads, texts, mail,
reservations, records) validate their arguments and return a generated ID, but store
nothing the caller provides, so no caller can see another caller's data. Reads return
only the fixtures in `fixtures.json`. The pack never connects to Redis; the service's
Redis settings (`NOAUTH_MCP_REDIS_*`, `NOAUTH_MCP_STATE_TTL_SECONDS`,
`NOAUTH_MCP_REQUIRE_SHARED_STATE`) are used only by the other packs. Keys that earlier
revisions wrote under `<NOAUTH_MCP_REDIS_KEY_PREFIX>:mock-tool-call:*` are no longer
read and expire on their own within 48 hours.

## Build and release

Run from `shared_mcp/`. Record the live image first; it is the rollback target. If it
is not the base digest in the Dockerfile, stop and rebase the Dockerfile on the
image the owner approves.

```bash
SUB=f6e76fc8-e9fc-435f-982a-9007a547ea2d
RG=voice-agent-portal-hosting-dev
OLD_IMAGE=$(az containerapp show --subscription $SUB -g $RG -n voice-agent-noauth-mcp \
  --query 'properties.template.containers[0].image' -o tsv)
python noauth/check_routes.py https://voice-agent-noauth-mcp.lemonsky-36682081.westus2.azurecontainerapps.io <base contract>

TAG="mock-tool-call-$(date -u +%Y%m%dT%H%M%SZ)-$(openssl rand -hex 3)"
az acr build --subscription $SUB --registry vaportall3hddama \
  --file noauth/MockToolCall.Dockerfile --image "voice-agent-noauth-mcp:$TAG" .
DIGEST=$(az acr repository show --subscription $SUB -n vaportall3hddama \
  --image "voice-agent-noauth-mcp:$TAG" --query digest -o tsv)

az containerapp update --subscription $SUB -g $RG -n voice-agent-noauth-mcp \
  --container-name noauth-mcp --image "vaportall3hddama.azurecr.io/voice-agent-noauth-mcp@$DIGEST" --output none
```

Only the image changes: environment variables, secrets, Redis settings, allowed hosts,
ingress, and replicas stay as they are. After the new revision is Healthy with 100%
traffic and 3 replicas:

```bash
python noauth/check_routes.py https://voice-agent-noauth-mcp.lemonsky-36682081.westus2.azurecontainerapps.io noauth/contracts.json
python noauth/accept_mock_tool_call.py https://voice-agent-noauth-mcp.lemonsky-36682081.westus2.azurecontainerapps.io/mcp/mock-tool-call
```

Roll back with the same `az containerapp update` and `--image "$OLD_IMAGE"`, then check
the old routes with the base contract (the new contract fails on the old image only
because the mock route does not exist there). Do not flush Redis or change the prefix.

## Release record

| Date (UTC) | Image | Revision | Result |
| --- | --- | --- | --- |
| 2026-10-20 | `sha256:0ce2f4342aa443b2e4444e29f4a45d8d7f5d45590b198be93de0055dbf012663` (tag `mock-tool-call-20261020T090800Z-481e23`) | `voice-agent-noauth-mcp--0000005`, Healthy, 3/3 replicas, 100% traffic | Build: 29 tests and 14-pack self-check passed. Before: 13/13 routes. After: 14/14 routes and the mock acceptance passed; environment variable names unchanged. Rollback image: `sha256:88cf811adcf862883473d729cacbb6d8d0d116825726b46acca095863a8cdd57` (revision `0000004`) |
| 2026-10-23 | `sha256:7640afcedc9e738ad7bbb3f3115ebd963100846c160a0e523db4e68298c601e6` (tag `mock-tool-call-stateless-20261023T075617Z`) | `voice-agent-noauth-mcp--0000006`, Healthy, 3/3 replicas, 100% traffic | Stateless mock pack: writes store nothing a caller provides. Build: 29 tests and the self-check passed. Before and after: 14/14 routes; the mock acceptance passed, including that a created ticket is not stored or searchable; environment variable names unchanged. Rollback image: `sha256:0ce2f4342aa443b2e4444e29f4a45d8d7f5d45590b198be93de0055dbf012663` (revision `0000005`) |
