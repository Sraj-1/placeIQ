"use client";
import { useEffect, useRef, useState } from "react";
import { SkillPicker } from "@/components/skill-picker";
import { EngineStatus, Loading, NeedProfile } from "@/components/status";
import { Button, Card, CardTitle, Delta, Notice, pct } from "@/components/ui";
import { useStudent } from "@/components/use-student";
import { api, type Profile, type WhatIfSuggestion } from "@/lib/client";

type NumKey = "cgpa" | "active_backlogs" | "internships" | "projects" | "certifications";
const SLIDERS: { key: NumKey; label: string; min: number; max: number; step: number }[] = [
  { key: "cgpa", label: "CGPA", min: 5, max: 10, step: 0.05 },
  { key: "active_backlogs", label: "Active backlogs", min: 0, max: 8, step: 1 },
  { key: "internships", label: "Internships", min: 0, max: 6, step: 1 },
  { key: "projects", label: "Projects", min: 0, max: 10, step: 1 },
  { key: "certifications", label: "Certifications", min: 0, max: 10, step: 1 },
];

export function WhatIfView() {
  const st = useStudent();
  if (st.loading) return <Loading />;
  return (
    <>
      <EngineStatus health={st.health} loading={st.loading} />
      {!st.profile ? <NeedProfile /> : st.health?.model_loaded ? <Simulator profile={st.profile} taxonomy={st.taxonomy} /> : null}
    </>
  );
}

function Simulator({ profile, taxonomy }: { profile: Profile; taxonomy: Record<string, string> }) {
  const [base, setBase] = useState<number | null>(null);
  const [sim, setSim] = useState<Profile>(profile);
  const [prob, setProb] = useState<number | null>(null);
  const [steps, setSteps] = useState<WhatIfSuggestion[]>([]);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => {
    api.whatif(profile).then((r) => { setBase(r.probability); setProb(r.probability); setSteps(r.suggestions); }).catch((e) => setError((e as Error).message));
  }, [profile]);

  // Live re-score from the trained model, debounced while a slider is dragged.
  useEffect(() => {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      api.score([sim]).then((r) => { setProb(r.probabilities[0]); setError(null); }).catch((e) => setError((e as Error).message));
    }, 200);
    return () => window.clearTimeout(timer.current);
  }, [sim]);

  if (base === null || prob === null) return error ? <Notice tone="error" className="mt-5">{error}</Notice> : <Loading label="Asking the model…" />;
  const changed = JSON.stringify(sim) !== JSON.stringify(profile);
  return (
    <>
      <Card accent className="mt-5">
        <div className="flex flex-wrap items-end gap-6">
          <div><p className="text-xs text-faint">Your estimate</p><p className="font-display text-5xl leading-none tabular-nums text-headline">{pct(base)}</p></div>
          <span aria-hidden className="pb-1 text-2xl text-faint">→</span>
          <div><p className="text-xs text-faint">With these changes</p><p className="font-display text-5xl leading-none tabular-nums text-headline">{pct(prob)}</p></div>
          <div className="pb-1"><Delta value={prob - base} /></div>
          {changed && <Button variant="outline" size="sm" onClick={() => setSim(profile)}>Reset</Button>}
        </div>
        <div className="mt-6 grid gap-x-10 gap-y-5 sm:grid-cols-2">
          {SLIDERS.map(({ key, label, min, max, step }) => (
            <div key={key}>
              <label htmlFor={`sim-${key}`} className="flex justify-between gap-2 text-xs font-semibold text-muted">
                <span>{label}{sim[key] !== profile[key] && <span className="font-normal text-faint"> (was {profile[key]})</span>}</span>
                <span className="tabular-nums text-foreground">{key === "cgpa" ? sim[key].toFixed(2) : sim[key]}</span>
              </label>
              <input id={`sim-${key}`} type="range" min={Math.min(min, profile[key])} max={Math.max(max, profile[key])} step={step} value={sim[key]}
                onChange={(e) => setSim({ ...sim, [key]: key === "cgpa" ? Math.round(Number(e.target.value) * 100) / 100 : Number(e.target.value) })}
                className="mt-1.5 w-full accent-[var(--color-brand)]" />
            </div>
          ))}
        </div>
        <details className="mt-5">
          <summary className="cursor-pointer text-sm text-muted">Try adding or removing skills ({sim.skills.length})</summary>
          <div className="mt-3"><SkillPicker taxonomy={taxonomy} value={sim.skills} onChange={(skills) => setSim({ ...sim, skills })} idPrefix="sim-skill" /></div>
        </details>
        {error && <Notice tone="error" className="mt-4">{error}</Notice>}
      </Card>

      <Card className="mt-5">
        <CardTitle>Most effective next steps for you</CardTitle>
        {steps.length === 0 ? <p className="text-sm text-muted">No single step raises your estimate measurably. You&apos;re in good shape.</p> : (
          <ol className="divide-y divide-border">
            {steps.map((s) => (
              <li key={s.key} className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1 py-3 sm:grid-cols-[1fr_auto_auto]">
                <div className="min-w-0"><p className="text-sm">{s.label}</p><p className="text-xs text-faint">{pct(base)} → {pct(s.probability)}</p></div>
                <Delta value={s.delta} />
                <Button variant="outline" size="sm" className="col-span-2 justify-self-start sm:col-span-1" onClick={() => setSim({ ...profile, ...s.changes })}>Try it</Button>
              </li>
            ))}
          </ol>
        )}
        <p className="mt-3 text-xs text-faint">Patterns learned from past batches (association, not a guarantee). Skills count by category, so swapping one skill for another in the same category won&apos;t change the estimate.</p>
      </Card>
    </>
  );
}
