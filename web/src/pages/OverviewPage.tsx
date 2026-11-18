import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api";
import { useFetch } from "../lib/useFetch";
import { ChartCard, StatTile } from "../components/ChartCard";
import { ErrorBlock, Loading } from "../components/StatusBlock";
import { CHANNEL_ORDER, channelColor, channelLabel } from "../lib/channels";
import { num, pct, shortDate } from "../lib/format";

function pivotSignups(rows: { period: string; acquisition_channel: string | null; signups: number }[]) {
  const periods = new Map<string, Record<string, number | string>>();
  for (const row of rows) {
    const key = row.acquisition_channel ?? "unknown";
    if (!periods.has(row.period)) periods.set(row.period, { period: row.period });
    periods.get(row.period)![key] = row.signups;
  }
  return Array.from(periods.values()).sort((a, b) => String(a.period).localeCompare(String(b.period)));
}

export default function OverviewPage() {
  const signups = useFetch(() => api.signupTrend("week"), []);
  const activation = useFetch(() => api.activationRate(), []);
  const dauWau = useFetch(() => api.dauWau(), []);
  const conversion = useFetch(() => api.conversion(), []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h1 style={{ fontSize: 22 }}>Overview</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 13, marginTop: 4 }}>
          Signup volume, activation, and daily/weekly engagement across the synthetic SaaS dataset.
        </p>
      </div>

      {activation.loading && <Loading />}
      {activation.error && <ErrorBlock error={activation.error} />}
      {activation.data && (
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          <StatTile label="Total accounts" value={num(activation.data[0].total_accounts)} />
          <StatTile
            label="Activated within 7 days"
            value={pct(activation.data[0].activation_rate)}
            caption={`${num(activation.data[0].activated_accounts)} of ${num(activation.data[0].total_accounts)} accounts`}
            tone="good"
          />
        </div>
      )}

      <ChartCard title="Weekly signups by acquisition channel" subtitle="Stacked by channel, fixed color per channel across the dashboard.">
        {signups.loading && <Loading />}
        {signups.error && <ErrorBlock error={signups.error} />}
        {signups.data && (
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={pivotSignups(signups.data)} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
              <CartesianGrid stroke="var(--gridline)" vertical={false} />
              <XAxis
                dataKey="period"
                tickFormatter={shortDate}
                tick={{ fontSize: 11, fill: "var(--text-muted)" }}
                axisLine={{ stroke: "var(--baseline)" }}
                tickLine={false}
              />
              <YAxis tick={{ fontSize: 11, fill: "var(--text-muted)" }} axisLine={false} tickLine={false} />
              <Tooltip
                labelFormatter={(v) => shortDate(String(v))}
                formatter={(value, name) => [value, channelLabel(String(name))]}
                contentStyle={{ background: "var(--surface-raised)", border: "1px solid var(--border)", fontSize: 12 }}
              />
              {[...CHANNEL_ORDER, "unknown"].map((ch) => (
                <Area
                  key={ch}
                  type="monotone"
                  dataKey={ch}
                  stackId="1"
                  stroke={channelColor(ch === "unknown" ? null : ch)}
                  fill={channelColor(ch === "unknown" ? null : ch)}
                  fillOpacity={0.75}
                  strokeWidth={1.5}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        )}
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap", padding: "4px 0 16px", fontSize: 12 }}>
          {[...CHANNEL_ORDER, null].map((ch) => (
            <span key={ch ?? "unknown"} style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--text-secondary)" }}>
              <span style={{ width: 10, height: 10, borderRadius: 2, background: channelColor(ch), display: "inline-block" }} />
              {channelLabel(ch)}
            </span>
          ))}
        </div>
      </ChartCard>

      <ChartCard title="Daily vs. weekly active users" subtitle="DAU plotted daily; WAU is the same ISO week's total distinct active users, repeated across its days.">
        {dauWau.loading && <Loading />}
        {dauWau.error && <ErrorBlock error={dauWau.error} />}
        {dauWau.data && (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={dauWau.data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
              <CartesianGrid stroke="var(--gridline)" vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={shortDate}
                tick={{ fontSize: 11, fill: "var(--text-muted)" }}
                axisLine={{ stroke: "var(--baseline)" }}
                tickLine={false}
                minTickGap={40}
              />
              <YAxis tick={{ fontSize: 11, fill: "var(--text-muted)" }} axisLine={false} tickLine={false} />
              <Tooltip
                labelFormatter={(v) => shortDate(String(v))}
                contentStyle={{ background: "var(--surface-raised)", border: "1px solid var(--border)", fontSize: 12 }}
              />
              <Line type="monotone" dataKey="dau" name="DAU" stroke="var(--series-1)" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="wau" name="WAU" stroke="var(--series-2)" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
        <div style={{ display: "flex", gap: 14, padding: "4px 0 16px", fontSize: 12 }}>
          <span style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--text-secondary)" }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: "var(--series-1)", display: "inline-block" }} />
            DAU
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--text-secondary)" }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: "var(--series-2)", display: "inline-block" }} />
            WAU
          </span>
        </div>
      </ChartCard>

      <ChartCard title="Plan conversion by acquisition channel" subtitle="Share of each channel's signups landing on each plan at signup time (no later upgrades modeled).">
        {conversion.loading && <Loading />}
        {conversion.error && <ErrorBlock error={conversion.error} />}
        {conversion.data && (
          <table>
            <thead>
              <tr>
                <th>Channel</th>
                <th>Plan</th>
                <th>Accounts</th>
                <th>Share within channel</th>
              </tr>
            </thead>
            <tbody>
              {conversion.data.map((row, i) => (
                <tr key={i}>
                  <td>{channelLabel(row.acquisition_channel)}</td>
                  <td style={{ textTransform: "capitalize" }}>{row.plan_id}</td>
                  <td>{num(row.accounts)}</td>
                  <td>{pct(row.pct_within_channel)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </ChartCard>
    </div>
  );
}
