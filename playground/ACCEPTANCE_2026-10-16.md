# User Playground multi-replica live acceptance - 2026-10-16

## Latest pricing/runtime UI acceptance: revision 0000022

```text
Portal revision: voice-agent-playground--0000022
Image: vaportall3hddama.azurecr.io/voice-agent-playground@sha256:a005635147f2adc186092a387b991b12f7ab938f3e372503719c81e0e40b3d59
Build: ccx
Ready replicas: 2
Traffic: 100%
Scale: min=2, max=2
```

- Speech and LLM rates were independently reviewed, then cross-checked against
  all 43 West US 2 Voice Live consumption meters. The full reference is
  [the conservative pricing audit](../cost/04_node_model_cost_quick_reference.md).
- The image snapshot exactly matches all 14 audited model rows. Coverage
  includes 12 STT options, 46 voices and over 1,000 compatible combinations.
  Unverified auxiliary transcription reserves 2 cents per input minute, not
  a falsely confirmed standalone API tariff. Full context is budgeted on
  every model request, with no cache discount.
- Runtime defaults to equal graph/debug and conversation widths. Manual resize
  remains available, with Home/double-click returning to equal widths.
- Completed visits show a large green COMPLETED badge/checkmark. Re-entry
  restores LIVE. Manual cancellation and abnormal closure show STOPPED; a
  normal server closure completes the final visit. A completed visit does not
  claim success for every business operation.
- Validation passed 49 focused unit tests, 23 Python-backed Portal browser
  tests, 63 Studio/privacy browser tests, and 32 hosted policy/packaging tests.
- Real authenticated Chromium verified all eight deployed asset hashes against
  the immutable build input, Whisper's 2-cent allowance, the 485.72-cent
  Elevator working-copy total, full blue latency ranges, phone/desktop layout,
  MCP readiness and 50/50 runtime widths at 1440 and 1920. No page errors occurred.

Evidence is retained in `.run/browser-acceptance.json` and the hosted Editor
screenshots. Runtime completion transitions used the synthetic WebSocket fixture;
this UI follow-up did not publish real Agents or rerun paid Voice conversations.
Earlier sections below retain their original revision-specific evidence.

## Scope

This is evidence for the invitation-protected multi-replica deployment, not a
fixture or local mock.

```text
Portal:
https://voice-agent-playground.blackground-c889ecc7.westus2.azurecontainerapps.io

Portal revision:
voice-agent-playground--0000011

Portal image:
vaportall3hddama.azurecr.io/voice-agent-playground@sha256:da5d5d96052ad4eaae281f76cbd70d3f99615e88329fb512910b98fa95aee151

Portal scale:
minReplicas: 2
maxReplicas: 2
ready replicas: 2

MCP:
https://voice-agent-noauth-mcp.lemonsky-36682081.westus2.azurecontainerapps.io

MCP revision:
voice-agent-noauth-mcp--0000004

MCP image:
vaportall3hddama.azurecr.io/voice-agent-noauth-mcp@sha256:88cf811adcf862883473d729cacbb6d8d0d116825726b46acca095863a8cdd57

MCP scale:
minReplicas: 3
maxReplicas: 3
ready replicas: 3

Shared state:
voice-agent-noauth-state-l3hddama
Standard C0 Azure Cache for Redis
TLS 1.2; non-TLS disabled; noeviction
```

Both Container Apps had one active healthy revision, 100% traffic on the
revision above and no sticky-session configuration.

## Build and deployment

- Portal policy tests: **29 passed**.
- Shared MCP component tests: **16 passed**.
- No-auth MCP image tests: **12 passed**.
- All **13** enabled MCP pack/route self-checks passed during the image build.
- Portal and MCP Bicep build/lint and ARM validation passed.
- Portal staging contained **83** allowlisted files.
- MCP staging contained **148** allowlisted files and no `.env`,
  `.run-*`, `*.local.json`, runtime state or secret parameter file.
- The first Redis-backed MCP revision failed readiness because an OTP helper
  unnecessarily touched a default local state directory. The old revision
  remained live. The helper was fixed to skip local state when Redis is
  configured, tested, rebuilt and redeployed before scaling.
- The failed and superseded revisions were deactivated before final
  acceptance.

## Invitation acceptance

- Unauthenticated `/config`: HTTP 401 without a `WWW-Authenticate` header.
- The custom `/login` form accepted the shared token and evaluation email,
  returned HTTP 303 and set the secure
  `__Host-voice_playground_access` cookie.
- The normalized email deterministically selected the Agent namespace; the
  invite flow no longer uses the random `voice_playground_workspace` cookie.
- A separately signed cross-check email namespace received HTTP 404 for every
  Agent published by the owner namespace.
- The ignored `0600` invitation file expires on
  **2026-10-23T09:01:49Z**. The raw token was not printed or placed in a
  deployment parameter.

## MCP and shared-state acceptance

- `/healthz` reported all 13 enabled packs.
- Every enabled route completed unauthenticated `initialize` and
  `tools/list`, with every required tool present.
- Startup logs reported the Front Desk Redis store and all pack routes.
- An Elevator workflow was created while revision `0000003` had one replica.
- Scaling to three created revision `0000004`; that new revision read the same
  workflow state successfully from Redis.
- All three final MCP replica logs were free of traceback, fatal, panic,
  unhandled and permission-error markers.

## Templates, publication and Voice

Each Template:

1. loaded from the hosted catalog;
2. materialized with `store=false`;
3. contained direct public MCP URL(s) and no connection ID, bearer, headers or
   credential fields;
4. passed its real unauthenticated MCP probe;
5. published a version to the hosted Foundry Project;
6. passed REST readback and Agent-list visibility;
7. opened a real Voice WebSocket that reached `session.created`,
   `response.created` and `response.done`, emitted audio and returned no error.

| Template | Model | MCP tools | Published Agent | Audio events | Audio bytes | Elapsed |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| Finance Handoff - Realtime | `gpt-realtime-2.1` | 18 | `pg-35b889e628aa4e4cd1dd568b-local-only-e2e-1-20261016-144628` | 9 | 177,600 | 4.648 s |
| Finance Handoff - Cascade Luna | `gpt-5.6-luna` | 18 | `pg-35b889e628aa4e4cd1dd568b-local-only-e2e-2-20261016-144628` | 8 | 165,600 | 3.901 s |
| Finance OTP and Officer Search | `gpt-realtime` | 8 | `pg-35b889e628aa4e4cd1dd568b-local-only-e2e-3-20261016-144628` | 14 | 312,000 | 4.846 s |
| Elevator Service | `gpt-realtime` | 8 | `pg-35b889e628aa4e4cd1dd568b-local-only-e2e-4-20261016-144628` | 9 | 175,200 | 3.848 s |

The validators retain published Agents as bounded acceptance evidence; they do
not delete Azure resources.

## Final operational checks

- MCP `/healthz`: HTTP 200, `status=ok`.
- Portal `/healthz`: HTTP 200, `status=ok`.
- MCP replica count: three running, started and ready.
- Portal replica count: two running, started and ready.
- Every live replica log passed the fatal-error scan.
- Redis reported `Succeeded`, TLS port 6380, primary/replica instances and
  `maxmemory-policy=noeviction`.

## Remaining limits

- MCP is intentionally public no-auth. Portal invitation access does not
  authenticate direct MCP callers.
- The two Container Apps environments and Redis deployment are not zone
  redundant; this rollout covers process/node failure, not zone or region
  failure.
- A Voice WebSocket stays on its selected Portal replica. Failure of that
  replica disconnects the active call; a new call can use the surviving
  replica.
- Interview still uses one fixed candidate namespace for unauthenticated
  callers.
- The acceptance exercised one response per published Agent, not every branch
  in every fictional workflow.

## Login follow-up: revision 0000015

The active Portal image is now:

```text
vaportall3hddama.azurecr.io/voice-agent-playground@sha256:21e983ec4e741190b21d9fc5713ac31f6a22bdc57b5f7b1dde09fa87e7b618d5
```

- The earlier native-form rejection came from `Origin: null` under
  `Referrer-Policy: no-referrer`. The hosted policy accepts that origin only
  with `Sec-Fetch-Site: same-origin`; untrusted-origin cases still return 403.
- Token and email now appear in one JavaScript-free form, with a
  `mailto:yiwenrong@microsoft.com` contact link.
- All 28 playground component tests and three invitation-issuance tests passed.
- The image build and ARM validation succeeded. The code-only release updated
  the existing Portal image without redeploying the Project or identity.
  Effective template settings, secret references, ingress, identity and
  `min=2`/`max=2` were verified unchanged.
- Revision `voice-agent-playground--0000015` receives 100% of traffic and has
  two running, started, ready replicas.
- Real Chromium verified both fields and the contact link at widths 390 and
  1440, submitted the native form successfully (303), and reached Studio and
  Templates (200). The secure access cookie, four Template cards, public MCP
  readiness and Handoff Graph all passed; there were no browser errors.
- Live checks retained anonymous `/config` rejection (401), invalid-token
  rejection after same-origin validation (401), cross-site login rejection
  (403), and Portal/MCP health (200).

This follow-up validates login and UI behavior only. It did not publish new
Agents or rerun Voice sessions; the full Voice evidence above belongs to the
earlier acceptance.

## Editor UI follow-up: revision 0000017

The Editor update uses image:

```text
vaportall3hddama.azurecr.io/voice-agent-playground@sha256:f85943639791ec0186fccaf83367a5904aca27778ee4aaee98932de721a2393e
```

- The root opens `/editor/`; old `/handoff/` links redirect with query
  parameters preserved. AgentRuntime and Agent deep links remain available.
- The hosted fixed sidebar is hidden. Create blank and Load from templates
  share the top row with the green, animated-border Try it now action.
  Validation remains automatic; Export and Format view are on the canvas.
- Costs use US cents per minute. Both latency endpoints use the same blue
  text size without wrapping; the dropdown contains only a short disclaimer.
- A visual check caught graph displacement after resizing. The final version
  preserves graph center and zoom as canvas dimensions change.
- Local verification passed 15 browser tests, 38 graph unit tests, five Editor
  route/contracts tests, 31 generic Portal tests and 28 hosted policy tests.
  Three targeted Studio browser regressions also passed.
- Real Chromium passed custom login, the Editor landing page, hidden sidebar,
  blank creation, Template loading, full blue ranges, costs, desktop/mobile
  toolbars, resize visibility, AgentRuntime navigation and public MCP readiness.
  Widths 390 and 1440 were checked with no browser errors.
- ARM confirmed revision `0000017` ready with two started, ready replicas,
  100% traffic and unchanged `min=2`/`max=2`. Only the Portal image was updated.

Browser evidence is in the ignored `.run/browser-acceptance.json` and
`.run/hosted-editor-1440.png` / `.run/hosted-editor-390.png` files. This UI
follow-up did not publish real Agents or rerun Voice sessions; local publication
success/failure checks used the existing synthetic Foundry fixture.

## Existing-Agent Try it now follow-up: revisions 0000020 and 0000021

The action first shipped in revision `0000020`, using image
`sha256:6f147d05cdaac0ae74a52291b422aa6886b600d4cba0f45700fcf5917cb3a717`.
It was also verified after the concurrent cost-display release became current:
revision `0000021`, image
`sha256:e9cef3d7ed745185f70474abab004eb0d7f26ed849edcfd1b7a02f9b83ccff47`.
The later image and its private deployment parameters were preserved.
A final read-only check found the subsequent revision `0000022` healthy with
two replicas and 100% traffic; its served Editor and Runtime assets retained
the verified direct-run and one-shot startup implementation.

- An unchanged published Agent loaded from the sidebar can use **Try it now**.
  It opens that Agent in Runtime and starts a voice session without publishing
  another version. Edited existing Agents publish and verify a release first.
- The start request is same-tab and one-shot. Reloads and ordinary shared URLs
  remain manual; an unavailable request never starts a different Agent.
  New working copies keep their publication and explicit-connect behavior.
- Seven initial targeted browser regressions, five Editor route/contract tests
  and 32 hosted policy/adapter tests passed. The five launch-specific browser
  regressions were repeated against the final shared source and also passed.
- Real Chromium verified both revisions: load the existing published Agent
  from the sidebar, enter Runtime with the correct selection, reach `listening`,
  open exactly one Voice WebSocket and request the synthetic microphone once.
  The Editor made zero version-publication requests; API readback confirmed the
  version was unchanged. Reload opened no new connection or microphone.
- Each isolated run seeded its acceptance namespace through the normal Finance
  Template workflow. Both setup Agents were deleted through the authenticated
  Foundry API, and readback returned 404. No Portal DELETE route was added.
- The general cloud browser smoke passed on revision `0000021`, including login,
  redirects, all eight deployed asset hashes, desktop/mobile layout and public
  MCP readiness. Both browser checks reported zero page errors.
- The Portal remained healthy with two replicas, 100% traffic and unchanged
  `min=2`/`max=2`. This change updated only the Portal image, not login,
  invitation, runtime identity or MCP resources.

Scoped live evidence is in the ignored `.run/existing-agent-run-30d8dc12.json`
and `.run/existing-agent-runtime-30d8dc12.png` files. The general browser report
is `.run/browser-acceptance.json`.
