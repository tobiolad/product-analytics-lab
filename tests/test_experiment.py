import pytest
from scipy.stats import chi2_contingency

from experiment import (
    check_sample_ratio_mismatch,
    two_proportion_z_test,
    required_sample_size_per_arm,
    assess_power,
    _decide,
    SRMResult,
    ProportionTestResult,
)


class TestSampleRatioMismatch:
    def test_balanced_split_is_not_flagged(self):
        result = check_sample_ratio_mismatch(502, 498)
        assert result.mismatch_detected is False

    def test_obviously_skewed_split_is_flagged(self):
        result = check_sample_ratio_mismatch(700, 300)
        assert result.mismatch_detected is True
        assert result.p_value < 0.001

    def test_small_natural_imbalance_is_not_flagged(self):
        """Pure sampling noise around 50/50 at a few hundred per arm should not trip SRM."""
        result = check_sample_ratio_mismatch(234, 271)
        assert result.mismatch_detected is False


class TestTwoProportionZTest:
    def test_matches_independent_chi_square_calculation(self):
        """
        Cross-checks against scipy's chi2_contingency on the same 2x2 table --
        a genuinely independent implementation path, not just re-deriving the
        same formula. For a 2-sided test, z^2 should equal the chi-square
        statistic, and the p-values should match closely.
        """
        result = two_proportion_z_test("test_metric", control_successes=50, control_n=200, treatment_successes=80, treatment_n=200)

        table = [[50, 150], [80, 120]]
        chi2, p_chi2, _, _ = chi2_contingency(table, correction=False)

        # z_statistic is rounded to 4dp before being returned (for display), so
        # squaring it reintroduces rounding error -- compare at a tolerance
        # consistent with that rounding, not scipy's full float precision.
        assert result.z_statistic**2 == pytest.approx(chi2, rel=1e-4)
        assert result.p_value == pytest.approx(p_chi2, rel=1e-4)

    def test_rates_and_diff_computed_correctly(self):
        result = two_proportion_z_test("m", control_successes=50, control_n=200, treatment_successes=80, treatment_n=200)
        assert result.control_rate == 0.25
        assert result.treatment_rate == 0.40
        assert result.absolute_diff == 0.15

    def test_clear_effect_is_significant(self):
        result = two_proportion_z_test("m", 50, 200, 80, 200)
        assert result.significant_at_05 is True

    def test_identical_rates_are_not_significant(self):
        result = two_proportion_z_test("m", 100, 400, 100, 400)
        assert result.significant_at_05 is False
        assert result.absolute_diff == 0.0

    def test_relative_lift_is_none_when_baseline_is_zero(self):
        result = two_proportion_z_test("m", 0, 100, 5, 100)
        assert result.relative_lift is None


class TestRequiredSampleSize:
    def test_larger_effect_needs_fewer_samples(self):
        n_small_effect = required_sample_size_per_arm(baseline_rate=0.25, absolute_effect=0.02)
        n_large_effect = required_sample_size_per_arm(baseline_rate=0.25, absolute_effect=0.15)
        assert n_large_effect < n_small_effect

    def test_zero_effect_requires_infinite_sample(self):
        assert required_sample_size_per_arm(baseline_rate=0.25, absolute_effect=0) == float("inf")


class TestDecisionLogic:
    def _primary(self, diff, significant):
        return ProportionTestResult("p", 1, 1, 0.1, 1, 1, 0.1 + diff, diff, None, 0, 0, 0, 0.01 if significant else 0.5, significant)

    def _guardrail(self, diff, significant):
        return ProportionTestResult("g", 1, 1, 0.9, 1, 1, 0.9 + diff, diff, None, 0, 0, 0, 0.01 if significant else 0.5, significant)

    def test_srm_blocks_any_decision(self):
        srm = SRMResult(700, 300, 0.5, 100, 0.0, True)
        decision = _decide(srm, self._primary(0.1, True), self._guardrail(0.0, False))
        assert decision["recommendation"] == "do_not_decide"

    def test_significant_positive_primary_with_safe_guardrail_ships(self):
        srm = SRMResult(250, 250, 0.5, 0, 0.9, False)
        decision = _decide(srm, self._primary(0.1, True), self._guardrail(0.0, False))
        assert decision["recommendation"] == "ship_treatment"

    def test_significant_guardrail_harm_overrides_positive_primary(self):
        srm = SRMResult(250, 250, 0.5, 0, 0.9, False)
        decision = _decide(srm, self._primary(0.1, True), self._guardrail(-0.05, True))
        assert decision["recommendation"] == "do_not_ship"

    def test_nonsignificant_primary_is_inconclusive_not_no_effect(self):
        srm = SRMResult(250, 250, 0.5, 0, 0.9, False)
        decision = _decide(srm, self._primary(0.02, False), self._guardrail(0.0, False))
        assert decision["recommendation"] == "inconclusive"
        assert "not statistically significant" in decision["reasoning"]
