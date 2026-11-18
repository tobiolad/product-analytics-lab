# Metric definitions

Every metric here has exactly one implementation, in `db/metrics.py`, tested
against a hand-crafted fixture in `tests/test_metrics.py`. This document is
the prose explanation of those same queries — if the two ever disagree, the
code is correct and this document is stale (file an issue / fix the doc).

## Signup trend (`signup_trend`)

Count of `accounts` by signup date, bucketed by day or ISO week, broken out
by `acquisition_channel` (including `NULL`, shown as "Unknown"). No
denominator — it's a raw count.

## Activation rate (`activation_rate`)

**Activation** = the account owner reached `completed_key_action` within
**7 days** of signup (`ACTIVATION_WINDOW_DAYS` in `generator/constants.py`).

- Denominator is **all signed-up accounts**, including ones with zero
  onboarding events — never just accounts that reached some earlier step.
  Shrinking the denominator to "accounts that got this far" would silently
  inflate the rate.
- Optionally grouped by `acquisition_channel` or `plan_id`.

## Onboarding funnel (`onboarding_funnel`)

For each step in the fixed order (`signed_up` → `completed_profile` →
`created_first_workspace` → `completed_key_action`):

- `pct_of_signups` — this step's count ÷ **total signups** (a constant
  denominator across all steps, not the previous step's count)
- `pct_of_previous_step` — this step's count ÷ the **previous** step's count
  (classic funnel drop-off reading)

`invited_teammate` is reported separately, flagged as optional and
non-gating — it is never on the critical path to activation, so folding it
into the ordered funnel would misrepresent it as a required step.

## Time to activation (`time_to_activation`)

Median / mean / 90th-percentile days-to-activation, computed over **every
account that ever reached `completed_key_action`** — not filtered to the
7-day activation-rate window. Filtering to `activated_within_7d` here would
truncate the distribution at exactly 7 by construction (nothing could ever
show as taking longer than the window), hiding the slower-activating tail
this metric exists to surface. "Activation rate" (7-day-bounded) and "time to
activation" (unbounded distribution) are deliberately two different
denominators answering two different questions.

## DAU / WAU (`dau_wau`)

- **DAU**: distinct users with ≥1 session **or** ≥1 event on a calendar day.
  Sessions are included (not just events) because a session with no
  feature-usage event inside it still represents real product usage.
- **WAU**: distinct users active on ≥1 day within the ISO week. Each day's
  row shows that day's DAU alongside its week's WAU for direct comparison.

## Cohort retention (`cohort_retention`)

Weekly signup cohorts. `retention[cohort_week][week_number]` = % of that
cohort's accounts with ≥1 active day (session or event) in
`cohort_week + week_number` weeks. Week 0 is always 100% by construction
(the signup itself counts as activity) — included anyway for a complete,
honest matrix rather than hidden.

## Feature adoption (`feature_adoption`)

Two adoption rates per feature, both reported:

- `adoption_rate_all_accounts` — adopting accounts ÷ **all** accounts
  (answers "adoption across the whole base")
- `adoption_rate_among_activated` — adopting accounts ÷ **activated**
  accounts only (the more typical PLG framing: "once someone's activated,
  do they use this?")

## Conversion by channel and plan (`conversion_by_channel_and_plan`)

"Conversion" here means **signed up on a paid plan** (`starter` / `pro` /
`enterprise`) at the moment of signup. This dataset does not model later
plan upgrades, so this is a same-session plan-choice rate, not a full
upgrade-funnel metric — don't read it as "% of free users who eventually
convert."
