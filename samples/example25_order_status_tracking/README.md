# Order Status and Tracking with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for a fictional online store,
Contoso Shop, that handles order status, returns, and warranty claims as a
staged handoff graph. It is the same conversation design that the Microsoft
Foundry **Order status and tracking** template creates, without that template's
tools. It needs no MCP service, Project connection, or Toolbox, so it runs in
any Foundry Project.

The agent does not look up an order, comment on a ticket, or text return
details. It gives timelines from the shipping policy, reads return and warranty
details back, and says that they are noted for the returns or warranty team.
Stages that used tools in the original template now carry a plain "no system is
connected" limit.

## When to use this example

Use it to try status, return, and warranty routing with policy-grounded answers
before you connect real order, ticketing, or SMS tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `greeting` | Capture the order number or account name and what the caller needs. |
| `assess` | Give the expected timeline from the shipping facts, or route to a return or warranty claim. |
| `process_return` | Explain the return policy and capture the order, item, and reason as a request. |
| `process_warranty` | Capture the order, item, defect, photos, and a follow-up contact. |
| `confirm` | Confirm the timeline given or the request noted, without claiming it was logged. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Contoso Shop ships within one business day; standard shipping takes 3 to 5
business days, express 1 to 2. Returns within 30 days of delivery, unused, in
original packaging. Refunds within 5 to 7 business days after the return
arrives. One-year limited warranty; claims reviewed in 3 to 5 business days.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 25: Order Status and Tracking**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "Where's my order 10045? I ordered last Monday with standard shipping." Expect
  the 3-to-5-business-day timeline and no invented carrier or date.
- "I want to return a jacket from order 10045, wrong size." Expect the policy, a
  read-back, and a request noted for the returns team.
- "My blender stopped working." Expect a warranty claim noted, never "filed" or
  "approved".
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The store and its policies are fictional; there is no order, ticketing, or SMS
  system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
