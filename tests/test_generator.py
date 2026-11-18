import pandas as pd

from generate import generate_all, deterministic_variant, SEED


class TestReproducibility:
    def test_same_seed_produces_identical_accounts(self):
        run1 = generate_all(seed=SEED)
        run2 = generate_all(seed=SEED)
        pd.testing.assert_frame_equal(run1.accounts, run2.accounts)

    def test_same_seed_produces_identical_events(self):
        run1 = generate_all(seed=SEED)
        run2 = generate_all(seed=SEED)
        pd.testing.assert_frame_equal(
            run1.events.sort_values(["user_id", "event_name"]).reset_index(drop=True),
            run2.events.sort_values(["user_id", "event_name"]).reset_index(drop=True),
        )

    def test_different_seed_produces_different_data(self):
        run1 = generate_all(seed=SEED)
        run2 = generate_all(seed=SEED + 1)
        assert not run1.accounts.equals(run2.accounts)


class TestDeterministicAssignment:
    def test_same_user_and_experiment_always_same_variant(self):
        variants = {deterministic_variant("user_123", "exp_a") for _ in range(20)}
        assert len(variants) == 1

    def test_different_users_can_get_different_variants(self):
        variants = {deterministic_variant(f"user_{i}", "exp_a") for i in range(50)}
        assert variants == {"control", "treatment"}

    def test_assignment_is_roughly_balanced(self):
        n = 5000
        treatment_count = sum(1 for i in range(n) if deterministic_variant(f"user_{i}", "exp_a") == "treatment")
        ratio = treatment_count / n
        assert 0.45 < ratio < 0.55

    def test_same_user_different_experiments_can_differ(self):
        """Assignment is per-(user, experiment), not just per-user."""
        results = {deterministic_variant("user_123", f"exp_{i}") for i in range(20)}
        assert len(results) > 1  # extremely unlikely to all collide if the hash is working


class TestGeneratedDataIntegrity:
    def setup_method(self):
        self.data = generate_all()

    def test_every_account_has_at_least_one_user(self):
        account_ids_with_users = set(self.data.users.account_id)
        assert set(self.data.accounts.account_id) <= account_ids_with_users

    def test_every_user_belongs_to_a_real_account(self):
        assert set(self.data.users.account_id) <= set(self.data.accounts.account_id)

    def test_experiment_assignments_only_within_window(self):
        from constants import EXPERIMENT_START, EXPERIMENT_END

        acct_signup = dict(zip(self.data.accounts.account_id, self.data.accounts.signup_date))
        for _, row in self.data.experiment_assignments.iterrows():
            account_id = row.user_id.replace("_u0", "")
            signup = acct_signup[account_id]
            assert EXPERIMENT_START <= signup <= EXPERIMENT_END

    def test_duplicate_events_share_the_same_event_id(self):
        dup_ids = self.data.events.event_id[self.data.events.event_id.duplicated(keep=False)]
        assert len(dup_ids) > 0  # the generator's duplicate-injection actually produced some

    def test_some_events_arrive_late(self):
        late = self.data.events[self.data.events.received_at > self.data.events.event_timestamp]
        assert len(late) > 0
        assert len(late) < len(self.data.events) * 0.1  # late arrival is the exception, not the norm

    def test_some_accounts_missing_acquisition_channel(self):
        assert self.data.accounts.acquisition_channel.isna().sum() > 0
