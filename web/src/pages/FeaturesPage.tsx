import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api";
import { useFetch } from "../lib/useFetch";
import { ChartCard } from "../components/ChartCard";
import { ErrorBlock, Loading } from "../components/StatusBlock";
import { pct } from "../lib/format";

function featureLabel(name: string): string {
  return name
    .replace(/^used_/, "")
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}

export default function FeaturesPage() {
  const adoption = useFetch(() => api.featureAdoption(), []);
  const rows = (adoption.data ?? [])
    .map((r) => ({ ...r, label: featureLabel(r.feature) }))
    .sort((a, b) => b.adoption_rate_all_accounts - a.adoption_rate_all_accounts);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h1 style={{ fontSize: 22 }}>Feature adoption</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 13, marginTop: 4 }}>
          Share of accounts that have used each feature at least once, against the whole base and against activated
          accounts only.
        </p>
      </div>

      <ChartCard title="Adoption rate by feature">
        {adoption.loading && <Loading />}
        {adoption.error && <ErrorBlock error={adoption.error} />}
        {adoption.data && (
          <ResponsiveContainer width="100%" height={Math.max(220, rows.length * 44)}>
            <BarChart data={rows} layout="vertical" margin={{ top: 8, right: 24, left: 24, bottom: 0 }}>
              <CartesianGrid stroke="var(--gridline)" horizontal={false} />
              <XAxis
                type="number"
                tickFormatter={(v) => pct(v, 0)}
                tick={{ fontSize: 11, fill: "var(--text-muted)" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="label"
                width={140}
                tick={{ fontSize: 12, fill: "var(--text-secondary)" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                formatter={(value) => pct(Number(value))}
                contentStyle={{ background: "var(--surface-raised)", border: "1px solid var(--border)", fontSize: 12 }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="adoption_rate_all_accounts" name="All accounts" fill="var(--series-1)" radius={[0, 4, 4, 0]} barSize={14} />
              <Bar
                dataKey="adoption_rate_among_activated"
                name="Among activated"
                fill="var(--series-2)"
                radius={[0, 4, 4, 0]}
                barSize={14}
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </ChartCard>
    </div>
  );
}
