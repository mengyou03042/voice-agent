# Corporate Training Role-Play Coach with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent that role-plays a tough
workplace conversation and then coaches the trainee, as a staged handoff graph.
It is the same definition that the Microsoft Foundry **Corporate training
role-play coach** template creates. It needs no MCP service, Project connection,
or Toolbox, so it runs in any Foundry Project.

The source template uses no tools, so nothing is removed. The agent does not
save scores or send a report; the debrief is given only in the conversation.

## When to use this example

Use it to try in-character role-play stages and a clean switch to an
out-of-character debrief before you connect real learning-management or
reporting tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `select` | Welcome the trainee, describe the scenarios, and wait until they are ready. |
| `customer` | Play the angry customer or the difficult employee in character. |
| `sales` | Play the sales prospect or the negotiation counterpart in character. |
| `debrief` | Step out of character and score Communication, Objection Handling, Empathy, and Resolution from 1 to 5 with one takeaway. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Four fictional scenarios: Pat, a Contoso Home Internet customer whose repair
visit was missed twice; Riley, a capable employee who missed three deadlines;
Sam, a Fabrikam finance director evaluating a 40,000 dollar a year analytics
subscription; and Alex, a supplier account manager asking for a 12 percent price
increase.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 11: Corporate Training Role-Play Coach**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "Let's do the angry customer." "Ready." Expect the coach to set the scene and
  play Pat in character.
- "Let's stop, give me feedback." Expect scores from 1 to 5 with reasons, quotes
  of your lines, and one takeaway.
- "Sales objection handling." Expect Sam to push back on price and ROI until you
  give evidence.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- All scenarios, people, and companies are fictional; there is no
  learning-management system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
