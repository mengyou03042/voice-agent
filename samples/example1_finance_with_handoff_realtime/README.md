# Finance with Handoff - Realtime

## Overview

This sample owns the standalone Realtime Finance template. Its root
[`agent.json`](agent.json) is the revised round-02 candidate of the business workflow
from the former `example1_finance_with_handoff/agent.realtime.json`, with the explicitly requested
runtime settings: `gpt-realtime`,
`whisper-1`, and `en-IN-Diya:DragonHDLatestNeural`.
It retains the original 13-node, 24-edge business graph and uses 400 ms Semantic VAD.

The [Cascade Luna sample](../example1_finance_with_handoff_cascade/README.md)
is maintained separately. There is no shared base/profile generation step;
edit each runtime's portable definition independently. Portal template IDs and
Agent names remain `finance-example-realtime` and `finance-example-cascade-luna`.

## Spoken responses

Since 2026-10-21 the default is a byte-for-byte copy of
`backups/20261020T040235Z/revised`, chosen because it performed best in
hands-on use. It keeps the business transfer messages on startup, identity,
offer, decision, recap, voicemail, decline and bureau-consent edges.

The previous default, a speech-only cleanup that removed process-only handoff
announcements and static tool-wait responses, remains selectable as
`backups/20261021T064258Z/previous_default`.
These local definition changes do not establish live audio quality or latency.

## Configure and run

Follow the [setup guide](../../docs/01_setup_subscription.md) and
[MCP configuration guide](../../docs/02_mcp_settings.md), then:

```bash
cd samples/example1_finance_with_handoff_realtime
cp .env.example .env
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Set your Foundry Project endpoint in `.env`. The CLI reads the same generated
`../../shared_mcp/config/generated/example1.local.env` as Cascade, targeting
`/mcp/finance-handoff`. Credentials stay in the Project connection, not the
portable Agent definition. Existing ignored `.env` and `.venv` files under the
former sample directory are not moved or deleted; configure the new directory
explicitly rather than copying secrets into a backup.

```bash
.venv/bin/python sample.py publish
.venv/bin/python sample.py check
.venv/bin/python sample.py connect
.venv/bin/python sample.py run \
  --message "Hello, who is calling?" --expect-handoff --expect-mcp
```

Publication uses the SDK raw-body overload and verifies handoff/MCP readback.
The CLI validates text turns over the real Voice WebSocket; it does not play
audio or establish VAD/audio quality. Publication and runtime calls may incur
charges. See the [run guide](../../docs/03_run_samples.md).

## Template versions

In Portal **Load from templates**, choose **Example 1: Finance with Handoff -
Realtime**, then select a **Version**:

| Version | Meaning |
| --- | --- |
| **Default** | Same bytes as `revised`, with `gpt-realtime` and 400 ms Semantic VAD. |
| `backups/20261020T040235Z/original` | Preserved original speech and business definition with current runtime settings. |
| `backups/20261020T040235Z/revised` | Continuation round-02 candidate content with the current runtime settings; the default since 2026-10-21. |
| `backups/20261021T064258Z/previous_default` | The replaced default: original business flow with concise speech. |

The revised version reduces some duplicate waiting narration but still has
missing spoken charges, filtered happy-path output, and incomplete closing.
Waiting/latency and listening acceptance are not established. It was promoted
to the default because it performed best in hands-on use. Loading any version
creates a working copy without changing the default.

Every selectable version uses the current runtime policy. Exact pre-update
bytes remain in each affected version's `agent.source.json`, which is not
discovered as a selectable version. Historical voice results apply to that
earlier runtime, not proof of this configuration's latency or VAD safety.

Fingerprints and source provenance are in the
[backup manifest](backups/20261020T040235Z/manifest.json).

## Conclusion

Realtime and Cascade have independent directories and version histories.
The default is the revised candidate, preferred in hands-on use. The
bounded evaluation findings above still apply; it is not a claim of completed
business disclosure or latency acceptance.
