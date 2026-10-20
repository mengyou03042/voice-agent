# Hotel Reservations with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for a fictional hotel, the
Grand Hotel, that takes reservation requests and answers guest questions as a
staged handoff graph. It is the same definition that the Microsoft Foundry
**Hotel reservations** template creates. It needs no MCP service, Project
connection, or Toolbox, so it runs in any Foundry Project.

The source template uses no tools, so nothing is removed. The agent quotes
sample rates, reads each request back, and says that the front desk will confirm
it; it never says a room is booked, held, or cancelled.

## When to use this example

Use it to try request routing, rate arithmetic from sample facts, and policy
answers before you connect real reservation, guest record, or mail tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `welcome` | Find out whether the caller wants a new stay, a change or cancellation, or hotel information. |
| `new_booking` | Match rooms to dates and guests, quote rates before taxes, and read the request back. |
| `manage_existing` | Capture the reservation and the change or cancellation, state the policy, and read it back. |
| `general_inquiry` | Answer amenity, dining, parking, check-in, and pet questions from the sample facts. |
| `wrap_up` | Recap the request noted for the front desk or the question answered. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

The Grand Hotel, 100 Example Avenue, Seattle. Check-in from 3 PM, check-out by
11 AM. Classic King $229, Deluxe Double Queen $259, Junior Suite $349 a night
before taxes. Free cancellation until 48 hours before arrival. Valet parking
only, $45 a night; dogs up to 25 kg, $75 a stay.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 14: Hotel Reservations**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "I'd like a room for two nights from Friday, two adults, it's our
  anniversary." Expect matching rooms, a total such as $458 for a Classic King,
  and a request noted for the front desk.
- "Cancel my reservation, confirmation A1B2C3, last name Test." Expect the
  48-hour policy and no claim that it was cancelled.
- "Can I bring my dog, and how does parking work?" Expect the pet fee and
  valet-only parking.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The hotel, rates, and policies are fictional; there is no reservation, guest
  record, or mail system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
