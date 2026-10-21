# Finance with Handoff - Cascade Luna

## Overview

This sample owns the standalone Cascade Finance template. Its root
[`agent.json`](agent.json) is the revised round-14 candidate of the business workflow
from the former `example1_finance_with_handoff/agent.cascade-luna.json`: `gpt-5.6-luna`,
`azure-speech`, and `en-IN-Diya:DragonHDLatestNeural`.
It retains the original 13-node, 24-edge graph and existing smart end-of-turn
configuration. Semantic VAD silence is now explicitly 400 ms; the Cascade model
is unchanged.

The [Realtime sample](../example1_finance_with_handoff_realtime/README.md)
is maintained separately. There is no shared base/profile generation step.
The Portal template ID and Agent name remain `finance-example-cascade-luna`;
selecting a backup here cannot select a Realtime definition.

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
cd samples/example1_finance_with_handoff_cascade
cp .env.example .env
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Set your Foundry Project endpoint in `.env`. Both Finance handoff runtimes use
`../../shared_mcp/config/generated/example1.local.env` and the
`/mcp/finance-handoff` route. Portable definitions contain no endpoint,
connection credential or test Agent name. Existing ignored local files under
the former combined directory are left untouched.

```bash
.venv/bin/python sample.py publish
.venv/bin/python sample.py check
.venv/bin/python sample.py connect
.venv/bin/python sample.py run \
  --message "Hello, who is calling?" --expect-handoff --expect-mcp
```

The SDK publisher verifies the exact graph and MCP readback. The CLI uses
real Voice WebSocket text turns; it does not establish audible latency,
listening quality or VAD safety. Cloud calls may incur charges. See the
[run guide](../../docs/03_run_samples.md).

## Template versions

In Portal **Load from templates**, choose **Example 1: Finance with Handoff -
Cascade Luna**, then choose **Version**:

| Version | Meaning |
| --- | --- |
| **Default** | Same bytes as `revised`, with the existing Cascade model and 400 ms Semantic VAD. |
| `backups/20261020T040235Z/original` | Preserved original speech and business definition with current runtime settings. |
| `backups/20261020T040235Z/revised` | Preserved round-14 candidate content with current runtime settings; the default since 2026-10-21. |
| `backups/20261021T064258Z/previous_default` | The replaced default: original business flow with concise speech. |

The revised candidate has observed content/business improvements, including
actual charges, consent and recap, but retains unresolved handoff preparation
waits and long gaps. Later faster runs do not erase the preserved slow cases.
It was promoted to the default because it performed best in hands-on use; it
is not a latency-approved replacement. Loading a version does not rewrite the
default or automatically deploy an Agent.

All selectable versions use 400 ms Semantic VAD without changing `gpt-5.6-luna`.
Pre-update source bytes are retained as `agent.source.json` and the previous
manifest is archived. Historical results are not new validation of the
400 ms configuration.

See the [backup manifest](backups/20261020T040235Z/manifest.json) for exact
file fingerprints and provenance.

## Conclusion

Cascade has its own authored source and backups. The default is the revised
candidate, preferred in hands-on use, without claiming that the unresolved
waiting behavior has passed acceptance.
