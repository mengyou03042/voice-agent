# User Playground debugging

## Start with the ownership boundary

```text
Browser/UI/Agent publication/Voice bridge:
docs/voice_agent/03_user_playground

MCP routes/tools/no-auth transport:
docs/voice_agent/12_noauth_mcp

Generic Portal behavior:
voice-agent/portal

Business tool behavior:
voice-agent/shared_mcp or the selected 11 MCP source pack
```

Do not diagnose a tool result failure by changing Portal identity or Project
RBAC before proving which layer failed.

## Current endpoints

```text
Portal:
https://voice-agent-playground.blackground-c889ecc7.westus2.azurecontainerapps.io

MCP:
https://voice-agent-noauth-mcp.lemonsky-36682081.westus2.azurecontainerapps.io
```

The `mangomushroom` Portal URL and
`voice-agent-playground-mcp.blackground...` MCP URL are superseded.

The Portal uses the custom
`/login` page. API requests without the signed access cookie return 401 without
a `WWW-Authenticate` header. The form accepts an approved shared token plus a
syntactically valid email; no browser-native Basic prompt should appear. The
email selects a namespace but is not inbox-verified. Health remains
unauthenticated.

## Debug sequence

For user/login/Agent-create statistics rather than runtime troubleshooting, use
the [telemetry design and query contract](TELEMETRY.md). From the workspace root:

```bash
python docs/voice_agent/03_user_playground/scripts/usage_stats.py --hours 24
```

Check `coverage_status`, heartbeat age and warnings before interpreting the
counts. Use `--traffic synthetic` when verifying an acceptance run. Never
count raw console lines as users or interpret a query failure as zero traffic.

### 1. Azure resource and revision

```bash
az containerapp show \
  --subscription f6e76fc8-e9fc-435f-982a-9007a547ea2d \
  --resource-group voice-agent-portal-hosting-dev \
  --name voice-agent-playground \
  --query '{running:properties.runningStatus,latest:properties.latestRevisionName,ready:properties.latestReadyRevisionName,image:properties.template.containers[0].image,ingress:properties.configuration.ingress}'

az containerapp revision list \
  --subscription f6e76fc8-e9fc-435f-982a-9007a547ea2d \
  --resource-group voice-agent-portal-hosting-dev \
  --name voice-agent-playground \
  --query '[].{name:name,active:properties.active,health:properties.healthState,traffic:properties.trafficWeight,image:properties.template.containers[0].image}'
```

Confirm 100% traffic is on the expected immutable digest. The accepted live
revision is `min=2`, `max=2`; both replicas must be ready.

Verify environment availability settings:

```bash
az containerapp env show \
  --subscription f6e76fc8-e9fc-435f-982a-9007a547ea2d \
  --resource-group voice-agent-portal-hosting-dev \
  --name voice-agent-portal-dev-env \
  --query '{zoneRedundant:properties.zoneRedundant}'

az containerapp show \
  --subscription f6e76fc8-e9fc-435f-982a-9007a547ea2d \
  --resource-group voice-agent-portal-hosting-dev \
  --name voice-agent-playground \
  --query '{sticky:properties.configuration.ingress.stickySessions,min:properties.template.scale.minReplicas,max:properties.template.scale.maxReplicas}'
```

### 2. Health and browser configuration

```bash
curl --fail https://voice-agent-playground.blackground-c889ecc7.westus2.azurecontainerapps.io/healthz
test "$(curl -sS -o /dev/null -w '%{http_code}' \
  https://voice-agent-playground.blackground-c889ecc7.westus2.azurecontainerapps.io/config)" = 401
```

`/config` must report the fixed hosted Project. Template details must contain
the `12_noauth_mcp` direct `server_url`, `store=false`, and no connection or
credential fields.

If a normal login form reports `Cross-origin requests are not allowed.`,
inspect the POST's `Origin` and `Sec-Fetch-Site` headers. With
`Referrer-Policy: no-referrer`, browsers can send `Origin: null` for a
same-origin form submission. The hosted policy accepts that combination only
when `Sec-Fetch-Site: same-origin`; an explicit foreign origin, a cross-site
request, or `Origin: null` without same-origin browser metadata remains
rejected. Do not disable the origin check or add wildcard CORS headers.

Use the real browser acceptance script, not just an HTTP client that manually
sets the expected `Origin`. It verifies that token and email are visible
together, the contact link targets `yiwenrong@microsoft.com`, and the native
form submission reaches the Studio with a secure access cookie.

### 3. Email access cookie

The successful login response should set
`__Host-voice_playground_access` with:

```text
HttpOnly
Secure
SameSite=Lax
```

The signed cookie is valid for `accessCookieDays`, 365 by default. Two fresh
HTTP sessions authenticated with the same email may receive different cookie
values, but must produce the same deterministic Agent namespace. Two different
emails must produce different namespaces. A WebSocket without the access cookie
is rejected, and one email reading another email's Agent receives 404.

The previous `voice_playground_workspace` cookie is not an identity in invite
mode and is deleted during the new login flow. Email identity comes from the
self-asserted normalized email after shared-token admission and is retained only
as a signed, opaque subject in the access cookie.

### 4. Agent publish

Publish failures are returned with a Portal request ID. Check:

```bash
az containerapp logs show \
  --subscription f6e76fc8-e9fc-435f-982a-9007a547ea2d \
  --resource-group voice-agent-portal-hosting-dev \
  --name voice-agent-playground \
  --tail 100 --format text
```

Common causes:

| Error | Cause | Action |
| --- | --- | --- |
| model not supported in region | Wrong Foundry account region | Use the fixed West US 2 account; do not silently change a locked Template |
| Agent name over 63 characters | Workspace prefix plus Template name | Hosted policy must apply deterministic hash shortening |
| MCP URL rejected as private | Portal and MCP accidentally share an environment or stale URL | Use the independent `lemonsky` MCP URL |
| 403 Agents write | Runtime identity missing Project data role | Verify role `19c28022-e58e-450d-a464-0b2a53034789` at Project scope |

### 5. MCP

Run the canonical validator:

```bash
python ../12_noauth_mcp/scripts/validate_live.py \
  --mcp-base-url \
  https://voice-agent-noauth-mcp.lemonsky-36682081.westus2.azurecontainerapps.io
```

Do not add Project connections or bearer credentials to fix a no-auth route.

### 6. Voice WebSocket

Confirm:

1. HTTP Agent publication succeeded.
2. The browser uses `wss://<portal>/agents/<owned-agent>/endpoint/protocols/voice`.
3. The request carries the signed access cookie.
4. The server generates a new `agent_session_id`.
5. The upstream events include `session.created` and `response.done`.

An error saying `Conversation already has an active response` usually means a
test sent `response.create` while a Template greeting was already running.
Wait for the initial response to finish; do not change the Agent.

### 7. Logs and secrets

Portal logs may contain request IDs and type names, but must not contain Azure
tokens, shared invitation tokens, email addresses, access
cookie values, MCP Authorization values or raw audio.

Never print secret parameter files. Use ARM REST instead of Microsoft Graph for
RBAC verification when Conditional Access blocks Graph tokens.

Example Project-scoped ARM query:

```bash
principal=$(az identity show \
  --subscription f6e76fc8-e9fc-435f-982a-9007a547ea2d \
  --resource-group voice-agent-portal-hosting-dev \
  --name voice-agent-playground-runtime \
  --query principalId -o tsv)

project='/subscriptions/f6e76fc8-e9fc-435f-982a-9007a547ea2d/resourceGroups/voice-agent-portal-hosting-dev/providers/Microsoft.CognitiveServices/accounts/voice-agent-portal-l3hddama/projects/voice-agent-playground'

az rest --method get \
  --url "https://management.azure.com${project}/providers/Microsoft.Authorization/roleAssignments?api-version=2022-04-01&%24filter=principalId%20eq%20'${principal}'"
```

## Canonical end-to-end check

Always finish with:

```bash
python ../12_noauth_mcp/scripts/validate_live.py \
  --mcp-base-url \
  https://voice-agent-noauth-mcp.lemonsky-36682081.westus2.azurecontainerapps.io \
  --portal-base-url \
  https://voice-agent-playground.blackground-c889ecc7.westus2.azurecontainerapps.io \
  --portal-invitation-file .run/access/invitation.local.json \
  --portal-email <evaluation-email>
```
