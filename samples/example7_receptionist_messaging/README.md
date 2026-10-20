# Receptionist and Messaging with Handoff

## Overview

`agent.json` is a portable, tool-free Voice Agent for a fictional company,
Contoso, that answers front desk questions, matches requested recipients to a
directory, and prepares messages as a staged handoff graph. The example portal
loads this local definition; a deployed Toolbox variant is a separate version.
It needs no MCP service,
Project connection, or Toolbox, so it runs in any Foundry Project.

The agent does not check anyone's availability, transfer the call, or send a
text or email. It matches the caller's request to a sample directory, reads a
message back as an unsent draft for the caller to note. It does not forward the
draft, save a business record, promise that someone will receive it, or arrange
a callback.

## When to use this example

Use it to try intent routing, answers grounded in a short list of company facts,
and message taking before you connect real presence, mail, or SMS tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `greeting` | Use the known intent and silently route a message request, with its existing details, to `take_message`. |
| `transfer` | Match the directory entry, answer the requested capability limits directly, and offer a caller-use unsent draft. |
| `take_message` | Explain the unsent/manual-use limit once, ask one missing detail, and read the known details together as one draft. Names and callback numbers are optional. |
| `answer_faq` | Answer hours, location, and parking questions from the sample facts only. |
| `wrap_up` | Check actual spoken completion, supply a missing draft once if needed, and otherwise continue without another recap or action announcement. |
| `end` | Call `end_conversation` after the incoming edge's single goodbye, without another spoken reply. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. A naturally completed task can also close without an explicit caller
goodbye or an extra confirmation; an unfinished request or correction must
still be handled.

The existing edges into `wrap_up` retain the short, neutral `transfer_message`
"All right." It covers the handoff without promising another recap. The next
stage continues directly rather than repeating the cue, thanks, or an action
announcement. Other business handoffs remain silent. Each existing edge into
`end` now supplies "Goodbye." once; the end node only calls the native ending
tool. Message-taking stages must not add their own farewell or tell the caller
to disconnect instead of invoking the end route.

Every message read-back includes the known recipient, caller name, grouped
callback number, and message once. After reading it back, the agent should not
announce another future read-back. Caller-requested repeats and corrections
remain supported. A final question is answered aloud before ending.
The draft limit is stated once for a new message request, not repeated on every
correction. Declining a callback number does not end a still-active message task.
The first message-taking reply owns that explanation. Missing-detail questions
do not inventory known fields or announce future steps. A completed draft needs
no extra claim of recording it or arranging follow-up. If the caller says they
have already explained the issue, continue from the known recipient and topic
rather than restarting the intake.
For a read-back alone, the spoken reply ends with the message content, without
another completeness announcement, manual-use reminder, or routine request for
confirmation. An explicit question about sending or saving still receives an
answer. A genuinely necessary question waits for the caller instead of being
followed by an immediate closing.
An explicit finish request goes directly to `end`, even after a complete draft;
the natural-completion `wrap_up` route is not a substitute for that request.
The end node remains silent on every resumed turn after an interrupted ending
call and calls the existing ending tool again without another acknowledgement.
Message completion requires an actual spoken draft, not just fields in an
internal handoff reason. `wrap_up` checks this rather than assuming the previous
stage already read it. It supplies a missing draft once, never repeats a
completed one without a caller request, and gives an explicit stop priority.

Directory entries such as Sales or Alex Wilber identify a message recipient,
not a `handoff` target. The entrypoint can target only `greeting`; each stage
uses only the IDs in its declared routes. An internal handoff failure is not
evidence that a real telephone transfer was attempted.
The directory stage answers requested capability limits aloud before proposing
an alternative. Asking for an email does not by itself accept an unsent draft;
the caller decides whether to use that alternative before intake starts.

The root `definition.instructions` is the shared prompt: Personality,
Environment, Tone, How you respond, How you sound, Goal, and Guardrails. Company
facts and capability limits live there once, without stage routes, a message
field checklist, or an entrypoint procedure. Every node sets
`inherit_from_base_instructions: true` and contains only its own stage
instructions. The existing publisher combines the shared and local text before
publishing; it does not depend on automatic service-side inheritance.
The existing `$entrypoint` edge specifies the initial silent route.

An explicit concern or frustration can receive a brief, specific response;
ordinary requests do not require an acknowledgement formula. Directory matching,
message-field collection, combined read-back, routing, and ending stay local.

The example uses `azure_semantic_vad` with `profile: normal` and
`silence_duration_ms: 400`. These settings affect turn boundaries and response
waiting; compare complete, same-condition conversations before judging latency
or interruption behavior.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 7: Receptionist and Messaging**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "What are your hours, and where do I park?" Expect the sample hours and
  visitor parking at the main entrance.
- "Can I talk to Alex Wilber?" Expect a plain statement that the line cannot
  transfer calls, and an offer to take a message.
- "Please tell Megan Bowen I called about my onboarding." Expect questions for
  your name and callback number, a read-back, and no claim that it was sent.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- All company facts and directory entries are fictional; there is no presence,
  mail, or SMS system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an
  authorization boundary.

## Conclusion

The supported result is company information or an unsent draft for manual use,
not delivery to a recipient. Verify the whole conversation, including fixed
messages, model continuations, truncations, and the actual native ending event.
