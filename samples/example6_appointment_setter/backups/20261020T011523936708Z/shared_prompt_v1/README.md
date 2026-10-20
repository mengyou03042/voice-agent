# Appointment Setter: shared-prompt backup v1

## Scope

This is a backup-only candidate derived from the frozen
[revised definition](../revised/agent.json), not the independently edited live
template. The [original](../original/agent.json) and revised snapshots are unchanged.

- [Shared prompt](shared_prompt.md): personality, environment, tone, response
  style, spoken delivery, goal, and global truth/privacy/capability boundaries.
  It contains no node IDs, meeting-field checklist, route conditions, or
  termination procedure.
- [Node prompts](node_prompts.md): the implicit entrypoint and each node's own
  objective, actions, routes, and closing behavior.
- [Agent definition](agent.json): the portable authored candidate. Shared text
  appears once in `definition.instructions`; business nodes contain only local
  instructions and set `inherit_from_base_instructions: true`.

The implicit entrypoint's policy is stored in its outgoing edge description,
not in the shared prompt. The terminal node opts out of inheritance so it emits
only its ending-tool call.

## Runtime and behavior

The existing sample and Portal publishers expand instruction inheritance before
publication. Do not send an unexpanded inheritance flag directly to a service
version that rejects it. No new service field or loader is added.

The candidate keeps the revised model, voice, greeting, audio/VAD, storage,
tools, tool choices, node/edge IDs, transfer limits, fixed edge messages, and
target-response settings. Local route descriptions are updated to match the
node prompts rather than retaining conflicting old instructions.

Two termination paths are now explicit and disjoint:

1. An explicit caller stop: the current node answers any actual final question
   or read-back, says one brief farewell, and calls `end_conversation` directly.
   It does not take an end edge and cannot rely on that edge's fixed audio.
2. Natural completion without an explicit stop: the node hands off silently to
   `end`; the existing edge supplies the farewell and the terminal node only
   calls the native tool.

Meeting fields and their correction rules belong to collection/read-back nodes,
not the shared prompt. Email and nurture follow-up preferences are optional.
The nurture completion edge is aligned with that fact; it does not require
those fields just to finish. The wrap-up route applies to confirmed details
with a remaining request, not every completed read-back.

The design follows the referenced [Front Desk fluency guidance](../../../../../../docs/voice_agent/flunecy_improvment/02_frontdesk_fluency_first_shared_prompt.md):
respond to meaningful caller content, avoid invented emotions and results, and
keep business steps local. An ordinary direct answer needs no extra bridge.

## Verification and limits

The snapshot manifest records provenance and SHA-256 hashes. Offline checks
cover prompt-source equality, shared/local separation, inheritance expansion,
graph/tool/audio preservation, matching route descriptions, coherent ending
paths, and frozen-source integrity. They do not establish live voice quality.

Before promotion, compare whole conversations with identical runtime settings
and caller evidence. Repeat corrected time/timezone/email, declined email,
next-quarter planning, paused scheduling, interrupted read-back, stop at the
first turn, final question plus goodbye, and natural completion cases. Inspect
actual tool events and the number of audible farewells, not just transcripts.

## 结论

This candidate separates shared speaking policy from appointment-node work and
removes the conflicting ending instructions. It remains an unpublished backup,
not a verified booking service or a live-validated fluency improvement.
