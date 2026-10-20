# Technical Support Agent with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for a fictional cloud product,
Contoso Cloud, that triages and troubleshoots issues as a staged handoff graph.
It is the same conversation design that the Microsoft Foundry **Technical
support agent** template creates, without that template's tools. It needs no MCP
service, Project connection, or Toolbox, so it runs in any Foundry Project.

The agent does not search knowledge articles, look up an account, or file or
update a ticket. It gives general steps, reads back the escalation, and says
that someone must file it manually. Stages that used tools in the original
template now carry a plain "no system is connected" limit.

## When to use this example

Use it to try triage between technical and account paths and honest escalation
before you connect real knowledge-base, customer record, or ticketing tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `greeting` | Listen to the issue and capture the caller's name. |
| `troubleshoot` | Walk through general steps one at a time and wait for the result. |
| `account_billing` | Give general account and billing guidance; the account is not verified. |
| `wrap_up` | Confirm the fix that worked or the escalation that was noted. |
| `escalate_ticket` | Read back the escalation summary and urgency; nothing is filed. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Contoso Cloud technical support. Issues needing the engineering or accounts team
get a ticket, usually answered within one business day. Passwords are never
collected; callers use the "Forgot password" link on the sign-in page.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 32: Technical Support Agent**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "My sync keeps failing with a timeout." Expect one general step at a time.
- "Still broken, escalate it, high urgency." Expect a read-back and no ticket
  number.
- "I forgot my password." Expect the "Forgot password" link and no password
  requested.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The product and support facts are fictional; there is no knowledge base,
  customer record, or ticketing system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
