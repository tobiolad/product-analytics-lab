from pathlib import Path

import duckdb
import pytest

import metrics

SQL_DIR = Path(__file__).resolve().parent.parent / "db" / "sql"


@pytest.fixture
def con():
    """
    A small, hand-crafted dataset where the correct answer to every metric
    is known in advance -- not a sample of the generated data, which would
    make the test circular (checking the code against itself).

    4 accounts:
      acct_1 (channel A): reaches completed_key_action on day 3  -> activated within 7d
      acct_2 (channel A): reaches created_first_workspace only, never activates
      acct_3 (channel B): reaches completed_key_action on day 10 -> activated, but NOT within 7d
      acct_4 (channel B): no onboarding events at all (never even "signed_up" logged beyond account creation)
    """
    c = duckdb.connect(":memory:")
    c.execute((SQL_DIR / "001_schema.sql").read_text())
    c.execute((SQL_DIR / "002_views.sql").read_text())

    c.execute(
        """
        INSERT INTO accounts VALUES
            ('acct_1', '2026-01-01', 'channel_a', 'free'),
            ('acct_2', '2026-01-01', 'channel_a', 'free'),
            ('acct_3', '2026-01-01', 'channel_b', 'free'),
            ('acct_4', '2026-01-01', 'channel_b', 'free')
        """
    )
    c.execute(
        """
        INSERT INTO users VALUES
            ('acct_1_u0', 'acct_1', 'owner', '2026-01-01'),
            ('acct_2_u0', 'acct_2', 'owner', '2026-01-01'),
            ('acct_3_u0', 'acct_3', 'owner', '2026-01-01'),
            ('acct_4_u0', 'acct_4', 'owner', '2026-01-01')
        """
    )
    c.execute(
        """
        INSERT INTO events_raw (event_id, user_id, account_id, session_id, event_name, event_timestamp, received_at) VALUES
            ('e1', 'acct_1_u0', 'acct_1', NULL, 'signed_up',               '2026-01-01', '2026-01-01'),
            ('e2', 'acct_1_u0', 'acct_1', NULL, 'completed_profile',       '2026-01-01', '2026-01-01'),
            ('e3', 'acct_1_u0', 'acct_1', NULL, 'created_first_workspace', '2026-01-02', '2026-01-02'),
            ('e4', 'acct_1_u0', 'acct_1', NULL, 'completed_key_action',    '2026-01-04', '2026-01-04'),

            ('e5', 'acct_2_u0', 'acct_2', NULL, 'signed_up',               '2026-01-01', '2026-01-01'),
            ('e6', 'acct_2_u0', 'acct_2', NULL, 'completed_profile',       '2026-01-01', '2026-01-01'),
            ('e7', 'acct_2_u0', 'acct_2', NULL, 'created_first_workspace', '2026-01-02', '2026-01-02'),

            ('e8', 'acct_3_u0', 'acct_3', NULL, 'signed_up',               '2026-01-01', '2026-01-01'),
            ('e9', 'acct_3_u0', 'acct_3', NULL, 'completed_profile',       '2026-01-01', '2026-01-01'),
            ('e10','acct_3_u0', 'acct_3', NULL, 'created_first_workspace', '2026-01-02', '2026-01-02'),
            ('e11','acct_3_u0', 'acct_3', NULL, 'completed_key_action',    '2026-01-11', '2026-01-11')
        """
    )
    c.execute("INSERT INTO sessions VALUES ('sess_1', 'acct_1_u0', 'acct_1', '2026-01-01 10:00:00', '2026-01-01 10:10:00')")
    return c


class TestActivationRate:
    def test_overall_rate_matches_hand_count(self, con):
        """2 of 4 accounts ever reach completed_key_action, but only acct_1 (day 3) is within 7 days -- acct_3's day 10 doesn't count toward this metric."""
        result = metrics.activation_rate(con)
        row = result.iloc[0]
        assert row.total_accounts == 4
        assert row.activated_accounts == 1
        assert row.activation_rate == 0.25

    def test_grouped_by_channel(self, con):
        result = metrics.activation_rate(con, by="acquisition_channel").set_index("acquisition_channel")
        # channel_a: acct_1 activated, acct_2 not -> 1/2
        assert result.loc["channel_a", "activation_rate"] == 0.5
        # channel_b: acct_3 activated at day 10 (outside window), acct_4 never -> 0/2
        assert result.loc["channel_b", "activation_rate"] == 0.0


class TestOnboardingFunnel:
    def test_step_counts_match_hand_count(self, con):
        funnel = metrics.onboarding_funnel(con).set_index("step")
        assert funnel.loc["signed_up", "accounts_reached"] == 3  # all 4 accounts exist, but acct_4 never logged any event, including signed_up
        assert funnel.loc["completed_profile", "accounts_reached"] == 3
        assert funnel.loc["created_first_workspace", "accounts_reached"] == 3
        assert funnel.loc["completed_key_action", "accounts_reached"] == 2  # acct_1 and acct_3 (ever, not just within-7d)

    def test_pct_of_previous_step_is_a_real_ratio(self, con):
        funnel = metrics.onboarding_funnel(con).set_index("step")
        # 3 of 4 "signed_up" (per the known limitation that acct_4 never logged the event) reached completed_profile
        expected = 3 / funnel.loc["signed_up", "accounts_reached"]
        assert funnel.loc["completed_profile", "pct_of_previous_step"] == pytest.approx(expected, rel=1e-6)


class TestTimeToActivation:
    def test_median_and_mean_over_the_two_activated_accounts(self, con):
        """
        Note: time_to_activation (like the rest of account_activation) is
        computed over days_to_activation regardless of the 7-day window --
        acct_3's day-10 activation DOES count here, since this metric
        describes "how long did it take, among those who ever activated,"
        not the 7-day activation-rate population.
        """
        result = metrics.time_to_activation(con).iloc[0]
        assert result.activated_accounts == 2
        assert result.median_days == pytest.approx(6.5)  # median of [3, 10]
        assert result.mean_days == pytest.approx(6.5)
