# Internal Knowledge Assistant with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for internal employee
questions, routed by question type, as a staged handoff graph. It is the same
conversation design that the Microsoft Foundry **Internal knowledge assistant**
template creates, without that template's tools. It needs no MCP service,
Project connection, or Toolbox, so it runs in any Foundry Project.

The agent does not search a knowledge base or log a documentation gap. It says
that no docs are connected, labels any guidance as general, and reads back a gap
note that someone must log manually. Stages that used tools in the original
template now carry a plain "no system is connected" limit.

## When to use this example

Use it to try question classification and honest answers when no source is
connected before you connect real knowledge-base or ticketing tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `greeting` | Greet briefly and ask what the employee is trying to figure out. |
| `classify_question` | Decide whether the question is a quick fact, a multi-step procedure, or not answerable. |
| `factual_lookup` | Give a short general answer and say plainly that no docs were checked. |
| `complex_walkthrough` | Walk through general steps one at a time and check the employee is following. |
| `not_in_kb` | Say it cannot be answered here, never guess, and read back a gap note for follow-up. |
| `confirm_understanding` | Check whether the question was answered and offer another topic. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Questions normally come from the company help center; questions it cannot answer
go to the docs team, who ask a subject matter expert to follow up.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 18: Internal Knowledge Assistant**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "How do I request a new monitor?" Expect general guidance labeled as general
  and no article title.
- "What's our policy for expensing conference travel?" Expect no guess and an
  offer to note the question for the docs team.
- "Thanks, that's all." Expect a short goodbye and the session ending.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- There is no knowledge base or ticketing system; answers are general guidance
  only.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
