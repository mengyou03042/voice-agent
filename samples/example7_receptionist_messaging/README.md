# Receptionist and Messaging with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for a fictional company,
Contoso, that answers front desk questions, routes callers to a person or
department, and takes messages as a staged handoff graph. It is the same
conversation design that the Microsoft Foundry **Receptionist and messaging**
template creates, without that template's tools. It needs no MCP service,
Project connection, or Toolbox, so it runs in any Foundry Project.

The agent does not check anyone's availability, transfer the call, or send a
text or email. It matches the caller's request to a sample directory, reads a
message back, and says that the message is noted for follow-up.

## When to use this example

Use it to try intent routing, answers grounded in a short list of company facts,
and message taking before you connect real presence, mail, or SMS tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `greeting` | Find out whether the caller wants a person, a message, or company information. |
| `transfer` | Match the person or department to the directory, explain that the line cannot transfer, and offer a message. |
| `take_message` | Collect name, callback number, recipient, and summary, then read the message back. |
| `answer_faq` | Answer hours, location, and parking questions from the sample facts only. |
| `wrap_up` | Confirm the noted message or the information given. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Edges into `wrap_up` carry a short, neutral `transfer_message`, so the
caller hears audio sooner than with a silent handoff; the other handoffs are
silent.

Each stage repeats the persona, tone, conversation rules, and the sample company
facts because a handoff node's instructions replace the session instructions.
Without the facts in every stage, the agent would invent hours or addresses.

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
