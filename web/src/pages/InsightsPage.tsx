import { api } from "../lib/api";
import { useFetch } from "../lib/useFetch";
import { ChartCard } from "../components/ChartCard";
import { ErrorBlock, Loading } from "../components/StatusBlock";
import { num, pct, signedPct } from "../lib/format";

const EXPERIMENT_NAME = "onboarding_redesign_v1";

/**
 * Every bullet below is computed from the live API response at render time --
 * nothing here is a hand-written number. If the underlying synthetic data is
 * regenerated, this page updates with it instead of going stale.
 */
export default function InsightsPage() {
  const activation = useFetch(() => api.activationRate(), []);
  const funnel = useFetch(() => api.onboardingFunnel(), []);
  const adoption = useFetch(() => api.featureAdoption(), []);
  const experiment = useFetch(() => api.experimentAnalysis(EXPERIMENT_NAME), []);

  const loading = activation.loading || funnel.loading || adoption.loading || experiment.loading;
  const error = activation.error || funnel.error || adoption.error || experiment.error;

  const biggestDropoff = funnel.data
    ?.filter((s) => s.pct_of_previous_step !== null)
    .reduce((worst, s) => (s.pct_of_previous_step! < (worst?.pct_of_previous_step ?? 1) ? s : worst), undefined as
      | (typeof funnel.data)[number]
      | undefined);

  const topFeature = adoption.data?.slice().sort((a, b) => b.adoption_rate_all_accounts - a.adoption_rate_all_accounts)[0];
  const bottomFeature = adoption.data?.slice().sort((a, b) => a.adoption_rate_all_accounts - b.adoption_rate_all_accounts)[0];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h1 style={{ fontSize: 22 }}>Insights</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 13, marginTop: 4 }}>
          A plain-language read of the charts on the other pages, computed from the same live data.
        </p>
      </div>

      {loading && <Loading />}
      {error && <ErrorBlock error={error} />}

      {!loading && !error && activation.data && funnel.data && adoption.data && experiment.data && (
        <ChartCard title="Summary">
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 14, color: "var(--text-primary)", display: "flex", flexDirection: "column", gap: 14, paddingBottom: 16 }}>
            <li>
              <strong>{pct(activation.data[0].activation_rate)}</strong> of accounts ({num(activation.data[0].activated_accounts)}{" "}
              of {num(activation.data[0].total_accounts)}) activate (complete the key action) within 7 days of signup.
            </li>
            {biggestDropoff && (
              <li>
                The steepest step-over-step drop-off is at <strong>{biggestDropoff.step.replace(/_/g, " ")}</strong>, which
                only <strong>{pct(biggestDropoff.pct_of_previous_step)}</strong> of the previous step's accounts reach — the
                clearest target for onboarding improvements.
              </li>
            )}
            {topFeature && bottomFeature && (
              <li>
                <strong>{topFeature.feature.replace(/^used_/, "").replace(/_/g, " ")}</strong> is the most broadly adopted
                feature ({pct(topFeature.adoption_rate_all_accounts)} of all accounts), while{" "}
                <strong>{bottomFeature.feature.replace(/^used_/, "").replace(/_/g, " ")}</strong> is the least (
                {pct(bottomFeature.adoption_rate_all_accounts)}) — a candidate for discoverability work or to question
                whether it should exist at all.
              </li>
            )}
            <li>
              The <strong>{EXPERIMENT_NAME}</strong> experiment shows a{" "}
              <strong>{signedPct(experiment.data.primary_metric.absolute_diff)}</strong> absolute change in 7-day activation
              for treatment vs. control (p={experiment.data.primary_metric.p_value.toFixed(4)},{" "}
              {experiment.data.primary_metric.significant_at_05 ? "statistically significant" : "not statistically significant"}
              ), with{" "}
              {experiment.data.guardrail_metric.significant_at_05 && experiment.data.guardrail_metric.absolute_diff < 0
                ? "a statistically significant regression"
                : "no statistically significant regression"}{" "}
              on the week-1 retention guardrail. Recommendation:{" "}
              <strong>{experiment.data.decision.recommendation.replace(/_/g, " ")}</strong>.
            </li>
            {!experiment.data.power_assessment.adequately_powered_for_observed_effect && (
              <li style={{ color: "var(--text-secondary)" }}>
                Caveat: this experiment's sample size is underpowered to reliably detect an effect as small as the one
                observed, at conventional 80% power — a non-significant primary result should be read as "inconclusive," not
                "no effect."
              </li>
            )}
          </ul>
        </ChartCard>
      )}
    </div>
  );
}
