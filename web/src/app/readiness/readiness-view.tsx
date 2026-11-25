"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { EngineStatus, Loading, NeedProfile } from "@/components/status";
import { Band, Card, CardTitle, DivergingBars, Notice, pct } from "@/components/ui";
import { useStudent } from "@/components/use-student";
import { api, featureLabel, type Attribution, type Report } from "@/lib/client";

function fmtValue(a: Attribution) {
  return typeof a.value === "number" ? (Number.isInteger(a.value) ? a.value : a.value.toFixed(2)) : a.value;
}

export function ReadinessView() {
  const st = useStudent();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!st.profile || !st.health?.model_loaded) return;
    setError(null);
    api.predict(st.profile).then(setReport).catch((e) => setError((e as Error).message));
  }, [st.profile, st.health]);

  if (st.loading) return <Loading />;
  const p = st.stored;
  return (
    <>
      <EngineStatus health={st.health} loading={st.loading} />
      {!st.profile ? <NeedProfile /> : (
        <>
          <p className="mt-5 text-sm text-muted">
            {p?.name ? `${p.name} · ` : ""}{p?.branch} · Batch {p?.batch_year} · CGPA {p?.cgpa} · {p?.active_backlogs} backlog(s) · {p?.internships} internship(s) ·{" "}
            {p?.projects} project(s) · {p?.certifications} certification(s) · {p?.skills?.length ?? 0} skills.{" "}
            <Link href="/profile" className="text-brand-text underline">Edit</Link>
          </p>
          {error && <Notice tone="error" className="mt-5">{error}</Notice>}
          {!report && !error && st.health?.model_loaded && <Loading label="Calculating your estimate…" />}
          {report && <ReportBody report={report} />}
        </>
      )}
    </>
  );
}

function ReportBody({ report }: { report: Report }) {
  const rows = [...report.attributions].sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution)).filter((a) => Math.abs(a.contribution) >= 0.005);
  const top = rows.slice(0, 8);
  return (
    <>
      <Card accent className="mt-5">
        <div className="flex flex-wrap items-baseline gap-3">
          <span className="font-display text-6xl leading-none tabular-nums text-headline">{pct(report.probability)}</span>
          <Band p={report.probability} />
        </div>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
          Estimated probability of campus placement, based on students with similar profiles in earlier batches.
          It&apos;s an estimate from historical data, not a guarantee.
        </p>
      </Card>
      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card>
          <CardTitle>What drives your estimate</CardTitle>
          <p className="mb-3 text-xs text-faint">How much each factor moves you away from the batch average (log-odds, from SHAP).</p>
          <DivergingBars legend={["Raises your estimate", "Lowers your estimate"]}
            items={top.map((a) => ({ label: featureLabel(a.feature), value: a.contribution, title: `${featureLabel(a.feature)}: ${fmtValue(a)}` }))}
            fmt={(v) => `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(2)}`} />
          {rows.length > top.length && <p className="mt-2 text-xs text-faint">{rows.length - top.length} smaller factor(s) are in the table.</p>}
          <details className="mt-3 text-sm">
            <summary className="cursor-pointer text-xs text-muted">Show as table</summary>
            <table className="mt-2 w-full text-xs">
              <thead><tr className="text-left text-muted"><th className="py-1">Factor</th><th>Your value</th><th className="text-right">Contribution</th></tr></thead>
              <tbody>{report.attributions.map((a) => (
                <tr key={a.feature} className="border-t border-border"><td className="py-1">{featureLabel(a.feature)}</td><td>{fmtValue(a)}</td>
                  <td className="text-right tabular-nums">{a.contribution >= 0 ? "+" : ""}{a.contribution.toFixed(3)}</td></tr>
              ))}</tbody>
            </table>
          </details>
        </Card>
        <Card>
          <CardTitle>What to work on</CardTitle>
          {report.guidance.length === 0 ? <p className="text-sm text-muted">Nothing you can change is pulling your estimate down. Keep it up.</p> : (
            <ol className="divide-y divide-border">
              {report.guidance.map((g) => (
                <li key={g.feature} className="py-3">
                  <p className="text-sm font-semibold">{featureLabel(g.feature)} <span className="ml-1 tabular-nums text-bad">{g.contribution.toFixed(2)}</span></p>
                  <p className="mt-0.5 text-sm text-muted">{g.message}</p>
                </li>
              ))}
            </ol>
          )}
          <p className="mt-3 text-xs text-faint">Ranked by impact. Only factors you can still change, and only when the model confirms the change would help.</p>
        </Card>
      </div>
    </>
  );
}
