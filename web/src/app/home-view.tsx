"use client";
import { ArrowRight, Share2 } from "lucide-react";
import { useEffect, useState } from "react";
import { EngineStatus, Loading, NeedProfile } from "@/components/status";
import { Band, ButtonLink, Card, CardTitle, Delta, Gauge, Meter, Notice, pct } from "@/components/ui";
import { useStudent } from "@/components/use-student";
import { api, type Roadmap, type WhatIfResult } from "@/lib/client";

export function HomeView() {
  const st = useStudent();
  const [wi, setWi] = useState<WhatIfResult | null>(null);
  const [rm, setRm] = useState<Roadmap | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!st.profile || !st.health?.model_loaded) return;
    Promise.all([api.whatif(st.profile), api.roadmap(st.profile)])
      .then(([w, r]) => { setWi(w); setRm(r); })
      .catch((e) => setError((e as Error).message));
  }, [st.profile, st.health]);

  if (st.loading) return <Loading />;
  const first = st.stored?.name?.split(" ")[0];
  return (
    <>
      {first && <p className="mt-5 text-sm text-muted">Welcome back, {first}.</p>}
      <EngineStatus health={st.health} loading={false} />
      {!st.profile ? <NeedProfile /> : error ? <Notice tone="error" className="mt-5">{error}</Notice> : !wi || !rm ? (st.health?.model_loaded ? <Loading label="Calculating…" /> : null) : (
        <>
          <div className="mt-5 grid gap-5 lg:grid-cols-2">
            <Card accent>
              <CardTitle>Estimated placement chance</CardTitle>
              <div className="flex flex-wrap items-center gap-5">
                <Gauge value={wi.probability} />
                <div className="min-w-0 flex-1 space-y-2">
                  <Band p={wi.probability} />
                  <p className="text-sm leading-6 text-muted">Based on students with similar profiles, from a model trained on recorded placement outcomes. An estimate, not a guarantee.</p>
                </div>
              </div>
              <div className="mt-4"><ButtonLink href="/readiness">See full report <ArrowRight className="size-4" /></ButtonLink></div>
            </Card>
            <Card>
              <CardTitle>Your best next step</CardTitle>
              {wi.suggestions.length === 0 ? <p className="text-sm text-muted">No single change raises your estimate measurably. You&apos;re in good shape.</p> : (
                <>
                  <p className="font-display text-3xl leading-tight text-headline">{wi.suggestions[0].label.replace(/ \(.*\)$/, "")}</p>
                  <div className="mt-3 flex flex-wrap items-baseline gap-3">
                    <span className="text-2xl font-semibold tabular-nums">{pct(wi.probability)} → {pct(wi.suggestions[0].probability)}</span>
                    <Delta value={wi.suggestions[0].delta} />
                  </div>
                  {wi.suggestions.length > 1 && (
                    <p className="mt-2 text-sm text-muted">Then: {wi.suggestions.slice(1, 3).map((s) => `${s.label.replace(/ \(.*\)$/, "").toLowerCase()} (+${(s.delta * 100).toFixed(1)} pts)`).join(", ")}.</p>
                  )}
                </>
              )}
              <div className="mt-4"><ButtonLink href="/what-if" variant="outline">Open the what-if simulator</ButtonLink></div>
            </Card>
          </div>
          <Card className="mt-5">
            <CardTitle action={<ButtonLink href="/roadmap" variant="ghost" size="sm">Open roadmap <ArrowRight className="size-3.5" /></ButtonLink>}>Roadmap at a glance</CardTitle>
            <div className="grid gap-5 md:grid-cols-3">
              {rm.roles.slice(0, 2).map((r) => (
                <div key={r.id} className="min-w-0 space-y-2">
                  <div className="flex justify-between gap-2 text-sm"><strong className="truncate">{r.title.replace(/ \(.*\)$/, "")}</strong><span className="shrink-0 text-faint">{r.have.length} / {r.have.length + r.missing.length}</span></div>
                  <Meter value={r.coverage} label={`${r.title} skill coverage`} />
                  {r.missing.length > 0 && <p className="text-xs text-muted">Learn next: {r.missing.slice(0, 3).join(", ")}</p>}
                </div>
              ))}
              <div className="rounded-xl border border-border bg-brand-soft p-4">
                <p className="text-xs font-semibold text-brand-text">Recruiters</p>
                <p className="mt-1 text-xl font-semibold">{rm.companies.eligible.length} eligible · {rm.companies.near.length} within reach</p>
                <p className="mt-1 text-xs text-muted">{rm.companies.out_of_reach.length} out of reach for now</p>
              </div>
            </div>
          </Card>
          <Card className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-muted"><Share2 className="mr-1.5 inline size-4 text-brand-text" />Share your confirmed profile with your placement cell so they can plan training. Your roll number becomes an anonymous code.</p>
            <ButtonLink href="/profile#share" variant="outline">Share with placement cell</ButtonLink>
          </Card>
        </>
      )}
    </>
  );
}
