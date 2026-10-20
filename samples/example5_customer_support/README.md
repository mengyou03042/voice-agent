# Customer Support with Handoff

## Overview

`agent.json` is a portable, tool-free Voice Agent that handles first-line
customer support as a staged handoff graph. The example portal loads this local
definition; it is not a claim about a separately deployed Toolbox variant. It needs no MCP
service, Project connection, or Toolbox, so it runs in any Foundry Project.

The agent is instructed not to claim an outcome that no tool produced. It does not create
tickets, change accounts, verify identity, or transfer to a person. It prepares
an unsubmitted summary and says that someone must follow up manually.

## When to use this example

Use it to try a multi-stage support conversation, staged handoff, and spoken
transfer messages before you connect real ticketing, knowledge, or CRM tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `identify_issue` | Classify the issue or answer the caller's limited note/next-step request without an unsolicited summary. |
| `troubleshoot` | Suggest one concrete step at a time and wait for the result. |
| `account_billing` | Give general account and billing guidance without an identity-check flow. |
| `resolve_or_escalate` | Confirm the fix, or read back an unsubmitted follow-up summary. |
| `end` | Call `end_conversation` after the incoming edge's single spoken goodbye. |

Every stage can route to `end` as soon as the caller says goodbye, asks to stop,
or reached the wrong number. Edges into business stages retain a short
`transfer_message` that states a capability limit, rather than announcing work
the target stage will describe again. The target replies directly to the latest
request instead of repeating the transition, greeting, or workflow. Shorter
wording still needs same-condition voice testing for newly exposed silence; an
early fixed message alone does not prove a faster substantive answer.

Every existing edge into `end` says "Goodbye." once. The target `end` node then
calls the same platform tool without another closing or question. This keeps
the spoken closing separate from tool-only termination and does not require the
caller to use a particular goodbye word or finish the current task.

The root `definition.instructions` is the shared prompt: Personality,
Environment, Tone, How you respond, How you sound, Goal, and Guardrails. It
contains no stage routes, field checklist, or entrypoint procedure. Every node
sets `inherit_from_base_instructions: true` and contains only its own stage
instructions. The existing publisher combines the shared and local text before
publishing; it does not depend on automatic service-side inheritance.
The existing `$entrypoint` edge specifies the initial silent route.

The shared conversation rules acknowledge only meaningful caller corrections,
emotions, and constraints, without mandatory filler or invented history.
Troubleshooting steps, note contents, routing, and termination remain local.

When the caller requests only one next step, an already suggested check counts:
the agent should not add a second recommendation just because another speech
segment or stage arrives. A final question must be answered aloud before the
end handoff; placing the answer only in an internal tool reason is insufficient.
An issue description alone does not request a new diagnostic. A later constraint
or request for brevity calls for a brief response to that constraint, not another
check, full summary, or submission reminder.

Summaries distinguish a suggestion from an accepted caller plan, an attempted
check, and an observed result. They preserve the latest corrected facts,
untested status, and urgency when supplied. Names and contact details are
optional. Nothing is sent automatically: the caller must submit the summary
themselves through a support channel they already know, with no promised
recipient, response time, or callback.
An issue-only note retains its known reference and omits recommendations unless
the caller asks to include them. Leaving out a personal field does not mean it
was never provided. Explaining a capability limit does not establish that the
caller confirmed or accepted it; notes must not invent that confirmation.
If the caller has not reported a test status, omit it rather than assuming the
issue is untested.

The example uses `azure_semantic_vad` with `profile: normal` and
`silence_duration_ms: 400`. These settings affect turn boundaries and response
waiting; compare complete, same-condition conversations before judging latency
or interruption behavior.

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
- No identity check is performed. Do not provide credentials or payment details;
  the agent should not request them to explain a limit or prepare a note.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; a prompt alone does not make a tool read-only.

## Conclusion

This example prepares general guidance and unsubmitted notes, not external
support actions. These are authored rules; complete same-condition conversations
and a human or Agent transcript review are still needed to verify a revision.
