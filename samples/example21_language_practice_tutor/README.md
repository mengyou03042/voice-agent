# Language Practice Tutor with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for a fictional language
studio, Contoso Language Studio, that runs conversation practice as a staged
handoff graph. It is the same conversation design that the Microsoft Foundry
**Language practice tutor** template creates, without that template's tools. It
needs no MCP service, Project connection, or Toolbox, so it runs in any Foundry
Project.

The agent does not search a calendar or book the next session. In the summary it
can note a preferred time, which someone must schedule manually. Stages that
used tools in the original template now carry a plain "no system is connected"
limit.

## When to use this example

Use it to try level-based branching and recaps in the right language before you
connect real calendar tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `assess` | Welcome the student, ask which language, and gauge their level. |
| `beginner` | Practice simple phrases slowly with gentle corrections. |
| `advanced` | Hold a natural conversation in the target language with targeted feedback. |
| `summary` | Recap practiced items, new words, strengths, and one area to work on. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Contoso Language Studio offers 30-minute practice sessions with Lena as
Microsoft Teams video calls.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 21: Language Practice Tutor**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "Let's practice Spanish, I'm a beginner." Expect simple phrases and an English
  recap.
- "I'm intermediate in French." Expect advanced practice and a recap in French.
- "Can you book my next session for Friday?" Expect the preference noted and no
  claim of a booking.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The studio is fictional; there is no calendar or student record system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
