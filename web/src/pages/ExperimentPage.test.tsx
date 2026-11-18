import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ExperimentPage from "./ExperimentPage";
import { api, type ExperimentAnalysis } from "../lib/api";

vi.mock("../lib/api", () => ({
  api: { experimentAnalysis: vi.fn() },
}));

const BASE_RESULT = {
  metric_name: "m",
  control_n: 234,
  control_successes: 68,
  control_rate: 0.2906,
  treatment_n: 271,
  treatment_successes: 109,
  treatment_rate: 0.4022,
  absolute_diff: 0.1116,
  relative_lift: 0.3841,
  ci_95_low: 0.0292,
  ci_95_high: 0.194,
  z_statistic: 2.6214,
  p_value: 0.008756,
  significant_at_05: true,
};

function makeAnalysis(overrides: Partial<ExperimentAnalysis> = {}): ExperimentAnalysis {
  return {
    experiment_name: "onboarding_redesign_v1",
    srm: {
      control_n: 234,
      treatment_n: 271,
      expected_ratio: 0.5,
      chi2_statistic: 2.71,
      p_value: 0.0997,
      mismatch_detected: false,
    },
    primary_metric: BASE_RESULT,
    guardrail_metric: { ...BASE_RESULT, absolute_diff: 0.003, significant_at_05: false },
    power_assessment: {
      observed_effect_size: 0.1116,
      required_n_per_arm_for_observed_effect: 300,
      actual_n_per_arm: 234,
      adequately_powered_for_observed_effect: false,
      note: "post-hoc",
    },
    warnings: ["Some caveat about multiple comparisons."],
    decision: { recommendation: "ship_treatment", reasoning: "Primary metric improved with no guardrail harm." },
    ...overrides,
  };
}

describe("ExperimentPage", () => {
  it("shows a loading state before the analysis resolves", () => {
    vi.mocked(api.experimentAnalysis).mockReturnValue(new Promise(() => {}));
    render(<ExperimentPage />);
    expect(screen.getByText(/Loading/)).toBeInTheDocument();
  });

  it("renders the decision, SRM, and metric comparisons once data loads", async () => {
    vi.mocked(api.experimentAnalysis).mockResolvedValue(makeAnalysis());
    render(<ExperimentPage />);

    await waitFor(() => expect(screen.getByText("Ship treatment")).toBeInTheDocument());
    expect(screen.getByText("Clean")).toBeInTheDocument();
    expect(screen.getByText(/Primary metric improved with no guardrail harm\./)).toBeInTheDocument();
    expect(screen.getByText(/Some caveat about multiple comparisons\./)).toBeInTheDocument();
  });

  it("renders a critical do-not-ship decision distinctly", async () => {
    vi.mocked(api.experimentAnalysis).mockResolvedValue(
      makeAnalysis({ decision: { recommendation: "do_not_ship", reasoning: "Guardrail regressed." } }),
    );
    render(<ExperimentPage />);
    await waitFor(() => expect(screen.getByText("Do not ship")).toBeInTheDocument());
  });

  it("shows an error state when the API call fails", async () => {
    vi.mocked(api.experimentAnalysis).mockRejectedValue(new Error("network down"));
    render(<ExperimentPage />);
    await waitFor(() => expect(screen.getByText(/Couldn't load this data/)).toBeInTheDocument());
    expect(screen.getByText(/network down/)).toBeInTheDocument();
  });
});
