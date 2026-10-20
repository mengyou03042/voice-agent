# Incident Response Coordinator with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent that triages a reported
incident and classifies its severity as a staged handoff graph. It is the same
conversation design that the Microsoft Foundry **Incident response coordinator**
template creates, without that template's tools. It needs no MCP service,
Project connection, or Toolbox, so it runs in any Foundry Project.

The agent does not page the on-call, text a service owner, or file a ticket. It
reads back the incident summary, gives the bridge line, and says plainly that
the page or ticket must be sent manually. Stages that used tools in the original
template now carry a plain "no system is connected" limit.

## When to use this example

Use it to try calm triage, severity branching, and honest escalation wording
before you connect real paging, SMS, or ticketing tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `greeting` | Open calmly and invite the caller to describe what they see. |
| `triage` | Capture the service, symptoms, impact, start time, and the caller's name and callback number. |
| `classify_severity` | Classify P0 or P1, P2, or not an incident from what was heard. |
| `p0_p1` | Read back the page details for the primary on-call; nothing is sent. |
| `p2` | Read back the ticket and owner notification details; nothing is filed or sent. |
| `not_incident` | Explain why it is not an incident and point to the right channel. |
| `capture_handoff` | Confirm what was captured and what someone must still do manually. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

On-call directory: primary on-call engineer, plus Checkout, Web app, and Data
platform service owners. Incident bridge 425-555-0199. The on-call acknowledges
a P0 or P1 page within 15 minutes; a service owner responds to a P2 within four
business hours. Non-incidents go to the IT help desk, the feature request form,
or the service docs.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 16: Incident Response Coordinator**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "Checkout is down for all customers since 10 minutes ago. I'm Dana." Expect a
  P0 or P1 classification, a read-back, the bridge line, and no claim that
  anyone was paged.
- "The web app is slow for some users." Expect P2 and ticket details read back
  as not yet filed.
- "Can you add a dark mode to the dashboard?" Expect not an incident and a
  pointer to the feature request form.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The directory, services, and phone numbers are fictional; there is no paging,
  SMS, or ticketing system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
