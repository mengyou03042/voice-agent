# Appointment Setter with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent that qualifies a prospect's
interest and coordinates a meeting **request** as a staged handoff graph. It is
the same definition that the Microsoft Foundry **Appointment setter** template
creates. It needs no MCP service, Project connection, or Toolbox, so it runs in
any Foundry Project.

The agent does not read a calendar, book a meeting, send an invite or email, or
create a CRM record. It collects proposed times, timezone, attendees, and email,
reads the request back, and says that the team will confirm a time.

## When to use this example

Use it to try lead qualification, a branch for prospects who are not ready, and
spoken transfer messages before you connect real calendar, mail, or CRM tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `greeting` | Thank the prospect and ask what they hope to solve. |
| `qualify` | Understand use case, role, and timeline without pressure. |
| `check_availability` | Collect two or three proposed times, the timezone, and attendees. |
| `book_meeting` | Confirm format, attendees, and email, then read back the meeting request. |
| `nurture` | Respect a prospect who is not ready and note follow-up preferences. |
| `wrap_up` | Confirm the request; no invite or email has been sent. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Edges into business stages carry a short, neutral `transfer_message`. The
caller hears audio sooner than with a silent handoff, and two consecutive
scheduling stages do not repeat the same message.

Each stage repeats the persona, tone, and conversation rules because a handoff
node's instructions replace the session instructions. Those rules tell the agent
to acknowledge the caller's specific point before any question, match the
caller's energy a notch calmer, and never claim that something was booked or
sent.

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
- "I'm not ready yet, just send me something." Expect the nurture stage and no
  claim that anything was sent.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- All company facts are fictional; there is no calendar, mail, or CRM system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an
  authorization boundary.
