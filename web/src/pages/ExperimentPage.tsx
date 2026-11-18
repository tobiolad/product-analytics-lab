import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, type ProportionTestResult } from "../lib/api";
import { useFetch } from "../lib/useFetch";
import { ChartCard, StatTile } from "../components/ChartCard";
import { ErrorBlock, Loading } from "../components/StatusBlock";
import { num, pct, signedPct } from "../lib/format";

const EXPERIMENT_NAME = "onboarding_redesign_v1";

const RECOMMENDATION_COPY: Record<string, { label: string; tone: "good" | "warning" | "critical" }> = {
  ship_treatment: { label: "Ship treatment", tone: "good" },
  do_not_ship: { label: "Do not ship", tone: "critical" },
  inconclusive: { label: "Inconclusive", tone: "warning" },
  do_not_decide: { label: "Do not decide — fix assignment first", tone: "critical" },
};

function MetricComparison({ title, result }: { title: string; result: ProportionTestResult }) {
  const data = [
    { arm: "Control", rate: result.control_rate, n: result.control_n },
    { arm: "Treatment", rate: result.treatment_rate, n: result.treatment_n },
  ];
  return (
    <ChartCard
      title={title}
      subtitle={`${signedPct(result.absolute_diff)} absolute (95% CI ${signedPct(result.ci_95_low)} to ${signedPct(result.ci_95_high)}), p=${result.p_value.toFixed(4)}${result.significant_at_05 ? " — significant at α=0.05" : " — not significant at α=0.05"}`}
    >
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} layout="vertical" margin={{ top: 8, right: 24, left: 24, bottom: 0 }}>
          <CartesianGrid stroke="var(--gridline)" horizontal={false} />
          <XAxis type="number" tickFormatter={(v) => pct(v, 0)} tick={{ fontSize: 11, fill: "var(--text-muted)" }} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="arm" width={80} tick={{ fontSize: 12, fill: "var(--text-secondary)" }} axisLine={false} tickLine={false} />
          <Tooltip
            formatter={(value, _n, entry) => [`${pct(Number(value))} (n=${num(entry.payload.n)})`, entry.payload.arm]}
            contentStyle={{ background: "var(--surface-raised)", border: "1px solid var(--border)", fontSize: 12 }}
          />
          <Bar dataKey="rate" radius={[0, 4, 4, 0]} barSize={28}>
            <Cell fill="var(--series-1)" />
            <Cell fill="var(--series-2)" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export default function ExperimentPage() {
  const analysis = useFetch(() => api.experimentAnalysis(EXPERIMENT_NAME), []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h1 style={{ fontSize: 22 }}>Experiment: {EXPERIMENT_NAME}</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 13, marginTop: 4 }}>
          Primary metric: 7-day activation rate. Guardrail: week-1 retention. See docs/EXPERIMENT_METHODOLOGY.md for
          the pre-registered hypothesis and decision rule.
        </p>
      </div>

      {analysis.loading && <Loading />}
      {analysis.error && <ErrorBlock error={analysis.error} />}

      {analysis.data && (
        <>
          {(() => {
            const rec = RECOMMENDATION_COPY[analysis.data.decision.recommendation] ?? {
              label: analysis.data.decision.recommendation,
              tone: "warning" as const,
            };
            return (
              <div
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 10,
                  padding: 20,
                }}
              >
                <StatTile label="Decision" value={rec.label} tone={rec.tone} />
                <p style={{ marginTop: 12, fontSize: 13, color: "var(--text-secondary)" }}>{analysis.data.decision.reasoning}</p>
              </div>
            );
          })()}

          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <StatTile
              label="Sample ratio mismatch"
              value={analysis.data.srm.mismatch_detected ? "Detected" : "Clean"}
              caption={`control n=${num(analysis.data.srm.control_n)}, treatment n=${num(analysis.data.srm.treatment_n)}, p=${analysis.data.srm.p_value.toFixed(4)}`}
              tone={analysis.data.srm.mismatch_detected ? "critical" : "good"}
            />
            <StatTile
              label="Statistical power"
              value={analysis.data.power_assessment.adequately_powered_for_observed_effect ? "Adequate" : "Underpowered"}
              caption="For the effect size actually observed — a post-hoc read, not a pre-registered power analysis."
              tone={analysis.data.power_assessment.adequately_powered_for_observed_effect ? "good" : "warning"}
            />
          </div>

          <MetricComparison title="Primary metric — 7-day activation rate" result={analysis.data.primary_metric} />
          <MetricComparison title="Guardrail metric — week-1 retention" result={analysis.data.guardrail_metric} />

          <ChartCard title="Caveats">
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 8, paddingBottom: 16 }}>
              {analysis.data.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </ChartCard>
        </>
      )}
    </div>
  );
}
