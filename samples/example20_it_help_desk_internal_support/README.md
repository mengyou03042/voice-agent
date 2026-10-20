# IT Help Desk with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for first-line internal IT
support as a staged handoff graph. It is the same conversation design that the
Microsoft Foundry **IT help desk** template creates, without that template's
tools. It needs no MCP service, Project connection, or Toolbox, so it runs in
any Foundry Project.

The agent does not search knowledge articles, file a ticket, or comment on an
existing one. It gives general steps, reads back the escalation details, and
says that someone must file them manually. Stages that used tools in the
original template now carry a plain "no system is connected" limit.

## When to use this example

Use it to try issue identification, one-step troubleshooting, and honest
escalation before you connect real knowledge-base or ticketing tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `identify` | Capture the employee's name, department, and the type and impact of the issue. |
| `troubleshoot` | Walk through general steps one at a time and wait for the result. |
| `escalate` | Read back the escalation details with the response time and say they are not yet filed. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Self-service password reset at passwordreset.contoso.com (also re-registers
MFA). VPN client: GlobalProtect. Approved software comes from the Company Portal
app. IT responds in about four business hours for medium impact and one hour for
high impact. Phishing and unauthorized access go to the security team as high
priority.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 20: IT Help Desk**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "VPN says authentication failed." Expect one general step at a time.
- "I'm locked out of my account." Expect the reset portal and no password
  requested.
- "Still failing, please escalate." Expect a read-back of the escalation and no
  claim of a ticket.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The company IT facts are fictional; there is no knowledge base or ticketing
  system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
