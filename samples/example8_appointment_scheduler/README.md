# Appointment Scheduler with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for a fictional clinic,
Contoso Wellness Clinic, that handles new, reschedule, and cancel requests as a
staged handoff graph. It is the same conversation design that the Microsoft
Foundry **Appointment scheduler** template creates, without that template's
tools. It needs no MCP service, Project connection, or Toolbox, so it runs in
any Foundry Project.

The agent does not search a calendar, book, move, or cancel an appointment, or
send a confirmation email. It collects the service, preferred times, and contact
details, reads the request back, and says that the clinic will confirm it.
Stages that used tools in the original template now carry a plain "no system is
connected" limit.

## When to use this example

Use it to try intent routing between booking and change requests,
one-question-at-a-time data capture, and honest read-backs before you connect
real calendar, customer record, or mail tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `greeting` | Find out whether the caller wants to book, reschedule, or cancel, and hand off right away. |
| `collect_info` | Capture name, email for the confirmation, and the service, one question at a time. |
| `new_booking` | Collect a preferred day, time, and timezone, and explain that the clinic confirms the slot. |
| `change_cancel` | Capture the existing appointment details and the requested change; nothing is looked up or changed. |
| `confirm` | Read back the service, preferred time, and contact details as a request, plus any prep. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Contoso Wellness Clinic offers an initial consultation (60 minutes), a follow-up
visit (30 minutes), and a nutrition check-in (30 minutes). Visits are Microsoft
Teams video calls, Monday to Friday, 9 AM to 5 PM in the caller's timezone. For
an initial consultation, bring a list of current medications and questions.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 8: Appointment Scheduler**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "I'd like to book an initial consultation, Thursday afternoon, Pacific time."
  Expect name and email questions, a read-back that mentions the medication-list
  prep, and no claim that anything was booked.
- "I need to move my follow-up visit to next week." Expect the old and new times
  read back as a request for the clinic to confirm.
- "Please cancel my nutrition check-in on Friday." Expect no new times offered
  and no claim that it was cancelled.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The clinic, services, and hours are fictional; there is no calendar, patient
  record, or mail system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
