# Appointment Setter with Handoff

## Overview

`agent.json` is a portable, tool-free Voice Agent that qualifies a prospect's
interest and coordinates an **unsubmitted meeting request** as a staged handoff
graph. The example portal loads this local definition. It needs no MCP service,
Project connection, or Toolbox, so it can run in any Foundry Project.

The agent does not read a calendar, book a meeting, send an invite or email, or
create a CRM record. It collects proposed times, timezone, meeting format,
attendees, and email, then reads them back for manual use. It does not submit or
forward the request; a human must separately confirm a time. It does not promise
that someone received the request, will send materials, or will contact the caller.

## When to use this example

Use it to try lead qualification, a branch for prospects who are not ready, and
spoken transfer messages before you connect real calendar, mail, or CRM tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `greeting` | Use the caller's intent, answer direct requests, and route without asking again for a known purpose. |
| `qualify` | Understand use case, role, and timeline without pressure. |
| `check_availability` | Collect missing proposed times/timezone, then hand off without another request recap. |
| `book_meeting` | Confirm format, attendees, and email, then read back the meeting request. |
| `nurture` | Respect a prospect who is not ready and note follow-up preferences. |
| `wrap_up` | Answer remaining questions without repeating a confirmed request or another recap. |
| `end` | Call `end_conversation` after the incoming edge supplies one short goodbye. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Explicit caller stop requests can also use the existing native
`end_conversation` system tool directly in the entrypoint or any business stage.
This avoids saying a call is ending without actually executing termination.
Answer any actual last question first; a capability limit is not a reason to
end before answering. No business tool or external write is added.

Existing business transfer messages acknowledge readiness or state that
this is only a request; they do not preview an action that the next model reply
should announce again. Waiting coverage is retained rather than deleting these
messages. Each existing edge into `end` supplies one short goodbye; the end node
is instructed to call the native tool without adding a second farewell.

A final question followed by goodbye is answered aloud before native ending.
An explicit stop with no remaining question must invoke the native tool or
complete the existing end route, not just say the call is ending. A completed
request does not need another recap or
confirmation question. Any requested email address is only part of the
unsubmitted draft, not a destination for an invitation this agent can send.
The time-collection stage does not submit anything to a team. The destination
stage owns attendee/email collection and the requested combined read-back.

Each stage repeats the persona, tone, and conversation rules because a handoff
node's instructions replace the session instructions. Those rules tell the agent
to acknowledge the caller when useful, avoid repeating a fixed transfer's
acknowledgement, match the caller's energy a notch calmer, and never offer or
claim unavailable calendar, mail, CRM, persistence, or submission actions.

Corrections replace only the changed fields before a read-back. Names and email
addresses are independent: use the latest explicit spelling without changing an
email to match a person's name. Keep other fields, such as the timezone and
attendees, unless the caller changes them. Ask when uncertain rather than
confirming an old value.

No product briefs, pricing facts, or prep materials are provided. The agent
should say so when asked, not offer email delivery or repeatedly append a prep
materials question to a requested read-back. A planning horizon such as next
quarter is not by itself a refusal to have a demo.

These are authored behavior rules, not a claim that live voice quality or
latency has passed. Changes to fixed messages and their model continuations
must be checked together in complete, same-condition conversations.

The example uses `azure_semantic_vad` with `profile: normal` and
`silence_duration_ms: 400`. These settings affect turn boundaries and response
waiting; compare complete, same-condition conversations before judging latency
or interruption behavior.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 6: Appointment Setter**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "We need to automate our support calls and I'd like a demo." Expect a short
  qualification, then requests for proposed times and a timezone.
- "Thursday at 2 or Friday morning, Pacific time." Expect a read-back and no
  claim that a time is booked.
- "I'm not ready yet, just send me something." Expect an honest explanation that
  documents cannot be sent, no pressure to provide an email, and an offer to
  read back known details.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- All company facts are fictional; there is no calendar, mail, or CRM system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an
  authorization boundary.

## Conclusion

The output is an unsubmitted request, not a booking or a sent invitation.
Verify both the requested spoken answer and native termination; a farewell
alone is not proof that the session actually ended.
