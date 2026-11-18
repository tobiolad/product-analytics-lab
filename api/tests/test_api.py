"""
Exercises the API against the real built database (generator/generate.py +
db/load.py must have been run first -- same as any consumer of this API).
These are integration tests of the HTTP layer and response shapes; the
underlying metric correctness is covered by db/tests/test_metrics.py and
db/tests/test_experiment.py against a known hand-crafted fixture.
"""
import pytest
from fastapi.testclient import TestClient

from app.db import DB_PATH, EXPERIMENT_NAME
from app.main import app

pytestmark = pytest.mark.skipif(
    not DB_PATH.exists(), reason="db/analytics.duckdb not built -- run generator/generate.py then db/load.py first"
)

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


class TestOverview:
    def test_signup_trend_week(self):
        resp = client.get("/overview/signup-trend")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) > 0
        assert {"period", "acquisition_channel", "signups"} <= body[0].keys()

    def test_signup_trend_rejects_bad_granularity(self):
        resp = client.get("/overview/signup-trend", params={"granularity": "month"})
        assert resp.status_code == 422

    def test_activation_rate_overall(self):
        resp = client.get("/overview/activation-rate")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["total_accounts"] > 0
        assert 0 <= body[0]["activation_rate"] <= 1

    def test_activation_rate_grouped_by_channel(self):
        resp = client.get("/overview/activation-rate", params={"by": "acquisition_channel"})
        assert resp.status_code == 200
        assert len(resp.json()) > 1

    def test_activation_rate_rejects_unlisted_column(self):
        """`by` is interpolated into SQL in metrics.activation_rate, so the API must
        reject anything outside the allowlist rather than pass it through."""
        resp = client.get("/overview/activation-rate", params={"by": "account_id; DROP TABLE accounts"})
        assert resp.status_code == 400

    def test_dau_wau(self):
        resp = client.get("/overview/dau-wau")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) > 0
        assert {"date", "dau", "wau"} <= body[0].keys()

    def test_conversion(self):
        resp = client.get("/overview/conversion")
        assert resp.status_code == 200
        assert len(resp.json()) > 0


class TestFunnel:
    def test_onboarding_funnel_has_all_steps_in_order(self):
        resp = client.get("/funnel/onboarding")
        assert resp.status_code == 200
        steps = [row["step"] for row in resp.json()]
        assert steps[:4] == ["signed_up", "completed_profile", "created_first_workspace", "completed_key_action"]

    def test_time_to_activation_shape(self):
        resp = client.get("/funnel/time-to-activation")
        assert resp.status_code == 200
        body = resp.json()
        assert "median_days" in body
        assert body["activated_accounts"] > 0


class TestRetention:
    def test_cohorts_default(self):
        resp = client.get("/retention/cohorts")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) > 0
        assert all(row["week_number"] <= 6 for row in body)

    def test_cohorts_custom_max_weeks(self):
        resp = client.get("/retention/cohorts", params={"max_weeks": 2})
        assert resp.status_code == 200
        assert all(row["week_number"] <= 2 for row in resp.json())

    def test_cohorts_rejects_out_of_range(self):
        resp = client.get("/retention/cohorts", params={"max_weeks": 999})
        assert resp.status_code == 422


class TestFeatures:
    def test_adoption(self):
        resp = client.get("/features/adoption")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) > 0
        assert {"feature", "adopting_accounts", "adoption_rate_all_accounts"} <= body[0].keys()


class TestExperiments:
    def test_list_experiments_includes_known_one(self):
        resp = client.get("/experiments")
        assert resp.status_code == 200
        names = {row["experiment_name"] for row in resp.json()}
        assert EXPERIMENT_NAME in names

    def test_analysis_for_known_experiment(self):
        resp = client.get(f"/experiments/{EXPERIMENT_NAME}/analysis")
        assert resp.status_code == 200
        body = resp.json()
        assert body["experiment_name"] == EXPERIMENT_NAME
        assert "srm" in body and "primary_metric" in body and "guardrail_metric" in body and "decision" in body
        assert body["decision"]["recommendation"] in {
            "ship_treatment",
            "do_not_ship",
            "inconclusive",
            "do_not_decide",
        }

    def test_analysis_for_unknown_experiment_is_404(self):
        resp = client.get("/experiments/not_a_real_experiment/analysis")
        assert resp.status_code == 404
