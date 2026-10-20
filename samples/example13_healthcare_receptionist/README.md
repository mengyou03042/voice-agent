# Healthcare Receptionist with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for a fictional practice,
Greenfield Medical Center, that handles appointment and change requests as a
staged handoff graph. It is the same conversation design that the Microsoft
Foundry **Healthcare receptionist** template creates, without that template's
tools. It needs no MCP service, Project connection, or Toolbox, so it runs in
any Foundry Project.

The agent does not search the practice calendar, book a visit, change an
appointment, or file a request ticket. It collects patient details and preferred
times, reads the request back, and says that the front desk will confirm it. It
gives no medical advice. Stages that used tools in the original template now
carry a plain "no system is connected" limit.

## When to use this example

Use it to try emergency screening, patient-detail capture, and request
read-backs before you connect real calendar, patient record, ticketing, or
messaging tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `greeting` | Find out whether the caller wants a new visit, a change, an office answer, or has an urgent issue. |
| `collect_info` | Capture the patient's full name and date of birth, plus contact details for a new patient. |
| `schedule` | Capture the provider or visit type and a preferred day and time as a request for the front desk. |
| `cancel_reschedule` | Capture the existing appointment and the change, mention the 24-hour policy, and read the request back. |
| `wrap_up` | Recap the request and what to bring, without claiming a booking or a request number. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Greenfield Medical Center, 200 Greenfield Avenue, Redmond, Washington, Monday to
Friday, 8 AM to 5 PM Pacific. Providers: Dr. Maya Patel, general medicine; Dr.
Luis Ortega, pediatrics; Dr. Hannah Kim, internal medicine. Visits are 30
minutes; bring photo ID, an insurance card, and prior records. Cancellations
need 24 hours' notice. Emergencies: 911; after-hours nurse line 425-555-0150.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 13: Healthcare Receptionist**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "I'd like a checkup with Dr. Patel next Wednesday morning." Expect name and
  date-of-birth questions, a read-back of the request, and what to bring.
- "I need to cancel my appointment on Thursday at 10 AM." Expect the 24-hour
  policy and a request noted for the front desk.
- "I have chest pain right now." Expect a direction to call 911 and the nurse
  line, with no medical advice.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The practice, providers, and phone numbers are fictional; there is no
  calendar, patient record, ticketing, or messaging system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
