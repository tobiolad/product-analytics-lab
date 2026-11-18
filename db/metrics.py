"""
Product analytics metrics, each a single documented SQL query against the
canonical `events`/`account_activation` views. See
docs/METRIC_DEFINITIONS.md for the prose definition of every metric here --
these functions are its executable form, not a separate reimplementation.

All functions take a duckdb connection and return a pandas DataFrame.
"""
from __future__ import annotations

import duckdb


def signup_trend(con: duckdb.DuckDBPyConnection, granularity: str = "week"):
    if granularity not in ("day", "week"):
        raise ValueError("granularity must be 'day' or 'week'")
    bucket_expr = "date_trunc('week', signup_date)" if granularity == "week" else "signup_date"
    return con.execute(
        f"""
        SELECT {bucket_expr} AS period, acquisition_channel, COUNT(*) AS signups
        FROM accounts
        GROUP BY 1, 2
        ORDER BY 1, 2
        """
    ).df()


def activation_rate(con: duckdb.DuckDBPyConnection, by: str | None = None):
    """
    Activation rate = fraction of accounts whose owner reached the
    'completed_key_action' onboarding step within 7 days of signup.
    Denominator is ALL signed-up accounts (including those with zero
    onboarding events), never just accounts that reached some earlier step
    -- that would silently shrink the denominator and inflate the rate.
    """
    group_col = f", {by}" if by else ""
    group_by = "GROUP BY 1" if by else ""
    select_by = f"{by}," if by else ""
    return con.execute(
        f"""
        SELECT {select_by}
            COUNT(*) AS total_accounts,
            SUM(CASE WHEN activated_within_7d THEN 1 ELSE 0 END) AS activated_accounts,
            ROUND(AVG(CASE WHEN activated_within_7d THEN 1.0 ELSE 0.0 END), 4) AS activation_rate
        FROM account_activation
        {group_by}
        ORDER BY {by if by else '1'}
        """
    ).df()


def onboarding_funnel(con: duckdb.DuckDBPyConnection):
    """
    Each step's denominator is the total signed-up account count (not the
    previous step's count) for "pct_of_signups", PLUS a separate
    "pct_of_previous_step" column for classic funnel drop-off reading.
    Step order is fixed and matches generator/constants.py ONBOARDING_STEPS
    (excluding the optional 'invited_teammate' side-step, reported
    separately since it doesn't gate activation).
    """
    steps = ["signed_up", "completed_profile", "created_first_workspace", "completed_key_action"]
    total = con.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]

    rows = []
    prev_count = total
    for step in steps:
        count = con.execute(
            "SELECT COUNT(DISTINCT account_id) FROM onboarding_progress WHERE step = ?", [step]
        ).fetchone()[0]
        rows.append(
            {
                "step": step,
                "accounts_reached": count,
                "pct_of_signups": round(count / total, 4) if total else None,
                "pct_of_previous_step": round(count / prev_count, 4) if prev_count else None,
            }
        )
        prev_count = count

    invited = con.execute(
        "SELECT COUNT(DISTINCT account_id) FROM onboarding_progress WHERE step = 'invited_teammate'"
    ).fetchone()[0]
    rows.append({"step": "invited_teammate (optional, not gating)", "accounts_reached": invited, "pct_of_signups": round(invited / total, 4), "pct_of_previous_step": None})

    import pandas as pd

    return pd.DataFrame(rows)


def dau_wau(con: duckdb.DuckDBPyConnection):
    """
    DAU = distinct users with >=1 session OR >=1 event on a calendar day.
    WAU = distinct users active on >=1 day within the ISO week.
    Uses sessions (not just events) because a session with no feature event
    still represents real product usage.
    """
    return con.execute(
        """
        WITH activity AS (
            SELECT user_id, CAST(started_at AS DATE) AS active_date FROM sessions
            UNION
            SELECT user_id, CAST(event_timestamp AS DATE) AS active_date FROM events
        ),
        daily AS (
            SELECT active_date, COUNT(DISTINCT user_id) AS dau FROM activity GROUP BY 1
        ),
        weekly AS (
            SELECT date_trunc('week', active_date) AS week, COUNT(DISTINCT user_id) AS wau
            FROM activity GROUP BY 1
        )
        SELECT d.active_date AS date, d.dau, w.wau
        FROM daily d
        JOIN weekly w ON date_trunc('week', d.active_date) = w.week
        ORDER BY d.active_date
        """
    ).df()


def cohort_retention(con: duckdb.DuckDBPyConnection, max_weeks: int = 6):
    """
    Weekly signup cohorts. retention[cohort_week][n] = % of that cohort's
    accounts with >=1 active day in signup-week-of-cohort + n. Week 0 is
    always 100% by construction (the signup itself counts as activity) --
    included anyway for a complete, honest matrix rather than hidden.
    """
    return con.execute(
        f"""
        WITH activity AS (
            SELECT user_id, CAST(started_at AS DATE) AS active_date FROM sessions
            UNION
            SELECT user_id, CAST(event_timestamp AS DATE) AS active_date FROM events
        ),
        user_account AS (
            SELECT user_id, account_id FROM users
        ),
        cohorts AS (
            SELECT account_id, date_trunc('week', signup_date) AS cohort_week
            FROM accounts
        ),
        user_activity_weeks AS (
            SELECT
                c.account_id,
                c.cohort_week,
                CAST(date_diff('day', c.cohort_week, date_trunc('week', a.active_date)) / 7 AS INTEGER) AS week_number
            FROM activity a
            JOIN user_account ua ON ua.user_id = a.user_id
            JOIN cohorts c ON c.account_id = ua.account_id
            WHERE date_diff('day', c.cohort_week, date_trunc('week', a.active_date)) >= 0
        ),
        cohort_sizes AS (
            SELECT cohort_week, COUNT(*) AS cohort_size FROM cohorts GROUP BY 1
        )
        SELECT
            uaw.cohort_week,
            cs.cohort_size,
            uaw.week_number,
            COUNT(DISTINCT uaw.account_id) AS retained_accounts,
            ROUND(COUNT(DISTINCT uaw.account_id) * 1.0 / cs.cohort_size, 4) AS retention_rate
        FROM user_activity_weeks uaw
        JOIN cohort_sizes cs ON cs.cohort_week = uaw.cohort_week
        WHERE uaw.week_number BETWEEN 0 AND {max_weeks}
        GROUP BY 1, 2, 3
        ORDER BY 1, 3
        """
    ).df()


def feature_adoption(con: duckdb.DuckDBPyConnection):
    """
    Adoption rate denominator is ALL accounts (not just activated ones), so
    the headline number answers "adoption across the whole base." A second
    column gives adoption-among-activated for the more typical PLG framing.
    """
    return con.execute(
        """
        WITH total AS (SELECT COUNT(*) AS n FROM accounts),
        activated AS (SELECT COUNT(*) AS n FROM account_activation WHERE activated_within_7d)
        SELECT
            e.event_name AS feature,
            COUNT(DISTINCT e.account_id) AS adopting_accounts,
            ROUND(COUNT(DISTINCT e.account_id) * 1.0 / (SELECT n FROM total), 4) AS adoption_rate_all_accounts,
            ROUND(
                COUNT(DISTINCT e.account_id) FILTER (WHERE aa.activated_within_7d) * 1.0
                / NULLIF((SELECT n FROM activated), 0),
                4
            ) AS adoption_rate_among_activated
        FROM events e
        LEFT JOIN account_activation aa ON aa.account_id = e.account_id
        WHERE e.event_name LIKE 'used_%'
        GROUP BY 1
        ORDER BY 2 DESC
        """
    ).df()


def time_to_activation(con: duckdb.DuckDBPyConnection):
    """
    Distribution is over accounts that EVER reached completed_key_action --
    not restricted to activated_within_7d. Filtering to within-7d would
    truncate the distribution at exactly 7 by construction (median/p90
    could never exceed the window), hiding the slower-activating tail that
    this metric exists to show. "Activation rate" (the 7d-bounded version)
    and "time to activation" (the full distribution) are deliberately two
    different denominators -- see docs/METRIC_DEFINITIONS.md.
    """
    return con.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE days_to_activation IS NOT NULL) AS activated_accounts,
            ROUND(MEDIAN(days_to_activation), 2) AS median_days,
            ROUND(AVG(days_to_activation), 2) AS mean_days,
            ROUND(QUANTILE_CONT(days_to_activation, 0.90), 2) AS p90_days
        FROM account_activation
        """
    ).df()


def conversion_by_channel_and_plan(con: duckdb.DuckDBPyConnection):
    """
    'Conversion' here = signed up on a paid plan (starter/pro/enterprise)
    at time of signup. This dataset doesn't model later upgrades, so this
    is a same-session plan-choice conversion rate, not a full upgrade-funnel
    metric -- documented explicitly in docs/METRIC_DEFINITIONS.md.
    """
    return con.execute(
        """
        SELECT
            acquisition_channel,
            plan_id,
            COUNT(*) AS accounts,
            ROUND(COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (PARTITION BY acquisition_channel), 4) AS pct_within_channel
        FROM accounts
        GROUP BY 1, 2
        ORDER BY 1, 2
        """
    ).df()
