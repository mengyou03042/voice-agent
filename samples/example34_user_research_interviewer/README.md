# User Research Interviewer with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent that runs a short user
research interview as a staged handoff graph. It is the same definition that the
Microsoft Foundry **User research interviewer** template creates. It needs no
MCP service, Project connection, or Toolbox, so it runs in any Foundry Project.

The source template uses no tools, so nothing is removed. The agent recaps the
answers at the end but does not record, save, or send notes.

## When to use this example

Use it to try neutral probing and time-based branching before you connect real
research repository tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `consent_intro` | Thank the participant and explain the study. |
| `discovery` | Ask the open discovery question and probe neutrally. |
| `depth_branch` | Reflect one point and ask how much time they have left. |
| `deep_dive` | Explore tools, workarounds, and ratings with an engaged participant. |
| `priority_questions` | Ask only the three priority questions when time is short. |
| `polite_close` | Thank a participant who is ready to stop. |
| `submit_notes` | Recap the interview for the participant to correct; nothing is saved. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Study: how small teams plan and track weekly work, 20 to 30 minutes. Discovery
question: "Walk me through how your team plans its work for the week." Three
priority questions cover tracking who does what, the last thing that slipped,
and one thing to change.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 34: User Research Interviewer**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "Sure, I'm happy to help." Then "I have 15 minutes." Expect the deep dive and
  ratings with reasons.
- "I only have a few minutes." Expect only the three priority questions, then
  the recap.
- "I'd rather stop here." Expect a thank-you, a recap, and the end.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The study is fictional; there is no research repository.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
