# Receptionist and Messaging: shared-prompt backup v1

## Scope

This is a backup-only candidate derived from the frozen
[revised definition](../revised/agent.json), not the independently edited live
template. The [original](../original/agent.json) and revised snapshots are unchanged.

- [Shared prompt](shared_prompt.md): personality, environment, company facts,
  tone, response style, spoken delivery, goal, and global truth/privacy/
  capability boundaries. It contains no node IDs, message-field checklist,
  route conditions, or termination procedure.
- [Node prompts](node_prompts.md): the implicit entrypoint and each node's own
  objective, actions, routes, and closing behavior.
- [Agent definition](agent.json): the portable authored candidate. Shared text
  appears once in `definition.instructions`; business nodes contain only local
  instructions and set `inherit_from_base_instructions: true`.

Company hours, location, parking, and directory entries remain shared reference
facts, not routing destinations or collection logic. The implicit entrypoint's
policy lives in its outgoing edge description. The terminal node opts out of
inheritance so it emits only the ending-tool call.

## Runtime and behavior

The existing sample and Portal publishers expand instruction inheritance before
publication. Do not send an unexpanded inheritance flag directly to a service
version that rejects it. No new service field or loader is added.

The candidate keeps the revised model, voice, greeting, audio/VAD, storage,
tools, tool choices, node/edge IDs, transfer limits, fixed edge messages, and
target-response settings. Node and edge descriptions are aligned with local
duties. Answering an FAQ does not cancel a pending message; recipient continuation
uses the existing route rather than inventing a new edge.

The directory node owns recipient matching. The message node owns optional
fields and one combined read-back. The wrap-up node handles actual remaining
questions or corrections instead of replaying the draft. End edges own the
single farewell; the terminal node only invokes the native ending tool.

The design follows the referenced [Front Desk fluency guidance](../../../../../../docs/voice_agent/flunecy_improvment/02_frontdesk_fluency_first_shared_prompt.md):
respond to the caller's meaningful point, preserve known evidence, and keep
specific business actions out of the shared speaking policy. A direct FAQ
answer counts as a response without a formulaic acknowledgement.

## Verification and limits

The snapshot manifest records provenance and SHA-256 hashes. Offline checks
cover prompt-source equality, shared/local separation, inheritance expansion,
graph/tool/audio preservation, matching route descriptions, exact company
facts, and frozen-source integrity. They are not live conversational evidence.

Before promotion, compare full conversations under identical runtime settings.
Repeat compound FAQ/message requests, invalid directory names, declined callback
numbers, corrected recipients, requested repeats, interrupted read-back, final
questions plus goodbye, and native termination with one audible farewell.

## 结论

This candidate separates shared speaking policy and company facts from node
work. It stays an unpublished backup and does not imply real transfer, storage,
delivery, or a measured live fluency improvement.
