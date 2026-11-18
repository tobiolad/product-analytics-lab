import { api } from "../lib/api";
import { useFetch } from "../lib/useFetch";
import { ChartCard } from "../components/ChartCard";
import { ErrorBlock, Loading } from "../components/StatusBlock";
import { sequentialStep, sequentialTextColor } from "../lib/sequential";
import { num, pct, shortDate } from "../lib/format";

const MAX_WEEKS = 6;

export default function RetentionPage() {
  const cohorts = useFetch(() => api.cohortRetention(MAX_WEEKS), []);

  const cohortWeeks = Array.from(new Set((cohorts.data ?? []).map((r) => r.cohort_week))).sort();
  const byKey = new Map((cohorts.data ?? []).map((r) => [`${r.cohort_week}:${r.week_number}`, r]));
  const sizeByWeek = new Map((cohorts.data ?? []).map((r) => [r.cohort_week, r.cohort_size]));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h1 style={{ fontSize: 22 }}>Retention cohorts</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 13, marginTop: 4 }}>
          % of each weekly signup cohort with at least one active day in that week-of-cohort. Week 0 is the signup
          week itself, included for a complete matrix.
        </p>
      </div>

      <ChartCard title="Weekly cohort retention" subtitle="Rows are signup-week cohorts; columns are weeks since signup. Darker = higher retention.">
        {cohorts.loading && <Loading />}
        {cohorts.error && <ErrorBlock error={cohorts.error} />}
        {cohorts.data && (
          <div style={{ overflowX: "auto", paddingBottom: 16 }}>
            <table>
              <thead>
                <tr>
                  <th>Cohort week</th>
                  <th>Size</th>
                  {Array.from({ length: MAX_WEEKS + 1 }, (_, w) => (
                    <th key={w} style={{ textAlign: "center" }}>
                      Week {w}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {cohortWeeks.map((week) => (
                  <tr key={week}>
                    <td style={{ whiteSpace: "nowrap" }}>{shortDate(week)}</td>
                    <td>{num(sizeByWeek.get(week))}</td>
                    {Array.from({ length: MAX_WEEKS + 1 }, (_, w) => {
                      const cell = byKey.get(`${week}:${w}`);
                      if (!cell) return <td key={w} style={{ textAlign: "center", color: "var(--text-muted)" }}>—</td>;
                      return (
                        <td
                          key={w}
                          style={{
                            textAlign: "center",
                            background: sequentialStep(cell.retention_rate),
                            color: sequentialTextColor(cell.retention_rate),
                            fontWeight: 500,
                            borderBottom: "1px solid var(--border)",
                          }}
                        >
                          {pct(cell.retention_rate, 0)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </ChartCard>
    </div>
  );
}
