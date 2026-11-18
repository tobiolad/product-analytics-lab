import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api";
import { useFetch } from "../lib/useFetch";
import { ChartCard, StatTile } from "../components/ChartCard";
import { ErrorBlock, Loading } from "../components/StatusBlock";
import { num, pct } from "../lib/format";

const STEP_LABELS: Record<string, string> = {
  signed_up: "Signed up",
  completed_profile: "Completed profile",
  created_first_workspace: "Created first workspace",
  completed_key_action: "Completed key action (activation)",
};

// Ordinal sequential ramp, lightest step clamped to >=250 per the dataviz
// skill's ordinal-ramp floor for the light surface.
const STEP_COLORS = ["var(--seq-250)", "var(--seq-400)", "var(--seq-500)", "var(--seq-650)"];

export default function FunnelPage() {
  const funnel = useFetch(() => api.onboardingFunnel(), []);
  const timeToActivation = useFetch(() => api.timeToActivation(), []);

  const mainSteps = funnel.data?.filter((s) => s.step in STEP_LABELS) ?? [];
  const sideStep = funnel.data?.find((s) => s.step.startsWith("invited_teammate"));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h1 style={{ fontSize: 22 }}>Onboarding funnel</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 13, marginTop: 4 }}>
          Each step's share of all signups, plus drop-off relative to the previous step.
        </p>
      </div>

      <ChartCard title="Accounts reaching each step" subtitle="Denominator for 'pct of signups' is always total signed-up accounts, never the previous step's count.">
        {funnel.loading && <Loading />}
        {funnel.error && <ErrorBlock error={funnel.error} />}
        {funnel.data && (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={mainSteps} layout="vertical" margin={{ top: 8, right: 24, left: 24, bottom: 0 }}>
              <CartesianGrid stroke="var(--gridline)" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11, fill: "var(--text-muted)" }} axisLine={false} tickLine={false} />
              <YAxis
                type="category"
                dataKey="step"
                tickFormatter={(s) => STEP_LABELS[s] ?? s}
                width={190}
                tick={{ fontSize: 12, fill: "var(--text-secondary)" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                formatter={(value, _n, entry) => [
                  `${num(Number(value))} accounts (${pct(entry.payload.pct_of_signups)} of signups)`,
                  STEP_LABELS[entry.payload.step] ?? entry.payload.step,
                ]}
                contentStyle={{ background: "var(--surface-raised)", border: "1px solid var(--border)", fontSize: 12 }}
              />
              <Bar dataKey="accounts_reached" radius={[0, 4, 4, 0]}>
                {mainSteps.map((_, i) => (
                  <Cell key={i} fill={STEP_COLORS[i] ?? STEP_COLORS[STEP_COLORS.length - 1]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </ChartCard>

      <ChartCard title="Step-over-step drop-off" subtitle="Share of the previous step's accounts that reached this one.">
        {funnel.data && (
          <table>
            <thead>
              <tr>
                <th>Step</th>
                <th>Accounts</th>
                <th>% of signups</th>
                <th>% of previous step</th>
              </tr>
            </thead>
            <tbody>
              {mainSteps.map((row) => (
                <tr key={row.step}>
                  <td>{STEP_LABELS[row.step] ?? row.step}</td>
                  <td>{num(row.accounts_reached)}</td>
                  <td>{pct(row.pct_of_signups)}</td>
                  <td>{row.pct_of_previous_step === null ? "—" : pct(row.pct_of_previous_step)}</td>
                </tr>
              ))}
              {sideStep && (
                <tr>
                  <td style={{ color: "var(--text-muted)" }}>Invited a teammate (optional, doesn't gate activation)</td>
                  <td>{num(sideStep.accounts_reached)}</td>
                  <td>{pct(sideStep.pct_of_signups)}</td>
                  <td>—</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </ChartCard>

      <ChartCard title="Time to activation" subtitle="Among accounts that ever reached 'completed key action', regardless of the 7-day activation-rate window.">
        {timeToActivation.loading && <Loading />}
        {timeToActivation.error && <ErrorBlock error={timeToActivation.error} />}
        {timeToActivation.data && (
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", paddingBottom: 16 }}>
            <StatTile label="Ever activated" value={num(timeToActivation.data.activated_accounts)} />
            <StatTile label="Median days to activate" value={`${timeToActivation.data.median_days}d`} />
            <StatTile label="Mean days to activate" value={`${timeToActivation.data.mean_days}d`} />
            <StatTile label="90th percentile" value={`${timeToActivation.data.p90_days}d`} />
          </div>
        )}
      </ChartCard>
    </div>
  );
}
