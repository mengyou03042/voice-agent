# Outbound Sales Representative with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for an outbound call from a
fictional data platform, CloudSync, as a staged handoff graph. It is the same
conversation design that the Microsoft Foundry **Outbound sales representative**
template creates, without that template's tools. It needs no MCP service,
Project connection, or Toolbox, so it runs in any Foundry Project.

The agent does not search a calendar, book a demo, or create a lead. It reads
the demo request back and says that an account executive will confirm a time.
Stages that used tools in the original template now carry a plain "no system is
connected" limit.

## When to use this example

Use it to try permission-based openers, concise objection handling, and
do-not-call requests before you connect real calendar or CRM tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `opener` | Ask permission for 30 seconds. |
| `pitch` | Give one value proposition and one qualifying question, then listen. |
| `close` | Wrap up warmly whatever the outcome. |
| `book` | Capture preferred demo times and contact details as a request. |
| `handle_objection` | Acknowledge the objection, answer with one concrete point, and check it resolved the concern. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

CloudSync keeps data from apps and databases in sync in real time. Demos are
30-minute Teams video calls with an account executive on weekdays. Most teams
start by replacing one pipeline. No prices are quoted.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 26: Outbound Sales Representative**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "Sure, I have a minute. That sounds useful, I'd like a demo." Expect preferred
  times and contact details read back as a request.
- "We already built our own pipelines and we're too busy." Expect one concrete
  point from the sample facts.
- "Take me off your list." Expect the request noted and the call ending.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The company and product are fictional; there is no calendar or CRM system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
