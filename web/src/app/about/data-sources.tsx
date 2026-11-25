"use client";
import { useEffect, useState } from "react";
import { api, type Health } from "@/lib/client";

/** Which data the live model was trained on, read from the engine. */
export function DataSources() {
  const [h, setH] = useState<Health | null | undefined>(undefined);
  useEffect(() => { api.health().then(setH).catch(() => setH(null)); }, []);
  if (h === undefined) return <p className="text-sm text-faint">Loading…</p>;
  if (!h?.model) return <p className="text-sm text-faint">No model information available (is the engine running?).</p>;
  const m = h.model;
  return (
    <div className="space-y-3 text-sm leading-6 text-muted">
      <p>
        Current model: {m.model_type ?? "logistic regression"}, trained on <strong className="text-foreground">{m.n_records?.toLocaleString()}</strong> students
        {m.trained_at ? ` on ${new Date(m.trained_at).toLocaleDateString()}` : ""}. Cross-validated ROC-AUC {m.roc_auc?.toFixed(3)}.
      </p>
      {m.public_data && (
        <>
          <ul className="list-disc space-y-1 pl-5">
            {m.data_sources?.map((d) => (
              <li key={d.source}>
                {d.url ? <a className="text-brand-text underline" href={d.url} target="_blank" rel="noreferrer">{d.title ?? d.source}</a> : (d.title ?? d.source)}: {d.rows.toLocaleString()} students
              </li>
            ))}
          </ul>
          <p className="font-semibold text-foreground">Limitations</p>
          <ul className="list-disc space-y-1 pl-5">{m.data_notes?.map((n) => <li key={n}>{n}</li>)}</ul>
        </>
      )}
      {m.synthetic_data && <p>This model was trained on synthetic demo data, for testing only.</p>}
    </div>
  );
}
