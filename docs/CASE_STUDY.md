# Case study: Product Analytics & Experimentation Lab

## The problem this demonstrates

Most portfolio "analytics dashboards" plot a few pre-aggregated numbers and
stop there. This project instead builds the full stack a product analytics
team actually depends on: a reproducible data source, a single
source-of-truth metric layer, a statistically rigorous A/B testing engine,
and a read-only API/dashboard on top — with the same rigor (reproducible
generation, deliberate data-quality edge cases, tested metric definitions)
as the companion Ontario Infrastructure and Grant Intelligence projects in
this portfolio.

**All data is synthetic**, generated deterministically from a fixed seed —
see `generator/generate.py` and `docs/DATA_DICTIONARY.md`. No real user data
is used anywhere. Numbers quoted below are the live output of that generator
and will reproduce exactly with `SEED = 42`.

## What was built

- A deterministic synthetic-data generator (2,000 accounts, ~2,400 users,
  ~29,000 sessions, ~20,000 onboarding/feature events) that *bakes in* a
  true underlying effect, a channel-quality hierarchy, and intentional data
  quality issues — duplicate events, late arrivals, missing categorical
  values — the same way a real analytics pipeline has to cope with them.
- A DuckDB analytical schema with a canonical, deduplicated `events` view
  sitting between the deliberately-dirty raw tables and every metric query.
- A metrics layer (`db/metrics.py`) implementing signup trends, activation
  rate, onboarding funnel, DAU/WAU, cohort retention, feature adoption, and
  channel/plan conversion — each with one documented SQL definition, no
  duplicate logic between the API and the dashboard.
- An experimentation engine (`db/experiment.py`) implementing sample-ratio-
  mismatch detection, a two-proportion z-test, and an honestly-caveated
  post-hoc power assessment, driving a pre-specified ship/no-ship decision
  rule — see `docs/EXPERIMENT_METHODOLOGY.md`.
- A FastAPI read-only analytics API and a React + TypeScript dashboard
  (Overview, Onboarding Funnel, Retention, Feature Adoption, Experiment
  Results, Insights) with light/dark themes and a validated, colorblind-safe
  chart palette.
- 60 automated tests across the generator, metrics, experiment engine,
  API, and frontend — including tests that cross-check the z-test against
  an independent `scipy.stats.chi2_contingency` implementation, and a
  hand-crafted 4-account fixture with known-by-construction correct answers
  for every metric.

## What the data actually shows

From one run of the generator (reproducible with `SEED = 42`):

- **29.5% of accounts** (590 of 2,000) activate — reach the core "key
  action" — within 7 days of signup.
- The steepest onboarding drop-off is between "created first workspace"
  and "completed key action": only ~59% of accounts that create a
  workspace go on to activate.
- The `onboarding_redesign_v1` experiment shows a **+11.2 percentage point**
  absolute lift in 7-day activation for treatment vs. control (p = 0.0088,
  statistically significant at α = 0.05), with **no statistically
  significant regression** on the week-1 retention guardrail (p = 0.81).
  Sample ratio mismatch check is clean (p = 0.10). Decision:
  **ship treatment.**
- The experiment's own power assessment flags itself as underpowered to
  reliably detect an effect this small at conventional 80% power — reported
  plainly rather than hidden, because a significant result from an
  underpowered design is still worth scrutinizing, not just celebrating.

## Engineering decisions worth calling out

- **DuckDB over Postgres**: chosen specifically for this project — a
  single-file embedded analytical database needs no server process, which
  keeps local setup to two Python scripts and matches the "experimentation
  lab" framing (a data scientist's local analysis environment, not a
  production OLTP system).
- **One metric definition, three consumers**: every number on the
  dashboard, every number the API serves, and every number the test suite
  checks all trace back to the same function in `db/metrics.py` or
  `db/experiment.py`. There is no second, hand-maintained copy of "how do
  we compute activation rate" anywhere.
- **Deterministic IDs everywhere**: event and session IDs are derived from
  the seeded NumPy `Generator`'s own byte stream (`rng.bytes(...).hex()`),
  not `uuid.uuid4()` — the whole point of a seeded generator is a
  byte-identical rerun, and a single unseeded `uuid4()` call would have
  silently broken that guarantee. Caught by `tests/test_generator.py`'s
  reproducibility test, not by inspection.
- **The 7-day activation window is a choice, not a given** — `time_to_activation`
  deliberately reports the full distribution of time-to-activation
  separately from the 7-day-bounded activation *rate*, because folding
  them into one metric would hide anyone who activates on day 8 or later.

## Honest limitations

- Synthetic data cannot capture the long tail of real user behavior; the
  generator's parametric choices (gamma-distributed delays, fixed channel
  quality multipliers) are a plausible model, not a validated one.
- The experiment is a single fixed-horizon test with no sequential/peeking
  correction, and this portfolio build doesn't layer on subgroup analysis
  — see `docs/EXPERIMENT_METHODOLOGY.md` for what was deliberately left out
  and why.
