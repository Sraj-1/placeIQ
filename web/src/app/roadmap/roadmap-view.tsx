"use client";
import { useEffect, useState } from "react";
import { EngineStatus, Loading, NeedProfile } from "@/components/status";
import { Card, CardTitle, Meter, Notice, pct } from "@/components/ui";
import { useStudent } from "@/components/use-student";
import { api, type Roadmap } from "@/lib/client";

type Entry = Roadmap["companies"]["eligible"][number];

function Bucket({ title, icon, tone, entries, empty, collapsed }: { title: string; icon: string; tone: string; entries: Entry[]; empty: string; collapsed?: boolean }) {
  const list = (
    <ul className="grid gap-3 text-sm">
      {entries.map((c) => (
        <li key={c.name}>{c.name}{c.gaps.length > 0 && <ul className="ml-4 list-disc text-xs text-muted">{c.gaps.map((g, i) => <li key={i}>{g.detail}</li>)}</ul>}</li>
      ))}
    </ul>
  );
  return (
    <div className="min-w-0">
      <h3 className="mb-2 text-sm font-semibold"><span className={tone}>{icon}</span> {title} ({entries.length})</h3>
      {entries.length === 0 ? <p className="text-sm text-faint">{empty}</p>
        : collapsed ? <details><summary className="cursor-pointer text-xs text-muted">Show reasons</summary><div className="mt-2">{list}</div></details> : list}
    </div>
  );
}

export function RoadmapView() {
  const st = useStudent();
  const [rm, setRm] = useState<Roadmap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [all, setAll] = useState(false);

  useEffect(() => {
    if (!st.profile || !st.health) return;
    api.roadmap(st.profile).then(setRm).catch((e) => setError((e as Error).message));
  }, [st.profile, st.health]);

  if (st.loading) return <Loading />;
  if (!st.profile) return <><EngineStatus health={st.health} loading={false} /><NeedProfile /></>;
  const roles = rm ? (all ? rm.roles : rm.roles.slice(0, 3)) : [];
  return (
    <>
      <EngineStatus health={st.health} loading={false} />
      {error && <Notice tone="error" className="mt-5">{error}</Notice>}
      {!rm && !error && st.health && <Loading label="Building your roadmap…" />}
      {rm && (
        <>
          <Card className="mt-5">
            <CardTitle>Roles</CardTitle>
            <p className="mb-3 text-sm text-muted">Your skills against what each role&apos;s job description asks for, best match first.</p>
            <div className="grid gap-3">
              {roles.map((r) => {
                const total = r.have.length + r.missing.length;
                return (
                  <div key={r.id} className="grid gap-2 rounded-xl border border-border p-4">
                    <div className="flex flex-wrap justify-between gap-2"><strong className="text-sm">{r.title}</strong><span className="text-xs text-faint">{r.have.length} of {total} skills</span></div>
                    <Meter value={r.coverage} label={`${r.title} skill coverage`} />
                    {r.missing.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-xs text-faint">To learn:</span>
                        {r.missing.map((s) => <span key={s} className="rounded-full border border-dashed border-border px-2 py-0.5 text-xs">{s}</span>)}
                      </div>
                    )}
                    {r.have.length > 0 && <p className="text-xs text-faint">You have: {r.have.join(", ")}</p>}
                    {r.delta_if_learned !== undefined && r.missing.length > 0 && (r.delta_if_learned >= 0.005
                      ? <p className="text-xs">Learning all of these: estimate {pct(r.probability_if_learned!)} (+{(r.delta_if_learned * 100).toFixed(1)} pts)</p>
                      : <p className="text-xs text-faint">Past batches show no measurable placement gain from these skills alone. They still matter for this role&apos;s interviews.</p>)}
                  </div>
                );
              })}
            </div>
            {rm.roles.length > 3 && <button type="button" className="mt-3 text-xs text-muted underline" onClick={() => setAll(!all)}>{all ? "Show top 3 only" : `Show all ${rm.roles.length} roles`}</button>}
          </Card>
          <Card className="mt-5">
            <CardTitle>Recruiters</CardTitle>
            <div className="grid gap-6 md:grid-cols-3">
              <Bucket title="Eligible now" icon="✓" tone="text-good" entries={rm.companies.eligible} empty="None yet." />
              <Bucket title="Within reach" icon="!" tone="text-warn" entries={rm.companies.near} empty="None." />
              <Bucket title="Out of reach" icon="✕" tone="text-bad" entries={rm.companies.out_of_reach} empty="None." collapsed />
            </div>
            <p className="mt-4 text-xs text-faint">&quot;Within reach&quot; means every gap can be fixed before placement season: skills, backlogs, or a CGPA shortfall of 0.5 or less.</p>
          </Card>
        </>
      )}
    </>
  );
}
