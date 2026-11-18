"""
Experimentation engine: deterministic assignment is already baked into the
generated data (generator/generate.py:deterministic_variant); this module
is the ANALYSIS side -- sample ratio mismatch, effect size, significance,
power -- for the "onboarding_redesign_v1" experiment.

See docs/EXPERIMENT_METHODOLOGY.md for the hypothesis, metrics, and
decision criteria agreed *before* looking at results.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

import duckdb
import numpy as np
from scipy import stats


@dataclass
class SRMResult:
    control_n: int
    treatment_n: int
    expected_ratio: float
    chi2_statistic: float
    p_value: float
    mismatch_detected: bool  # True if p_value < 0.001 -- a strict threshold, since false alarms here are costly


@dataclass
class ProportionTestResult:
    metric_name: str
    control_n: int
    control_successes: int
    control_rate: float
    treatment_n: int
    treatment_successes: int
    treatment_rate: float
    absolute_diff: float
    relative_lift: Optional[float]
    ci_95_low: float
    ci_95_high: float
    z_statistic: float
    p_value: float
    significant_at_05: bool


@dataclass
class PowerAssessment:
    observed_effect_size: float
    required_n_per_arm_for_observed_effect: int
    actual_n_per_arm: int
    adequately_powered_for_observed_effect: bool
    note: str


def check_sample_ratio_mismatch(control_n: int, treatment_n: int, expected_ratio: float = 0.5) -> SRMResult:
    total = control_n + treatment_n
    expected_control = total * expected_ratio
    expected_treatment = total * (1 - expected_ratio)
    chi2, p_value = stats.chisquare(f_obs=[control_n, treatment_n], f_exp=[expected_control, expected_treatment])
    return SRMResult(
        control_n=control_n,
        treatment_n=treatment_n,
        expected_ratio=expected_ratio,
        chi2_statistic=round(float(chi2), 4),
        p_value=round(float(p_value), 6),
        mismatch_detected=bool(p_value < 0.001),
    )


def two_proportion_z_test(
    metric_name: str, control_successes: int, control_n: int, treatment_successes: int, treatment_n: int
) -> ProportionTestResult:
    """
    Standard unpooled-variance two-proportion z-test with a normal-approximation
    95% CI on the difference (treatment - control). Not pooled for the CI
    (unpooled is more standard for the CI on the difference itself), pooled
    for the test statistic under H0 (standard practice: pool under the null
    that the two proportions are equal).
    """
    p1 = control_successes / control_n
    p2 = treatment_successes / treatment_n
    diff = p2 - p1

    pooled_p = (control_successes + treatment_successes) / (control_n + treatment_n)
    se_pooled = np.sqrt(pooled_p * (1 - pooled_p) * (1 / control_n + 1 / treatment_n))
    z = diff / se_pooled if se_pooled > 0 else 0.0
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))

    se_unpooled = np.sqrt(p1 * (1 - p1) / control_n + p2 * (1 - p2) / treatment_n)
    ci_low = diff - 1.96 * se_unpooled
    ci_high = diff + 1.96 * se_unpooled

    relative_lift = (diff / p1) if p1 > 0 else None

    return ProportionTestResult(
        metric_name=metric_name,
        control_n=control_n,
        control_successes=control_successes,
        control_rate=round(p1, 4),
        treatment_n=treatment_n,
        treatment_successes=treatment_successes,
        treatment_rate=round(p2, 4),
        absolute_diff=round(diff, 4),
        relative_lift=round(relative_lift, 4) if relative_lift is not None else None,
        ci_95_low=round(ci_low, 4),
        ci_95_high=round(ci_high, 4),
        z_statistic=round(float(z), 4),
        p_value=round(float(p_value), 6),
        significant_at_05=bool(p_value < 0.05),
    )


def required_sample_size_per_arm(baseline_rate: float, absolute_effect: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Standard two-proportion sample size formula (Wald, equal-size arms)."""
    if absolute_effect == 0:
        return float("inf")
    p1 = baseline_rate
    p2 = baseline_rate + absolute_effect
    p_bar = (p1 + p2) / 2
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)
    numerator = (z_alpha * np.sqrt(2 * p_bar * (1 - p_bar)) + z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    n = numerator / (absolute_effect**2)
    return int(np.ceil(n))


def assess_power(control_rate: float, treatment_rate: float, actual_n_per_arm: int) -> PowerAssessment:
    """
    Post-hoc power framing is easy to misuse (computing power from the
    observed effect and calling an experiment "underpowered" after the fact
    is a known statistical pitfall -- it tends to rubber-stamp null results).
    This reports the comparison plainly and says so, rather than presenting
    a single "power = X%" number as if it settles anything.
    """
    observed_effect = treatment_rate - control_rate
    required_n = required_sample_size_per_arm(control_rate, observed_effect) if observed_effect != 0 else float("inf")
    adequately_powered = actual_n_per_arm >= required_n if required_n != float("inf") else False
    return PowerAssessment(
        observed_effect_size=round(observed_effect, 4),
        required_n_per_arm_for_observed_effect=int(required_n) if required_n != float("inf") else -1,
        actual_n_per_arm=actual_n_per_arm,
        adequately_powered_for_observed_effect=adequately_powered,
        note=(
            "This compares actual sample size to what WOULD have been required to reliably detect the effect "
            "size actually observed -- a post-hoc calculation, not the pre-registered power analysis a real "
            "experiment should run BEFORE collecting data. It describes this specific result's statistical "
            "precision; it is not evidence the experiment was well- or poorly-designed."
        ),
    )


def get_experiment_outcomes(con: duckdb.DuckDBPyConnection, experiment_name: str):
    """Per-user variant + primary metric (7d activation) + guardrail metric (week-1 retention)."""
    return con.execute(
        """
        WITH assignment AS (
            SELECT user_id, variant, split_part(user_id, '_u0', 1) AS account_id
            FROM experiment_assignments
            WHERE experiment_name = ?
        ),
        activity AS (
            SELECT user_id, CAST(started_at AS DATE) AS active_date FROM sessions
            UNION
            SELECT user_id, CAST(event_timestamp AS DATE) AS active_date FROM events
        ),
        week1_retention AS (
            SELECT a.user_id, a.account_id,
                   MAX(CASE WHEN act.active_date BETWEEN acct.signup_date + 1 AND acct.signup_date + 7 THEN 1 ELSE 0 END) AS retained_week1
            FROM assignment a
            JOIN accounts acct ON acct.account_id = a.account_id
            LEFT JOIN activity act ON act.user_id = a.user_id
            GROUP BY 1, 2
        )
        SELECT
            a.user_id, a.variant,
            aa.activated_within_7d,
            COALESCE(w.retained_week1, 0) AS retained_week1
        FROM assignment a
        JOIN account_activation aa ON aa.account_id = a.account_id
        LEFT JOIN week1_retention w ON w.user_id = a.user_id
        """,
        [experiment_name],
    ).df()


def run_experiment_analysis(con: duckdb.DuckDBPyConnection, experiment_name: str) -> dict:
    df = get_experiment_outcomes(con, experiment_name)
    control = df[df.variant == "control"]
    treatment = df[df.variant == "treatment"]

    srm = check_sample_ratio_mismatch(len(control), len(treatment))

    primary = two_proportion_z_test(
        "activation_rate_7d",
        int(control.activated_within_7d.sum()),
        len(control),
        int(treatment.activated_within_7d.sum()),
        len(treatment),
    )
    guardrail = two_proportion_z_test(
        "week1_retention",
        int(control.retained_week1.sum()),
        len(control),
        int(treatment.retained_week1.sum()),
        len(treatment),
    )

    power = assess_power(primary.control_rate, primary.treatment_rate, min(len(control), len(treatment)))

    warnings = []
    if srm.mismatch_detected:
        warnings.append("Sample ratio mismatch detected -- results below should not be trusted until this is investigated.")
    if not power.adequately_powered_for_observed_effect:
        warnings.append(
            "This sample size would be underpowered to reliably detect an effect this small at 80% power -- "
            "a non-significant result here does not confirm no effect exists."
        )
    warnings.append(
        "Two metrics were tested (primary + guardrail). No multiple-comparison correction was applied to the "
        "primary metric since it was pre-specified as the single decision metric; the guardrail is interpreted "
        "directionally (did it get meaningfully worse), not as a second confirmatory test."
    )

    decision = _decide(srm, primary, guardrail)

    return {
        "experiment_name": experiment_name,
        "srm": asdict(srm),
        "primary_metric": asdict(primary),
        "guardrail_metric": asdict(guardrail),
        "power_assessment": asdict(power),
        "warnings": warnings,
        "decision": decision,
    }


def _decide(srm: SRMResult, primary: ProportionTestResult, guardrail: ProportionTestResult) -> dict:
    if srm.mismatch_detected:
        return {"recommendation": "do_not_decide", "reasoning": "Sample ratio mismatch detected; fix the assignment/logging issue before trusting any metric from this experiment."}

    guardrail_harmed = guardrail.significant_at_05 and guardrail.absolute_diff < 0
    if primary.significant_at_05 and primary.absolute_diff > 0 and not guardrail_harmed:
        return {
            "recommendation": "ship_treatment",
            "reasoning": f"Primary metric improved by {primary.absolute_diff:+.1%} (p={primary.p_value:.4f}) with no statistically significant harm to the guardrail metric.",
        }
    if guardrail_harmed:
        return {
            "recommendation": "do_not_ship",
            "reasoning": f"Guardrail metric (week-1 retention) moved by {guardrail.absolute_diff:+.1%} (p={guardrail.p_value:.4f}), a statistically significant regression -- this overrides a positive primary-metric result.",
        }
    if not primary.significant_at_05:
        return {
            "recommendation": "inconclusive",
            "reasoning": f"Primary metric difference ({primary.absolute_diff:+.1%}) is not statistically significant at p<0.05 (p={primary.p_value:.4f}). Do not conclude the treatment has no effect -- see the power assessment.",
        }
    return {"recommendation": "inconclusive", "reasoning": "Results do not meet a clear ship/no-ship threshold; review manually."}
