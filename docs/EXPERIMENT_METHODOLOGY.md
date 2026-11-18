# Experiment methodology: `onboarding_redesign_v1`

This document records the hypothesis, metrics, and decision rule **as they
would be pre-registered before looking at results** — the standard
discipline for not p-hacking your own experiment. The analysis code
(`db/experiment.py`) implements exactly this and nothing more.

## Hypothesis

A redesigned onboarding flow increases 7-day activation without harming
early retention.

## Assignment

- Unit of randomization: the **account owner** (`users.role = 'owner'`),
  not the account — assignment happens before any other user on the account
  could exist.
- Method: deterministic hash bucketing —
  `sha256(f"{experiment_name}:{user_id}")`, mod 100, split at 50 — so
  assignment is reproducible from `user_id` alone and requires no stored
  randomization state. See `generator/generate.py::deterministic_variant`.
- Eligibility window: accounts created between `2026-03-01` and
  `2026-04-15` (`EXPERIMENT_START` / `EXPERIMENT_END` in
  `generator/constants.py`). Accounts outside this window are not part of
  the experiment at all.

## Metrics

| Role | Metric | Definition |
|---|---|---|
| **Primary** (the single decision metric) | 7-day activation rate | See `METRIC_DEFINITIONS.md` — reached `completed_key_action` within 7 days of signup |
| **Guardrail** | Week-1 retention | Active (session or event) on any day between signup+1 and signup+7 |

Only one primary metric is pre-specified. The guardrail is read
**directionally** (did it get meaningfully worse?), not as a second
confirmatory hypothesis test — so no multiple-comparison correction is
applied across the two.

## Decision rule (`db/experiment.py::_decide`)

Evaluated in this order:

1. **Sample ratio mismatch (SRM) detected** (chi-square p < 0.001 on the
   observed 50/50 split) → `do_not_decide`. Fix the assignment/logging bug
   before trusting anything else from this experiment.
2. **Guardrail regressed significantly** (p < 0.05, retention *down* in
   treatment) → `do_not_ship`, regardless of the primary result. A
   statistically significant harm overrides a positive primary metric.
3. **Primary metric improved significantly** (p < 0.05, activation *up* in
   treatment) with no significant guardrail harm → `ship_treatment`.
4. Otherwise → `inconclusive`. A non-significant primary result is reported
   as "not enough evidence," never as "confirmed no effect" — that
   conflation is one of the most common experiment-reading mistakes.

## Statistical methods

- **SRM check**: chi-square goodness-of-fit against the expected 50/50
  split (`scipy.stats.chisquare`).
- **Primary/guardrail test**: two-proportion z-test. The test statistic
  uses the **pooled** standard error (standard under the null that the two
  proportions are equal); the 95% confidence interval on the difference
  uses the **unpooled** standard error (standard for a CI on the difference
  itself, since under the alternative the proportions aren't assumed equal).
- **Post-hoc power**: reported for transparency, but framed explicitly as
  what it is — a comparison of the actual sample size to what *would* have
  been required to detect the effect *actually observed*, computed after
  the fact. This is **not** a substitute for a pre-registered power
  analysis, and a non-significant result alongside an "underpowered" flag
  should be read as "inconclusive," not "the treatment doesn't work."
  Computing power from an observed effect and using it to explain away a
  null result is a known statistical pitfall; this codebase states the
  caveat every time the number is shown rather than printing it bare.

## What this experiment deliberately does not do

- No sequential testing / peeking correction — this is a single fixed-horizon
  analysis of the full eligibility window.
- No per-segment subgroup analysis beyond the channel/plan breakdowns
  elsewhere in the dashboard — slicing the experiment itself by subgroup
  post-hoc would reintroduce the multiple-comparisons problem the
  single-primary-metric design is meant to avoid.
- No causal claims beyond the randomized comparison itself (e.g., this
  experiment says nothing about *why* the redesign works, only *whether*
  it moved the primary metric).
