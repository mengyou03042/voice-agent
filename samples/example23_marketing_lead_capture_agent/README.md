# Marketing Lead Capture with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for a fictional workflow
automation product, Contoso Flow, that captures leads as a staged handoff graph.
It is the same conversation design that the Microsoft Foundry **Marketing lead
capture** template creates, without that template's tools. It needs no MCP
service, Project connection, or Toolbox, so it runs in any Foundry Project.

The agent does not book a sales call, create a lead, or send a case study or
pricing overview. It reads the contact details and request back and says that
the team will follow up. Stages that used tools in the original template now
carry a plain "no system is connected" limit.

## When to use this example

Use it to try conversational lead capture and hot or nurture routing before you
connect real calendar, CRM, or mail tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `greeting` | Welcome the visitor and ask what brought them here. |
| `collect` | Collect name, email, company, role, the problem, timeline, and any budget signal. |
| `hot` | Capture a preferred sales-call time for the team to confirm. |
| `nurture` | Capture the resource they want and a follow-up preference. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Contoso Flow is a no-code workflow automation platform with Starter, Business,
and Enterprise tiers; sales shares exact prices. A free 14-day trial is
available. Resources: a case study, a pricing overview, and a demo video. Sales
calls are 30-minute Teams video calls on weekdays.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 23: Marketing Lead Capture**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "I run operations at Fabrikam and we need to automate approvals this month;
  can we schedule a call?" Expect a call request read back, not a booking.
- "Just browsing; send me the pricing overview." Expect a follow-up noted, never
  "sent".
- "How much is Business?" Expect that sales shares exact prices, and the trial.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The product and tiers are fictional; there is no calendar, CRM, or mail
  system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
