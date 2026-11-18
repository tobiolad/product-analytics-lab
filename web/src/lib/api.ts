const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${path} -> ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export interface SignupTrendRow {
  period: string;
  acquisition_channel: string | null;
  signups: number;
}

export interface ActivationRateRow {
  acquisition_channel?: string;
  plan_id?: string;
  total_accounts: number;
  activated_accounts: number;
  activation_rate: number;
}

export interface DauWauRow {
  date: string;
  dau: number;
  wau: number;
}

export interface ConversionRow {
  acquisition_channel: string | null;
  plan_id: string;
  accounts: number;
  pct_within_channel: number;
}

export interface FunnelStepRow {
  step: string;
  accounts_reached: number;
  pct_of_signups: number | null;
  pct_of_previous_step: number | null;
}

export interface TimeToActivation {
  activated_accounts: number;
  median_days: number;
  mean_days: number;
  p90_days: number;
}

export interface CohortRow {
  cohort_week: string;
  cohort_size: number;
  week_number: number;
  retained_accounts: number;
  retention_rate: number;
}

export interface FeatureAdoptionRow {
  feature: string;
  adopting_accounts: number;
  adoption_rate_all_accounts: number;
  adoption_rate_among_activated: number;
}

export interface ExperimentSummary {
  experiment_name: string;
  assigned_users: number;
  first_assigned: string;
  last_assigned: string;
}

export interface ProportionTestResult {
  metric_name: string;
  control_n: number;
  control_successes: number;
  control_rate: number;
  treatment_n: number;
  treatment_successes: number;
  treatment_rate: number;
  absolute_diff: number;
  relative_lift: number | null;
  ci_95_low: number;
  ci_95_high: number;
  z_statistic: number;
  p_value: number;
  significant_at_05: boolean;
}

export interface SRMResult {
  control_n: number;
  treatment_n: number;
  expected_ratio: number;
  chi2_statistic: number;
  p_value: number;
  mismatch_detected: boolean;
}

export interface PowerAssessment {
  observed_effect_size: number;
  required_n_per_arm_for_observed_effect: number;
  actual_n_per_arm: number;
  adequately_powered_for_observed_effect: boolean;
  note: string;
}

export interface ExperimentAnalysis {
  experiment_name: string;
  srm: SRMResult;
  primary_metric: ProportionTestResult;
  guardrail_metric: ProportionTestResult;
  power_assessment: PowerAssessment;
  warnings: string[];
  decision: { recommendation: string; reasoning: string };
}

export const api = {
  signupTrend: (granularity: "day" | "week" = "week") =>
    get<SignupTrendRow[]>(`/overview/signup-trend?granularity=${granularity}`),
  activationRate: (by?: "acquisition_channel" | "plan_id") =>
    get<ActivationRateRow[]>(`/overview/activation-rate${by ? `?by=${by}` : ""}`),
  dauWau: () => get<DauWauRow[]>("/overview/dau-wau"),
  conversion: () => get<ConversionRow[]>("/overview/conversion"),
  onboardingFunnel: () => get<FunnelStepRow[]>("/funnel/onboarding"),
  timeToActivation: () => get<TimeToActivation>("/funnel/time-to-activation"),
  cohortRetention: (maxWeeks = 6) => get<CohortRow[]>(`/retention/cohorts?max_weeks=${maxWeeks}`),
  featureAdoption: () => get<FeatureAdoptionRow[]>("/features/adoption"),
  listExperiments: () => get<ExperimentSummary[]>("/experiments"),
  experimentAnalysis: (name: string) => get<ExperimentAnalysis>(`/experiments/${name}/analysis`),
};
