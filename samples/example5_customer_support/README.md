# Customer Support with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent that handles first-line
customer support as a staged handoff graph. It is the same definition that the
Microsoft Foundry **Customer support** template creates. It needs no MCP
service, Project connection, or Toolbox, so it runs in any Foundry Project.

The agent never claims an outcome that no tool produced. It does not create
tickets, change accounts, verify identity, or transfer to a person. It prepares
an unsubmitted summary and says that someone must follow up manually.

## When to use this example

Use it to try a multi-stage support conversation, staged handoff, and spoken
transfer messages before you connect real ticketing, knowledge, or CRM tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `identify_issue` | Acknowledge the problem and classify it as technical or account/billing. |
| `troubleshoot` | Suggest one concrete step at a time and wait for the result. |
| `account_billing` | Give general account and billing guidance; identity is not verified. |
| `resolve_or_escalate` | Confirm the fix, or read back an unsubmitted follow-up summary. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye, asks to stop,
or reached the wrong number. Edges into business stages carry a short, neutral
`transfer_message`. The caller hears audio sooner than with a silent handoff,
and the message never announces a transfer or promises a result.

Each stage repeats the persona, tone, and conversation rules because a handoff
node's instructions replace the session instructions. Those rules tell the agent
to acknowledge the caller's specific point in a few words before any question,
match the caller's emotional intensity a notch calmer, and avoid generic
acknowledgements, invented emotions, and premature "I'll" or "transferring".

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 5: Customer Support**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "My API calls started returning 500 errors this morning." Expect routing to
  troubleshooting and one step at a time.
- "I was charged twice this month." Expect the account stage and no claim of a
  refund or a verified account.
- "That didn't help, can someone look at it?" Expect a read-back summary that
  is explicitly not submitted.
- "Thanks, that's all." Expect a short goodbye and the session ending.

## Boundaries

- All company facts are fictional; there is no knowledge base, ticketing, CRM,
  payment system, or live transfer.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; a prompt alone does not make a tool read-only.
