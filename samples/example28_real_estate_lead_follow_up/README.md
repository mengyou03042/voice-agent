# Real Estate Lead Follow-Up with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for a fictional brokerage,
Contoso Realty, that follows up property leads as a staged handoff graph. It is
the same conversation design that the Microsoft Foundry **Real estate lead
follow-up** template creates, without that template's tools. It needs no MCP
service, Project connection, or Toolbox, so it runs in any Foundry Project.

The agent does not search a calendar, book a showing, create a lead, or send
floor plans. It reads the request back and says that the agent will follow up.
Stages that used tools in the original template now carry a plain "no system is
connected" limit.

## When to use this example

Use it to try buyer qualification, listing discussion from sample facts, and
request capture before you connect real calendar or CRM tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `greeting` | Introduce yourself, reference the property they viewed, and thank them. |
| `qualify` | Understand timeline, budget, pre-approval, and what they want. |
| `discuss_properties` | Discuss one to three matching listings from the sample facts only. |
| `book_showing` | Capture the listing, preferred showing time, and contact details as a request. |
| `send_info` | Capture which information they want and how to follow up. |
| `wrap_up` | Confirm the next step that was noted. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

14 Maple Court, Redmond: 3 bed, 2 bath craftsman, $849,000. 220 Lakeview Drive,
Kirkland: 2 bed, 2 bath condo, $695,000. 8 Cedar Lane, Bellevue: 4 bed, 3 bath
modern home, $1,450,000. Showings take 45 minutes at the property's front door.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 28: Real Estate Lead Follow-Up**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "We want three bedrooms in Redmond under 900k. Can I see 14 Maple Court
  Saturday?" Expect listed features only and a showing request, not a booking.
- "Send me the floor plans for the Kirkland condo." Expect a request noted,
  never "sent".
- "What's the kitchen like at 8 Cedar Lane?" Expect no invented details.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The brokerage and listings are fictional; there is no calendar or CRM system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
