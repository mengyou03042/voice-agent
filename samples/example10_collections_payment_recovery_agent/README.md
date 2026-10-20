# Collections and Payment Recovery with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for an outbound collections
call from a fictional lender, Contoso Financial, as a staged handoff graph. It
is the same conversation design that the Microsoft Foundry **Collections and
payment recovery** template creates, without that template's tools. It needs no
MCP service, Project connection, or Toolbox, so it runs in any Foundry Project.

The agent does not look up the account, take a payment, or text a confirmation.
It verifies the holder against the sample account, reads the chosen arrangement
back, and says that the billing team will contact the holder to process it.
Stages that used tools in the original template now carry a plain "no system is
connected" limit.

## When to use this example

Use it to try identity checks before disclosure, a required disclosure line, and
empathetic hardship handling before you connect real customer record, payment,
or SMS tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `verify` | Confirm the account holder with the sample verification details without reading them aloud. |
| `discuss` | Give the debt-collection disclosure, the balance, and the days past due, and ask whether the holder can pay. |
| `pay` | Offer pay in full or an installment plan, capture the method and start date, and read the arrangement back. |
| `hardship` | Explain the hardship program and capture a commitment for the billing team to approve. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Holder Jordan Lee, account ending 4821, born March 14, 1985, balance $482.16, 47
days past due. Options: pay in full; 3 monthly payments of $160.72 or 6 of
$80.36; or the hardship program, $25 a month for up to 6 months or a 30-day
pause. Written disputes go to Contoso Financial Disputes, 1 Contoso Way,
Redmond, Washington, within 30 days.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 10: Collections and Payment Recovery**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "Yes, this is Jordan Lee. The last four are 4821. I can do three monthly
  payments by debit card starting November 1." Expect the disclosure, a
  read-back, no card details requested, and no text sent.
- "I lost my job last month and can't pay right now." Expect the hardship
  options and a commitment noted for the billing team, never "approved".
- "No, this is his roommate." Expect no mention of the account or the debt.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The account holder, balance, and lender are fictional; there is no customer
  record, payment, or SMS system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
