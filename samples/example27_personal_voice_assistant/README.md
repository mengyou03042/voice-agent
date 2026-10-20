# Personal Voice Assistant with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for a fictional company,
Contoso, that answers questions, captures notes, and routes requests as a staged
handoff graph. It is the same conversation design that the Microsoft Foundry
**Personal voice assistant** template creates, without that template's tools. It
needs no MCP service, Project connection, or Toolbox, so it runs in any Foundry
Project.

The agent does not search docs, email notes, or file a follow-up request. It
reads the note or request back and says that it must be sent manually. Stages
that used tools in the original template now carry a plain "no system is
connected" limit.

## When to use this example

Use it to try intent routing between answers, notes, and team follow-ups before
you connect real knowledge-base, mail, or ticketing tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `understand` | Decide whether the user wants an answer, a note, or a person on a team. |
| `answer` | Answer from the sample facts, or read back a one-sentence note. |
| `route` | Identify the right team and read back the follow-up request. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Contoso headquarters, 1 Contoso Way, Redmond, Washington, Monday to Friday, 8 AM
to 6 PM Pacific. Teams for follow-ups: IT help desk, HR and benefits, Finance,
Legal, and Facilities.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 27: Personal Voice Assistant**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "What are the office hours?" Expect the sample hours.
- "Take a note: send the Q3 report to Finance by Friday." Expect a one-sentence
  read-back and no claim that it was emailed.
- "I need someone in Legal to review a contract." Expect Legal as the team and a
  request that is not filed.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The company facts and teams are fictional; there is no knowledge base, mail,
  or ticketing system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
