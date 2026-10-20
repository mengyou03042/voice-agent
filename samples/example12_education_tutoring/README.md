# Education and Tutoring with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for a fictional tutoring
service, Contoso Tutoring, that teaches a topic step by step as a staged handoff
graph. It is the same conversation design that the Microsoft Foundry **Education
and tutoring** template creates, without that template's tools. It needs no MCP
service, Project connection, or Toolbox, so it runs in any Foundry Project.

The agent does not search a calendar or book the next session. At the wrap-up it
summarizes progress and can note a preferred time for the next session, which
someone must schedule manually. Stages that used tools in the original template
now carry a plain "no system is connected" limit.

## When to use this example

Use it to try level-based branching, step-by-step explanations, and practice
loops before you connect real calendar tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `welcome` | Welcome the student and find out what they want to work on. |
| `assess_level` | Ask a couple of open questions to gauge what the student already knows. |
| `advanced_explore` | Explore the topic in depth for a student with a foundation. |
| `teach_fundamentals` | Teach the basics step by step for a student who needs a foundation. |
| `practice` | Work through practice problems at the right level, one at a time. |
| `wrap_up` | Summarize what the student learned and what to practice next; any next-session request is noted only. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Contoso Tutoring offers 30-minute follow-up sessions with Sage as Microsoft
Teams video calls.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 12: Education and Tutoring**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "Help me with adding fractions." Expect level questions, then teaching and a
  practice problem.
- "I have to go." Expect a short summary instead of an abrupt end.
- "Can we book the next session for Thursday?" Expect the preference noted and
  no claim that it was booked.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The tutoring service is fictional; there is no calendar or student record
  system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
