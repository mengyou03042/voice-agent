# Customer Support: shared-prompt backup v1

## Scope

This is a backup-only candidate derived from the frozen
[revised definition](../revised/agent.json), not the independently edited live
template. The [original](../original/agent.json) and revised snapshots are unchanged.

- [Shared prompt](shared_prompt.md): personality, environment, tone, response
  style, spoken delivery, goal, and global truth/privacy/capability boundaries.
  It contains no node IDs, field-collection sequence, route conditions, or
  termination procedure.
- [Node prompts](node_prompts.md): the implicit entrypoint and each node's own
  objective, actions, routes, and closing behavior.
- [Agent definition](agent.json): the portable authored candidate. Shared text
  appears once in `definition.instructions`; business nodes contain only local
  instructions and set `inherit_from_base_instructions: true`.

The implicit entrypoint's policy is stored in its outgoing edge description,
not in the shared prompt. The terminal node opts out of inheritance so its
tool-only output cannot acquire persona dialogue or another farewell.

## Runtime and behavior

The existing sample and Portal publishers expand instruction inheritance before
publication. Do not send an unexpanded inheritance flag directly to a service
version that rejects it, and do not assume local node instructions replace the
need to materialize the shared policy. No new service field or loader is added.

The candidate keeps the revised model, voice, greeting, audio/VAD, storage,
tools, tool choices, node/edge IDs, transfer limits, fixed edge messages, and
target-response settings. Node and edge descriptions are aligned with their
local duties. In particular, a completed answer does not force an unsolicited
summary; a real final question must be answered before ending.

The design follows the referenced [Front Desk fluency guidance](../../../../../../docs/voice_agent/flunecy_improvment/02_frontdesk_fluency_first_shared_prompt.md):
respond to meaningful caller content, preserve exact evidence, avoid invented
emotion, and leave business steps to their owner. A direct answer counts as a
response; there is no mandatory acknowledgement phrase or rigid word count.

## Verification and limits

The snapshot manifest records provenance and SHA-256 hashes. Offline checks
cover prompt-source equality, shared/local separation, inheritance expansion,
graph/tool/audio preservation, matching route descriptions, and frozen-source
integrity. These are structural checks, not a live fluency or latency result.

Before promotion, compare whole conversations with the revised baseline under
identical model, voice, VAD, tools, and caller turns, repeating important cases.
Include corrections, refused personal details, a one-step request, interrupted
read-back, a final question plus goodbye, and actual native termination.

## 结论

This candidate separates shared speaking policy from node work. It is not
published, registered as a template, or claimed to have passed live voice tests.
