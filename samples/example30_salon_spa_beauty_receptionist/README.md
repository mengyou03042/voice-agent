# Salon and Spa Receptionist with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for a fictional salon, Contoso
Salon and Spa, that answers menu questions and takes appointment requests as a
staged handoff graph. It is the same conversation design that the Microsoft
Foundry **Salon and spa receptionist** template creates, without that template's
tools. It needs no MCP service, Project connection, or Toolbox, so it runs in
any Foundry Project.

The agent does not search a calendar, book an appointment, or text a reminder.
It reads the request back with the price and duration and says that the salon
will confirm it. Stages that used tools in the original template now carry a
plain "no system is connected" limit.

## When to use this example

Use it to try menu-grounded answers, stylist matching, and appointment request
capture before you connect real calendar or SMS tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `greeting` | Greet the caller and find out what they need. |
| `service_inquiry` | Give prices and durations from the sample menu only. |
| `book_appointment` | Capture name, service, stylist, preferred time, and new or existing client. |
| `confirm` | Read back the request with price and duration; nothing is booked or texted. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Contoso Salon and Spa, 25 Contoso Avenue, Seattle, Tuesday to Saturday, 9 AM to
7 PM Pacific. Menu includes a women's haircut and style $65 (60 minutes),
balayage from $180 (3 hours, consultation recommended), and a classic facial $90
(60 minutes). Stylists: Jessica, Marco, Priya, and Lee. Services of $150 or more
need a $50 deposit paid in person.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 30: Salon and Spa Receptionist**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "I'd like a women's haircut with Jessica on Saturday." Expect a read-back with
  $65 and 60 minutes, as a request.
- "How much is balayage?" Expect from $180, 3 hours, and the in-person deposit.
- "I'm unhappy with my last color." Expect a note for the salon manager, read
  back.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The salon, menu, and stylists are fictional; there is no calendar or SMS
  system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
