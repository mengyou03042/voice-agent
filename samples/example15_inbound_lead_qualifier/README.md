# Inbound Lead Qualifier with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for a fictional software
company, Contoso, that qualifies inbound prospects as a staged handoff graph. It
is the same conversation design that the Microsoft Foundry **Inbound lead
qualifier** template creates, without that template's tools. It needs no MCP
service, Project connection, or Toolbox, so it runs in any Foundry Project.

The agent does not search a calendar, book a meeting, create a lead, or send
materials. It collects contact details and preferred times, reads them back, and
says that the sales team will follow up. Stages that used tools in the original
template now carry a plain "no system is connected" limit.

## When to use this example

Use it to try BANT qualification and hot or nurture routing before you connect
real calendar, CRM, or mail tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `greeting` | Thank the caller and ask what prompted the call. |
| `identify_needs` | Understand the core problem, what success looks like, and what they have tried. |
| `qualify_bant` | Collect budget, authority, need, and timeline conversationally. |
| `route_hot` | Capture a preferred meeting time and contact details for an account executive to confirm. |
| `route_nurture` | Capture contact details and a follow-up preference for a prospect who is not ready. |
| `wrap_up` | Confirm the next step that was noted, without claiming a booking or a sent email. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Contoso sells a cloud collaboration platform for mid-size and enterprise teams.
Account-executive meetings are 30-minute Teams video calls on weekdays covering
pricing, case studies, and a walkthrough. The agent quotes no prices or
discounts.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 15: Inbound Lead Qualifier**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "I'm Dana from Fabrikam. Budget is approved, I decide, and we need it within
  two months." Expect a meeting request with preferred times read back and no
  claim of a booking.
- "We're just exploring, no budget yet." Expect a nurture follow-up noted for
  the team.
- "How much does it cost?" Expect no price; the account executive covers
  pricing.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The company and product are fictional; there is no calendar, CRM, or mail
  system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
