# Travel Agency Trip Planner with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for a fictional agency,
Contoso Travel, that plans trips as a staged handoff graph. It is the same
conversation design that the Microsoft Foundry **Travel agency trip planner**
template creates, without that template's tools. It needs no MCP service,
Project connection, or Toolbox, so it runs in any Foundry Project.

The agent does not create a lead, book a trip, or email an itinerary. It reads
the trip request back and says that a travel agent will follow up with a
detailed proposal. Stages that used tools in the original template now carry a
plain "no system is connected" limit.

## When to use this example

Use it to try destination discovery and package recommendations from sample
facts before you connect real CRM or booking tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `discover` | Greet the traveler and ask about their plans. |
| `destination_details` | Build a trip around a destination the traveler already has in mind. |
| `recommend_destinations` | Recommend sample packages for an undecided traveler. |
| `build_itinerary` | Discuss stays and activities with ballpark pricing and policies. |
| `booking_wrap` | Read back the trip request for a travel agent; nothing is booked. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Packages per person, excluding international flights: 7-day Tuscany tour $2,800;
6-day Amalfi Coast escape $3,100; 8-day Bali wellness retreat $2,100; 10-day
Japan highlights $4,200; 5-day Costa Rica adventure $1,900. Groups of 8 or more
get 10 percent off. Full refund 60 or more days before departure, 50 percent 30
to 59 days, none within 30 days.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 33: Travel Agency Trip Planner**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "Japan in April for two, budget about 10,000 dollars." Expect $4,200 per
  person, flights excluded, and a request read back for a travel agent.
- "Somewhere relaxing, I'm not sure where." Expect a recommendation such as
  Bali.
- "We're a group of 10; what if we cancel 45 days out?" Expect the group
  discount and a 50 percent refund.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The agency, packages, and prices are fictional; there is no CRM or booking
  system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
