# Insurance Advisor with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for a fictional insurer,
Pinnacle Insurance Group, that explores coverage and starts an application as a
staged handoff graph. It is the same conversation design that the Microsoft
Foundry **Insurance advisor** template creates, without that template's tools.
It needs no MCP service, Project connection, or Toolbox, so it runs in any
Foundry Project.

The agent does not look up a customer, save an application, book a review call,
or take a payment. It reads the application details and a preferred call time
back and says that a licensed agent will follow up. Stages that used tools in
the original template now carry a plain "no system is connected" limit.

## When to use this example

Use it to try needs assessment, range-only pricing, and application capture
before you connect real CRM, calendar, or payment tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `greeting` | Welcome the caller and find out whether they want coverage or have a claim. |
| `needs_assessment` | Understand the coverage type, what prompted it, and current coverage, one question at a time. |
| `claims_redirect` | Capture the claim basics and give the claims line and hours. |
| `present_options` | Walk through one to three options with typical ranges and honest trade-offs. |
| `wrap_up` | Read back what was captured and the licensed agent's follow-up. |
| `collect_details` | Capture application details and a preferred review time; nothing is saved or booked. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Pinnacle Insurance Group offers homeowners, auto, life, and umbrella insurance.
Typical monthly ranges, never a quote: auto liability $60 to $100; auto full
coverage $120 to $220; homeowners $100 to $200. A licensed agent follows up
within two business days with a binding quote. Claims line 1 800 555 0142,
Monday to Friday, 8 AM to 8 PM Eastern.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 17: Insurance Advisor**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "I just bought a new car and need auto insurance." Expect ranges only, never a
  premium, and application questions one at a time.
- "I need to file a claim on policy 12345." Expect the claims line and hours.
- "Can I pay by card now?" Expect no payment by phone.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The insurer, prices, and phone numbers are fictional; there is no CRM,
  calendar, or payment system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
