# Survey and Feedback Intake with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for an outbound feedback call
from a fictional company, Contoso, as a staged handoff graph. It is the same
conversation design that the Microsoft Foundry **Survey and feedback intake**
template creates, without that template's tools. It needs no MCP service,
Project connection, or Toolbox, so it runs in any Foundry Project.

The agent does not match the respondent to a record or save the answers. It
reads the summary back and says that the feedback is noted for the team. Stages
that used tools in the original template now carry a plain "no system is
connected" limit.

## When to use this example

Use it to try consent handling, scaled questions, and a confirmed summary before
you connect real CRM or survey tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `intro_consent` | Mention the recent support call and ask for about three minutes. |
| `questions` | Ask each question in order, one at a time, and wait for the answer. |
| `polite_decline` | Thank a respondent who declines and end without pressure. |
| `summary` | Read back the scores and comments and ask whether they are correct. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Respondent Jordan Lee. Questions: satisfaction with the recent support call (1
to 5), likelihood to recommend Contoso (0 to 10), one thing to do better, and
anything still unresolved.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 31: Survey and Feedback Intake**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "Sure." Then answer "4", "8", "Shorter hold times", and "No." Expect one
  question at a time and a summary, never "saved".
- "I don't have time." Expect a graceful goodbye.
- "That's all I have time for." Expect the summary straight away.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The respondent and company are fictional; there is no CRM or survey system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
