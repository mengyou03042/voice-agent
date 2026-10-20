# New Hire Onboarding Assistant with Handoff

## Conclusion

`agent.json` is a portable, tool-free Voice Agent for a fictional company,
Contoso, that guides a new hire through day one as a staged handoff graph. It is
the same conversation design that the Microsoft Foundry **New hire onboarding
assistant** template creates, without that template's tools. It needs no MCP
service, Project connection, or Toolbox, so it runs in any Foundry Project.

The agent does not search calendars, book the first 1:1, or text contacts. It
names the manager to meet and can note a preferred 1:1 time, which someone must
schedule manually. Stages that used tools in the original template now carry a
plain "no system is connected" limit.

## When to use this example

Use it to try role-based branching and one-item-at-a-time walkthroughs before
you connect real calendar or SMS tools.

## Workflow

| Stage | Purpose |
| --- | --- |
| `welcome` | Welcome the new hire and ask how they are feeling. |
| `confirm_role` | Ask which role they are starting in. |
| `engineering_track` | Walk through laptop setup, GitHub access, the handbook, on-call, and the first task. |
| `sales_track` | Walk through Salesforce access, territory, quota ramp, and the enablement library. |
| `ops_track` | Walk through systems access, team SOPs, and key vendors. |
| `benefits` | Walk through medical, dental, and the 401k one at a time. |
| `wrap_up` | Share the key people to meet this week; any 1:1 request is noted only. |
| `end` | Say a short goodbye and call `end_conversation`. |

Every stage can route to `end` as soon as the caller says goodbye or asks to
stop. Handoffs are silent: no edge carries a `transfer_message`.

Each stage repeats the persona, tone, conversation rules, and the sample facts
because a handoff node's instructions replace the session instructions. Without
the facts in every stage, the agent would invent details.

## Sample data

Contacts: Alex Wilber, engineering tech lead; Megan Bowen, sales manager; Isaiah
Langer, operations manager; Adele Vance, HR people partner; the IT help desk.
Benefits: medical (PPO or HMO), dental, and a 401k with a 4 percent match;
enroll within 30 days.

## Run in the portal

1. Start the portal as described in [portal/README.md](../../portal/README.md).
2. In **Editor**, choose **Load from templates**.
3. Select **Example 24: New Hire Onboarding Assistant**.
4. Choose **Try it now**, then connect in AgentRuntime.

No `shared_mcp` setup is required.

## Try these turns

- "I'm a new software engineer." Expect engineering items one at a time and Alex
  Wilber as the person to meet.
- "What's the 401k match?" Expect 4 percent and the 30-day enrollment window.
- "Can you text me the contacts?" Expect the contacts read out and no claim that
  a text was sent.
- "No thanks, bye." Expect a short goodbye and the session ending.

## Boundaries

- The company, people, and addresses are fictional; there is no calendar or SMS
  system.
- `store` is `false`; enable persistence deliberately if you need it.
- To attach real tools, add them to the stage that needs them and remove that
  stage's capability limit; conversational confirmation is not an authorization
  boundary.
