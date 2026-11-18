# Event taxonomy

All event names below are the literal strings the generator writes to
`events_raw.event_name` (`generator/constants.py`) — this document describes
what the generator actually emits, not an aspirational schema maintained
separately from the code.

## Onboarding funnel events

Ordered; a user must reach step *N-1* before step *N* is eligible to occur.
`signed_up` is implicit (it fires at account creation and is never missing).

| Event | Required? | Gates activation? | Notes |
|---|---|---|---|
| `signed_up` | Always fires | — | Account creation |
| `completed_profile` | ~76% of signups | No, but gates the next step | |
| `created_first_workspace` | ~54% of signups | No, but gates the next step | |
| `invited_teammate` | ~19% of signups | **No** — optional side-step | Gated on `created_first_workspace`, but doesn't block or require `completed_key_action` |
| `completed_key_action` | ~32% of signups | — (this *is* the activation step) | The product's core "aha" action. Reaching this within 7 days of signup is the definition of "activated" — see `METRIC_DEFINITIONS.md` |

Percentages above are from one generator run with the default seed; see the
Onboarding Funnel page for live numbers.

## Feature-usage events

Fired during `sessions`, independent of the onboarding funnel. A user can use
a feature without having activated, and vice versa.

| Event | What it represents |
|---|---|
| `used_dashboard` | Opened the main dashboard view |
| `used_automation_builder` | Built or edited an automation |
| `used_reporting_export` | Exported a report |
| `used_integration_connect` | Connected a third-party integration |

## Event envelope

Every event (onboarding or feature) carries the same columns — see
`DATA_DICTIONARY.md` for the full `events_raw` schema. The two timestamps
(`event_timestamp` vs `received_at`) and the non-unique `event_id` are
deliberate, not implementation gaps — see "Known data quality issues" there.
