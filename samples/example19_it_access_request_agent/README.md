# IT Access Request Agent with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent that classifies employee
access requests against a sample policy as a staged handoff graph. It is the
same conversation design that the Microsoft Foundry **IT access request agent**
template creates, without that template's tools. It needs no MCP service,
Project connection, or Toolbox, so it runs in any Foundry Project.

The agent does not verify the employee, grant access, or file a ticket. It
captures the system, access level, and justification, reads them back with the
approval path and timing, and says that the request must be filed manually.
Stages that used tools in the original template now carry a plain "no system is
connected" limit.

## When to use this example

Use it to try policy-based classification into three approval paths before you
connect real directory or ticketing tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `greeting` | Greet briefly if the employee has not yet said what they need. |
| `identify_request` | Capture the employee's name, email, the system, and the access level. |
| `classify` | Classify the request as standard, manager approval, or restricted. |
| `standard` | Read back a standard request with the one-business-day timing. |
| `manager_approval` | Capture the manager's email and read back the request with the approval path. |
| `restricted` | Capture system, data, level, duration, and justification for security review. |
| `wrap_up` | Confirm the approval path and timing, and say plainly that no ticket was filed. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Standard (VPN, Slack, Zoom, Microsoft 365, basic SaaS): within one business day.
Manager approval (GitHub repositories, Salesforce, Figma editor seats, Tableau,
shared finance or HR folders): within one business day after approval.
Restricted (production systems, cloud admin consoles, customer PII, financial
systems): three to five business days. Sign-in through myapps.contoso.com.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 19: IT Access Request Agent**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "I need VPN access to work from home." Expect a standard classification and a
  read-back, with no ticket claimed.
- "I need write access to a GitHub repository." Expect a question for your
  manager's email and the approval path.
- "I need read access to the production database." Expect restricted, the
  justification questions, and three to five business days.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The access policy and portal are fictional; there is no directory or ticketing
  system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
