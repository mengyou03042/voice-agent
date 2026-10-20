# User Playground build, start, stop and rollback

For the Chinese deployment guide, local UI startup, port forwarding and Debug mode,
start with [GUIDE.md](GUIDE.md). The local preview uses the staged generic Portal
entry point; it does not weaken or emulate the hosted invitation policy.

Run commands from:

```text
/home/jimxie/repo/one-speech-service/docs/voice_agent/03_user_playground
```

## Fixed Azure target

```text
Subscription: Speech Services - DEV - Synthesis
Subscription ID: f6e76fc8-e9fc-435f-982a-9007a547ea2d
Resource group: voice-agent-portal-hosting-dev
Region: westus2
OwnerAlias: mengyou
```

Do not deploy this playground to `PrincetonOnlineMeetingsDev`.

## Prerequisites

1. Azure CLI login can access the fixed subscription through ARM.
2. Bicep CLI is installed.
3. `../../../voice-agent` is a complete canonical checkout.
4. The MCP owned by `../12_noauth_mcp` is healthy before Portal exposure.
5. `parameters.local.json` exists, is mode `0600`, and is ignored by Git.
6. Node.js 20 or newer is available for the real browser acceptance script.

Tool bootstrap:

```bash
az version
az bicep version || az bicep install

python3 -m venv .venv
.venv/bin/python -m pip install \
  -r ../../../voice-agent/portal/requirements.txt
```

The current developer has effective subscription actions `["*"]` and a
permanent `Cognitive Services Data Contributor (Preview)` assignment on the
playground Project.

## Foundation

`foundation.bicep` creates or reconciles:

- resource group with `OwnerAlias=mengyou`;
- Foundry account;
- ACR;
- Portal Container Apps environment;
- Log Analytics.

Validate and preview:

```bash
az deployment sub validate \
  --subscription f6e76fc8-e9fc-435f-982a-9007a547ea2d \
  --location westus2 \
  --template-file foundation.bicep

az deployment sub what-if \
  --subscription f6e76fc8-e9fc-435f-982a-9007a547ea2d \
  --location westus2 \
  --template-file foundation.bicep
```

Execute only after the preview contains no unrelated resource:

```bash
az deployment sub create \
  --subscription f6e76fc8-e9fc-435f-982a-9007a547ea2d \
  --location westus2 \
  --name voice-agent-portal-foundation \
  --template-file foundation.bicep
```

Read exact outputs instead of copying names from historical docs:

```bash
az deployment sub show \
  --subscription f6e76fc8-e9fc-435f-982a-9007a547ea2d \
  --name voice-agent-portal-foundation \
  --query properties.outputs

az identity show \
  --subscription f6e76fc8-e9fc-435f-982a-9007a547ea2d \
  --resource-group voice-agent-portal-hosting-dev \
  --name voice-agent-playground-runtime \
  --query '{id:id,clientId:clientId,principalId:principalId}'
```

## Build the Portal image

The [Dockerfile](Dockerfile) pins `pip==26.2` before installing application
dependencies. This covers GHSA-qwm4-qh6w-59xr, GHSA-wf93-45jw-7689,
GHSA-jp4c-xjxw-mgf9 and GHSA-4xh5-x5gv-qwph; their highest required fix
version is `26.2.0` (`26.2` is the same Python package version). The runtime
does not bootstrap package installers, so the image also removes `ensurepip`
and its embedded old pip wheel. The build checks the installed pip version,
the absence of `ensurepip`, dependency consistency and the non-root Portal
startup.

For a security-only release when the checkout has unrelated changes, derive
the remediation image from the currently deployed immutable digest instead
of rebuilding the application from that checkout. Upgrade pip and remove
`ensurepip` as above, retain `USER 10001`, and verify application file hashes
and every other installed package version are unchanged. Deploy only the new
image; do not reapply identity, invitation, signing-key or scaling settings.
After rollout, verify both replicas and wait for the security scanner to
evaluate the new digest. An absent scan result is not proof of remediation.

Create a fresh allowlisted context:

```bash
rm -rf .run/image-context
PORTAL_SOURCE=../../../voice-agent
python3 build_context.py .run/image-context --portal-source "$PORTAL_SOURCE"
```

`build_context.py` fails if the public Portal baseline does not match the
hosting patch. Never bypass that failure.
It stages every enabled catalog entry's configured Agent file and same-named
nested versions, without copying neighboring backup files. It normalizes the
allowlisted files to `0644` after applying the adapter, including under
`umask 077`; the context root remains `0700`. This is required by the image's
non-root startup check. Fix staging and create a fresh context if that check
fails; do not modify an already-staged release.

Inspect the staged input before upload:

```bash
find .run/image-context -type f | sort
test ! -e .run/image-context/portal/.env
test ! -e .run/image-context/portal/.venv
PYTHONPATH=.run/image-context/portal \
  .venv/bin/python -m py_compile \
  .run/image-context/portal/*.py
```

Build:

```bash
az acr build \
  --subscription f6e76fc8-e9fc-435f-982a-9007a547ea2d \
  --registry vaportall3hddama \
  --file .run/image-context/portal/hosting/Dockerfile \
  --image voice-agent-playground:<unique-tag> \
  .run/image-context
```

Record the immutable digest in `parameters.local.json`.

Current active image:

```text
vaportall3hddama.azurecr.io/voice-agent-playground@sha256:932691d8bc193bbd762c4b832cbd91b7d7a3290fc684fc01f57cfa90ab9f971f
```

For code-only releases with no IaC change, prefer updating only the existing
Portal image rather than reapplying the Project, identity and role assignments:

```bash
az containerapp update \
  --subscription f6e76fc8-e9fc-435f-982a-9007a547ea2d \
  --resource-group voice-agent-portal-hosting-dev \
  --name voice-agent-playground \
  --image 'vaportall3hddama.azurecr.io/voice-agent-playground@sha256:<approved-image-digest>' \
  --query '{latest:properties.latestRevisionName,ready:properties.latestReadyRevisionName}'
```

Keep the same digest in the ignored deployment parameters. Require the new
revision to become ready, retain `min=2`/`max=2`, and run the browser acceptance
below. This path must not change the signing key, invitation or runtime identity.

The image must include `portal/playground_usage.py`. After every image-only
release, check recent telemetry from the workspace root:

```bash
python docs/voice_agent/03_user_playground/scripts/usage_stats.py --hours 1
```

Require a fresh `last_heartbeat_utc`; a new installation may legitimately report
`coverage_status=partial`. Missing or stale collection is not a successful
telemetry release. Mark all acceptance requests with `X-MS-Synthetic-Source`
and check `--traffic synthetic` separately. See [TELEMETRY.md](TELEMETRY.md)
for the metric definitions and privacy boundary.

## Parameters

Copy `parameters.example.json` to `parameters.local.json`.

Required values include:

- Foundation outputs.
- Immutable Portal image digest.
- Stable random `anonymousCookieKey`.
- SHA-256 `invitationCodeHash` of the shared login token.
- Positive Unix timestamp `invitationExpiresAt`.
- `accessCookieDays` between 1 and 400; the default is 365.
- `mcpBaseUrl`:
  `https://voice-agent-noauth-mcp.lemonsky-36682081.westus2.azurecontainerapps.io`.
- `exposePortalIngress`.
- `minimumReplicas`.
- `maximumReplicas`.

`anonymousCookieKey` must remain stable across revisions if existing browser
workspaces should survive.

Generate it without printing:

```bash
python - <<'PY'
import json, secrets
from pathlib import Path

path = Path("parameters.local.json")
data = json.loads(path.read_text())
data["parameters"]["anonymousCookieKey"] = {
    "value": secrets.token_urlsafe(48)
}
path.write_text(json.dumps(data, indent=2) + "\n")
path.chmod(0o600)
PY
```

Create or rotate the ignored shared token file without printing the token:

```bash
python issue_invitation.py .run/access/invitation.local.json --days 30
python scripts/prepare_release.py
```

The first command creates the file with mode `0600`; the second reads only its
hash and expiry into ignored deployment parameters. Deliver the same raw token
to each trusted user through an approved secret channel. Do not put the token
in Git, deployment output, command-line arguments, URLs or application logs.

## Validate Portal IaC

```bash
mkdir -p .run
az bicep lint --file main.bicep
az bicep build --file main.bicep --outfile .run/main.arm.json

az deployment group validate \
  --subscription f6e76fc8-e9fc-435f-982a-9007a547ea2d \
  --resource-group voice-agent-portal-hosting-dev \
  --template-file main.bicep \
  --parameters @parameters.local.json

az deployment group what-if \
  --subscription f6e76fc8-e9fc-435f-982a-9007a547ea2d \
  --resource-group voice-agent-portal-hosting-dev \
  --template-file main.bicep \
  --parameters @parameters.local.json
```

The deployment may touch only the Portal app, Project, runtime identity and
their scoped roles. MCP resources belong to `12_noauth_mcp`.

## Start order

### 1. Start and validate MCP

Follow `../12_noauth_mcp/README.md`. Require:

```text
https://voice-agent-noauth-mcp.lemonsky-36682081.westus2.azurecontainerapps.io/healthz -> 200
```

Run the MCP-only validator before exposing Portal:

```bash
python ../12_noauth_mcp/scripts/validate_live.py \
  --mcp-base-url \
  https://voice-agent-noauth-mcp.lemonsky-36682081.westus2.azurecontainerapps.io
```

### 2. Start Portal

Set:

```json
"exposePortalIngress": {"value": true},
"minimumReplicas": {"value": 2},
"maximumReplicas": {"value": 5}
```

Deploy:

```bash
az deployment group create \
  --subscription f6e76fc8-e9fc-435f-982a-9007a547ea2d \
  --resource-group voice-agent-portal-hosting-dev \
  --name voice-agent-playground-public \
  --template-file main.bicep \
  --parameters @parameters.local.json
```

This deployment enables `VOICE_PLAYGROUND_AUTH_MODE=invite`. A successful
health check does not prove invitation enforcement. Require:

- browser navigation without an access cookie -> custom `/login` page;
- API request without an access cookie -> 401 without a Basic challenge;
- valid shared token and syntactically valid email -> secure
  `__Host-voice_playground_access` cookie;
- wrong or expired shared token -> custom login error with no cookie;
- the same email from another authenticated browser -> the same Agent namespace;
- the same shared token with a different email -> a different Agent namespace;
- a signed-in browser cannot directly read another email namespace and receives 404;
- HTTP APIs and Voice WebSocket reject requests without the access cookie;
- shared tokens and email addresses are absent from application logs.

This flow does not verify inbox ownership. Any trusted user who has the shared
token can deliberately enter another known email and establish that namespace.
Do not use this admission model where users are mutually untrusted.

The first custom-login deployment invalidates the previous Basic-auth cookie.
Users must sign in once with the shared token and their email. Agents created under old
random workspace cookies remain in Foundry but are not automatically assigned
to an email; do not delete them as part of the authentication rollout.

Run the validator with the ignored shared-token file. It reads the token from
the file instead of placing it in a URL or command line:

```bash
PORTAL=https://voice-agent-playground.blackground-c889ecc7.westus2.azurecontainerapps.io

test "$(curl -sS -o /dev/null -w '%{http_code}' "$PORTAL/config")" = 401
.venv/bin/python scripts/accept_live.py \
  --base-url "$PORTAL" \
  --invitation-file .run/access/invitation.local.json \
  --email acceptance@example.com \
  --output .run/live-acceptance.json

VOICE_PLAYGROUND_EMAIL=acceptance@example.com \
  node scripts/accept_browser.mjs

unset PORTAL
```

Wrong-token rejection, cookie tampering and stable distinct email namespaces
remain covered by `tests/test_playground.py`; repeat the live smoke after any
shared-token rotation or login-policy change.

Verify:

```bash
curl --fail \
  https://voice-agent-playground.blackground-c889ecc7.westus2.azurecontainerapps.io/healthz
```

### 3. Run canonical integration validation

```bash
python ../12_noauth_mcp/scripts/validate_live.py \
  --mcp-base-url \
  https://voice-agent-noauth-mcp.lemonsky-36682081.westus2.azurecontainerapps.io \
  --portal-base-url \
  https://voice-agent-playground.blackground-c889ecc7.westus2.azurecontainerapps.io \
  --portal-invitation-file .run/access/invitation.local.json \
  --portal-email <evaluation-email>
```

Do not declare success from `/healthz` alone.

The current Portal release is `voice-agent-playground--0000033`, image digest
`sha256:4f56be75...`, built by ACR run `cc1u` on 2026-10-21 from this repository
(`build_context.py`) with 35 cards. Examples 5-34 run on the `mock-tool-call` route of
the shared no-auth MCP service. In **Load from templates**, each card marks **Mock
tools** and the systems it uses, and its **Tools** choice can open **Connect my tools**
right after loading. The Editor shows a mock-tools banner, and **Connect my tools** binds
each business system to the user's own public HTTPS MCP server. Work IQ is listed but
cannot be connected. `/guide/real-tools` and `/guide/logic-apps-mcp` are rendered as
HTML. It replaced revision `0000032` (`sha256:e9ed2285...`), the rollback image. Only
the image changed: environment variable names were compared before and after, and the
revision is Healthy with two replicas and 100% traffic. The hosted regression suite ran
47 tests: 46 passed and the opt-in Kusto check was skipped.

The earlier release was `voice-agent-playground--0000026`, image digest
`sha256:932691d8...`, built by ACR run `cc13` from the Portal working-copy snapshot
based on commit `8c41ae3` on 2026-10-20. Both replicas are ready with zero restarts
and 100% traffic. The before/after resource comparison verified that only the
image changed; both existing signing/admission secret fingerprints also matched.

The hosted regression suite ran 46 tests: 45 passed and one opt-in fixture-only
Kusto check was skipped. Staging now includes all eight configured cards and
17 versions, and a regression covers patch output permissions under `umask 077`.
The first build, `cc12`, correctly stopped at the non-root startup guard when
patched files were private to the staging user. The staging fix normalizes the
allowlisted files after patching; a fresh, byte-identical package passed `cc13`.
No failed image was deployed and no startup guard was bypassed.

All 17 versions were actually published and read back with matching selected
instructions. The eight default versions completed real Voice sessions, each
returning 163200-376800 decoded audio bytes with no protocol errors. The nine
backups were published/read back, but were not separately voice-probed. Acceptance
uses text input and checks real returned Voice audio; it is not a microphone
recording or human listening test. The dedicated synthetic namespace retains
the 17 acceptance Agents; no Azure resources were deleted.

Live browser acceptance verified 11 exact asset hashes, default-hidden Debug
metrics, all eight cards, the 17-version catalog, desktop/mobile Editor backup
loading and runtime Agent selection. It checked the backup previews on the
Templates page and reported no page errors.

Fresh telemetry reported `coverage_status=observed`, 17 synthetic publications,
zero failed publications and a heartbeat 38 seconds old at 01:54:35 UTC.
The protected API still returns 401 without a cookie.
Revision-filtered logs through 01:57:58 UTC contained 206 records and no
traceback, panic, fatal or Voice bridge error. A fresh session using the same
email read its acceptance Agent with HTTP 200; a different email received 404.

Release evidence is retained in the ignored, private
`.run/template-versions-20261020T014128Z/` directory. It contains the frozen
package and manifest, ACR build results, live/browser acceptance reports,
telemetry and private before/after configuration and secret fingerprints.
Do not upload the private snapshots. The ignored parameters file was updated
only at `parameters.image.value`, retaining mode `0600`.

The previous release was `voice-agent-playground--0000025`, image digest
`sha256:9b49e86d...`, built by ACR run `cc11` from Portal commit `237f4ee` on
2026-10-19. Its additional synthetic playback check covered interleaved item
scheduling, immediate first-item playback and interruption. The current release
does not claim to repeat that separate check; its evidence remains in
`.run/release-evidence-20261019-237f4ee/`.

The earlier pricing/runtime UI release was `voice-agent-playground--0000022`,
image digest `sha256:a0056351...`. Its acceptance covered the conservative
Whisper allowance, Elevator total and equal runtime columns; those browser
checks also passed for the current release. Node completion, re-entry and
interrupted-session behavior remain covered by the Studio fixture regressions.

The existing-Agent action was accepted on revision `voice-agent-playground--0000021` with image
digest `sha256:e9cef3d7...`, two ready replicas, the single-step login flow,
usage telemetry and the Editor-first UI. Browser acceptance checks the complete blue latency
ranges, cents-per-minute costs, toolbar layout and graph visibility at widths
390 and 1440.
Editor/voice acceptance evidence is recorded in `ACCEPTANCE_2026-10-16.md`;
the telemetry release's exact live counts are recorded in [TELEMETRY.md](TELEMETRY.md).

## Stop Portal

Stopping or revision deactivation disconnects active Voice WebSockets. Announce
a maintenance window and stop admitting new users before continuing.

Set:

```json
"exposePortalIngress": {"value": false},
"minimumReplicas": {"value": 0}
```

Deploy the same `main.bicep`, then disable ingress and deactivate any remaining
active revisions if Azure has not drained them.

Stopping Portal does not stop MCP. Stop MCP through
`12_noauth_mcp/infra/main.bicep`.

After disabling ingress, deactivate old revisions and verify they are drained:

```bash
for revision in $(az containerapp revision list \
  --subscription f6e76fc8-e9fc-435f-982a-9007a547ea2d \
  --resource-group voice-agent-portal-hosting-dev \
  --name voice-agent-playground \
  --query '[?properties.active].name' -o tsv); do
  az containerapp revision deactivate \
    --subscription f6e76fc8-e9fc-435f-982a-9007a547ea2d \
    --resource-group voice-agent-portal-hosting-dev \
    --name voice-agent-playground \
    --revision "$revision"
done
```

Require zero active revisions and no `Running` replicas.

## Replica rule

Serve with at least two ready replicas:

```json
"minimumReplicas": {"value": 2},
"maximumReplicas": {"value": 2}
```

The hosted adapter no longer contains process-local request/publication
limits, active-session counters or pagination cursor mappings. The remaining
access cookie and deterministic email Agent namespace are stateless across replicas. See
`SCALING.md` for the expected WebSocket disconnect if one selected replica
fails.

## Rollback

Current image (`revision 0000026`, Template versions):

```text
vaportall3hddama.azurecr.io/voice-agent-playground@sha256:932691d8bc193bbd762c4b832cbd91b7d7a3290fc684fc01f57cfa90ab9f971f
```

Preferred rollback is revision `0000025`, retaining the preceding Portal
playback/UI fixes and the pip remediation:

```bash
az containerapp update \
  --subscription f6e76fc8-e9fc-435f-982a-9007a547ea2d \
  --resource-group voice-agent-portal-hosting-dev \
  --name voice-agent-playground \
  --image 'vaportall3hddama.azurecr.io/voice-agent-playground@sha256:9b49e86d4191b2772842cf54a0a589f1cd6151e2a79ac10d4d2b4a6369567daf' \
  --query '{latest:properties.latestRevisionName,ready:properties.latestReadyRevisionName}'
```

Only use rollback when required; it removes Template version selection and the
three newly packaged sample cards. Recheck two ready replicas, login, health and traffic, and synchronize
the private image parameter without changing invitation or signing keys.

Previous image (`revision 0000024`, pip remediation for
[IcM 887686614](https://portal.microsofticm.com/imp/v5/incidents/details/887686614/summary)):

```text
sha256:f8ef8e561c20fce66243b17d9450d1662f968b402a32f3fa4f02f8a1f8754ffc
```

This image was built by ACR run `cc10` on 2026-10-18 from the exact revision
`0000023` image. Only pip and the unused `ensurepip` bootstrap package changed;
application file hashes and all non-pip installed versions were checked
against the base image. At acceptance, both replicas were ready with 100% traffic, unchanged
runtime configuration and `min=2`/`max=2`.

Validation passed: 44 regression tests (one opt-in Kusto test skipped),
unauthenticated rejection, invitation sign-in, authenticated config and four
Templates, matching hashes for all eight served application assets, and live
publication/readback/MCP/voice responses for every Template. Telemetry had a
fresh heartbeat with `coverage_status=observed`. In-container checks on both
replicas confirmed pip `26.2`, absent `ensurepip`, and runtime UID `10001`.
The installed version was also checked against all four advisory ranges,
including the equivalent `26.2.0` fix threshold. Both replicas use the same
immutable image and reported ready with zero restarts.

The original MDVM assessment reported pip `25.0.1` with a required fixed
version of `26.2.0`. On 2026-10-18 the new digest did not yet have an assessment
visible in Azure Resource Graph. That absence is not a clean scan. Scanner
confirmation and automatic IcM closure remain pending; the assessment guidance
allows up to 24 hours for recommendations to update. The IcM portal required
an interactive Entra sign-in, so no incident comment or state change was made.

Follow-up checks also called the individual recommendation ARM endpoint
directly: the original digest returned its known `Unhealthy` pip assessment,
while the corrected digest returned `AssessmentNotFound` ("does not exist or
not calculated yet"). This rules out treating Resource Graph absence alone as
proof. Container registry vulnerability assessment is enabled on the existing
Defender plans; no security settings were changed. Microsoft documents
[new-image scanning as asynchronous, typically within a few hours](https://learn.microsoft.com/en-us/azure/defender-for-cloud/agentless-vulnerability-assessment-azure#scanning-behavior-and-timing).
The legacy subassessment API returned `SubAssessmentsDeprecated`; use
individual recommendations for follow-up rather than the old API.

Earlier images below contain pip `25.0.1` and do not satisfy this security
fix. Do not restore one unchanged for routine rollback: apply the same pip
remediation to the selected application image first.

Previous application image (`revision 0000023`, before pip remediation):

```text
sha256:2868d331f62ff1acefc55a6dd235a0e8e785c6305fa14db370d3f14a39a92ee1
```

Previous pricing/runtime UI image (`revision 0000022`):

```text
sha256:a005635147f2adc186092a387b991b12f7ab938f3e372503719c81e0e40b3d59
```

Previous accepted existing-Agent action image (`revision 0000021`):

```text
sha256:e9cef3d7ed745185f70474abab004eb0d7f26ed849edcfd1b7a02f9b83ccff47
```

Previous accepted Editor/telemetry image (`revision 0000019`):

```text
sha256:8ca1e029c7caa9b883e8d8746cdfb888d8d9876472e3097deb4a470b0cb041e4
```

Previous accepted telemetry image (`revision 0000018`):

```text
sha256:65abc1e96c22eb2032cd351df7d097e35abba907d01f0a8955c6172f43e77a29
```

Previous accepted Editor image before telemetry (`revision 0000017`):

```text
sha256:f85943639791ec0186fccaf83367a5904aca27778ee4aaee98932de721a2393e
```

Previous accepted custom-login image before the Editor update (`revision 0000015`):

```text
sha256:21e983ec4e741190b21d9fc5713ac31f6a22bdc57b5f7b1dde09fa87e7b618d5
```

Set the complete ACR digest reference in `parameters.local.json`, run
`validate`/`what-if`, and redeploy. Do not use floating tags.

Rolling back before revision `0000018` removes usage emission. The reporting
command must then show stale/missing coverage rather than an apparent traffic
drop; retain the existing log history.

If the failure is only a Template/MCP binding issue, keep the Portal image and
restore the previous MCP base URL/profile revision instead of rolling back
unrelated Portal code.

## Cookie-signing-key rotation

Changing `anonymousCookieKey` invalidates every existing access cookie. Users
must sign in again, but the deterministic email namespace does not change, so
they regain access to their existing Agents after authenticating with the
shared token and the same email.

Rotate only in a maintenance window:

1. Stop new admission.
2. Warn users that they must sign in again.
3. Generate a new key without printing it.
4. Deploy one revision.
5. Deactivate old revisions so one signing key is authoritative.
6. Run email-token, namespace-isolation and canonical live validation.
