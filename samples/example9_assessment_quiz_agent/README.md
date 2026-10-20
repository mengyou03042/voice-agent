# Assessment and Quiz with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent that proctors a spoken
10-question security awareness quiz as a staged handoff graph. It is the same
definition that the Microsoft Foundry **Assessment and quiz** template creates.
It needs no MCP service, Project connection, or Toolbox, so it runs in any
Foundry Project.

The source template uses no tools, so nothing is removed. The agent does not
save scores or send results; the score is given only in the conversation.

## When to use this example

Use it to try strict turn-by-turn questioning, neutral acknowledgements, and a
branch on the final score before you connect real learning-management or
reporting tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `intro` | Set expectations: the topic, 10 questions, about 15 minutes, one point each, and 7 of 10 to pass. |
| `questions` | Ask the questions in order, exactly one per turn, with neutral acknowledgements and no hints. |
| `pass_node` | Confirm the pass, review any missed question, give the exact score, and suggest next topics. |
| `fail_node` | Review each missed question, give the score constructively, and suggest what to study before a retake. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Security awareness basics: 10 questions on passwords, phishing, data handling,
physical security, devices, and software updates; one point each, no penalty for
guessing, and 7 of 10 to pass. Answers with the same meaning are accepted.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 9: Assessment and Quiz**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "I'm ready." Then answer "No, one breach exposes both" to the first question.
  Expect one question per turn and no hints.
- Answer "I don't know" to four or more questions. Expect the needs-work debrief
  with each missed answer explained.
- After the score, "Question 5 should count." Expect the reasoning, with the
  score unchanged.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The quiz content is fictional sample material; there is no learning-management
  system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
