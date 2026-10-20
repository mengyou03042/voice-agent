# User Playground scaling and availability

## Current answer

The hosted Portal code, IaC and current deployment support multiple replicas.
The accepted live profile is:

```text
minimumReplicas: 2
maximumReplicas: 2
sticky sessions: not required
revision: voice-agent-playground--0000011
```

Both replicas were ready and running during final acceptance. The checked-in
Bicep still permits a higher configurable maximum for future deployments.

The Container App FQDN does not change when replicas are added. Azure Container
Apps load-balances HTTP requests, and a Voice WebSocket remains on the selected
replica for that connection's lifetime.

## What previously assumed one replica

| Feature | Previous implementation | Multi-replica change |
| --- | --- | --- |
| API and publication limits | Sliding windows in one Python process | Removed. The Portal no longer enforces replica-local request or publication quotas. |
| Invitation attempt limit | One process-local counter | Removed. Invitation security relies on the high-entropy secret and expiry; add an ingress/WAF limit if public abuse control is required. |
| Voice concurrency | One process-local active-workspace set and one global count | Removed. The Portal no longer claims a global or per-workspace concurrent-session limit. |
| Voice duration | Timer attached to the selected WebSocket handler | Kept. It is connection-local and therefore safe on every replica. |
| Agent-list pagination | Random browser cursor mapped to a Foundry cursor in one process | Removed. The hosted list returns only the filtered current upstream page with `has_more=false`; it never exposes or retains a cross-workspace cursor. |
| Email ownership | HMAC-signed access cookie and deterministic email Agent-name prefix | Kept. Every replica validates the same cookie with the same Container App secret. |

The features that blocked scaling were therefore guardrails and pagination
bookkeeping, not the Portal UI, Agent publication, managed identity, or Voice
WebSocket transport.

## Remaining state

The following data is intentionally local but does not participate in request
correctness:

- managed-identity token caches;
- application logs;
- temporary process files;
- an open WebSocket and its duration timer.

Session recording is disabled. Agent definitions and versions remain in the
shared Foundry Project, and email ownership is encoded in Agent names
rather than a local database.

## Failure behavior

Multiple replicas remove the single ready-process dependency, but they do not
make an individual Voice connection movable. If its replica stops, that
WebSocket disconnects and the browser must start a new Voice session. Ordinary
HTTP requests can continue on another ready replica.

The current Container Apps environment is not zone redundant. Two replicas in
that environment cover a process or node failure, not every zone or regional
failure.

## Deployment checks

Before declaring a multi-replica release healthy:

1. Use one stable `anonymousCookieKey` across all replicas and revisions.
2. Deploy `minimumReplicas >= 2` and `maximumReplicas >= minimumReplicas`;
   the accepted live deployment uses `2/2`.
3. Sign in as the same email through multiple replicas and verify the same
   Agent namespace is used.
4. Publish and read an Agent while requests are distributed across replicas.
5. Verify the Agent list never returns another email namespace or an
   upstream pagination cursor.
6. Open concurrent Voice sessions and verify each is independently bounded by
   `session_seconds`.
7. Stop one replica and verify HTTP recovery; document the expected disconnect
   for a WebSocket pinned to that replica.

Portal and MCP scale independently. The MCP must use the shared-state setup in
`../12_noauth_mcp/SCALING.md` before its own replica count is raised.
