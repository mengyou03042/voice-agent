# Legal Intake Specialist with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for a fictional law firm,
Contoso Law Group, that runs confidential intake as a staged handoff graph. It
is the same conversation design that the Microsoft Foundry **Legal intake
specialist** template creates, without that template's tools. It needs no MCP
service, Project connection, or Toolbox, so it runs in any Foundry Project.

The agent does not save the intake, check conflicts in a system, or book a
consultation. It reads the intake and a preferred consultation time back and
says that the firm will follow up. It gives no legal advice and quotes no fees.
Stages that used tools in the original template now carry a plain "no system is
connected" limit.

## When to use this example

Use it to try confidential intake, scope screening, and emergency routing before
you connect real CRM or calendar tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `greeting` | Introduce the firm and reassure the caller that what they share is confidential. |
| `identify_matter` | Clarify the matter type. |
| `emergency_resources` | Direct a caller in or near an emergency to emergency services. |
| `conflict_check` | Capture the other parties' names before detailed facts. |
| `refer_out` | Refer out-of-scope matters to the bar association's lawyer referral service. |
| `collect_facts` | Capture the essential facts and contact details for attorney review. |
| `wrap_up` | Confirm the next step that was noted. |
| `schedule_consultation` | Capture the consultation format and a preferred time as a request. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Contoso Law Group, 100 Contoso Plaza, Seattle, Washington. Practice areas:
personal injury, employment law, family law, and estate planning. Not handled:
criminal defense, immigration, bankruptcy, or tax. Consultations are 45 minutes
on weekdays by video, phone, or in person; fees are discussed at the
consultation.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 22: Legal Intake Specialist**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "I was rear-ended last month and hurt my back." Expect the conflict-check
  question, fact collection, and a read-back noted for attorney review.
- "I was arrested and need a defense lawyer." Expect a referral to the lawyer
  referral service.
- "Can I come in Tuesday?" Expect the preference read back as a request, not a
  booking.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The firm and its practice areas are fictional; there is no CRM or calendar
  system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
