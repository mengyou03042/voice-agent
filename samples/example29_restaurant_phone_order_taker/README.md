# Restaurant Phone Order Taker with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for a fictional restaurant,
Contoso Kitchen, that takes phone orders as a staged handoff graph. It is the
same conversation design that the Microsoft Foundry **Restaurant phone order
taker** template creates, without that template's tools. It needs no MCP
service, Project connection, or Toolbox, so it runs in any Foundry Project.

The agent does not submit the order to a kitchen system, take payment, or text a
summary. It reads the order back with the total and timing and says that it is
noted. Stages that used tools in the original template now carry a plain "no
system is connected" limit.

## When to use this example

Use it to try menu-grounded ordering, arithmetic on totals, and zone checks
before you connect real ordering, payment, or SMS tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `greeting` | Find out whether the order is for pickup or delivery. |
| `pickup` | Take the pickup order item by item, asking about allergies. |
| `delivery` | Check the delivery ZIP, minimum, and fee, then take the order. |
| `review` | Read back each item, the total, and the timing; nothing is texted. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Contoso Kitchen, 200 Contoso Avenue, Redmond, daily 11 AM to 10 PM. Menu
includes pepperoni pizza (12 inch $15, 16 inch $19), Pad Thai $13.95, spring
rolls $6.50, and fresh lemonade $3.50. Delivery covers ZIP codes 98052, 98053,
and 98033 with a $15 minimum and a $4.99 fee. Payment at pickup or on delivery
only.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 29: Restaurant Phone Order Taker**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "Pickup. One 16-inch pepperoni and a fresh lemonade." Expect an allergy
  question and a total of $22.50, ready in about 20 minutes.
- "Delivery to 1 Main Street, 98052. Pad Thai, medium, and spring rolls." Expect
  $20.45 plus the $4.99 fee.
- "Delivery to ZIP 98101." Expect outside the zone and a pickup offer.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The restaurant and menu are fictional; there is no ordering, payment, or SMS
  system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
