"use client";
// PlaceIQ placement cell: extraction study (§4.3), baseline comparison (§4.6), fairness audit.
import { useEffect, useState } from "react";
import { adminApi, signalLabel, type ExtractionMetrics, type Fairness, type ModelMetrics } from "@/lib/client";
import { Badge, Button, Notice, Section, Table, Tile, Tiles, n3, pct, signed } from "@/components/ui";
import { ModelNotice } from "./model";

function verdict(ci: [number, number]) {
  if (ci[0] > 0) return { text: "Classifier better", cls: "text-emerald-800 dark:text-emerald-400" };
  if (ci[1] < 0) return { text: "Similarity better", cls: "text-red-700 dark:text-red-400" };
  return { text: "No clear difference", cls: "text-muted" };
}

const ATTR_LABEL: Record<string, string> = { branch: "Branch", gender: "Gender", batch_year: "Batch year" };
const GAP_LABEL: Record<string, string> = { auc_gap: "AUC gap (ranking quality)", tpr_gap: "TPR gap (equal opportunity)", fpr_gap: "FPR gap (false alarms)", calibration_gap: "Calibration gap" };

function FairnessAudit({ fairness }: { fairness?: Fairness }) {
  return (
    <Section title="Fairness audit">
      <p className="text-sm text-muted">
        Does the model work equally well for every group? Out-of-fold predictions. TPR is the share of placed students flagged at the {fairness?.threshold ?? 0.5} threshold;
        FPR is the share of not-placed students wrongly flagged. Groups under {fairness?.min_group ?? 15} students are shown but excluded from the gaps. Gender is used only here, never as a model input.
      </p>
      {!fairness ? <p className="mt-2 text-sm text-faint">Retrain the model to compute the audit.</p> : Object.entries(fairness.attributes).map(([attr, a]) => (
        <div key={attr} className="mt-5">
          <h3 className="mb-2 text-sm font-semibold">{ATTR_LABEL[attr] ?? attr}</h3>
          <div className="mb-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {(["auc_gap", "tpr_gap", "fpr_gap", "calibration_gap"] as const).map((k) => {
              const flagged = a.flags.includes(k);
              return (
                <div key={k} className={`rounded-lg border p-2 text-xs ${flagged ? "border-amber-500/60 bg-amber-500/10" : "border-border"}`}>
                  <div className="text-muted">{GAP_LABEL[k]}</div>
                  <div className="text-lg font-semibold tabular-nums">{flagged ? "! " : ""}{n3(a[k])}</div>
                </div>
              );
            })}
          </div>
          <Table head={["Group", "Students", "Placed (actual)", "Mean predicted", "AUC", "TPR", "FPR"]}>
            {a.groups.map((g) => (
              <tr key={g.group} className={g.too_small ? "text-faint" : ""}>
                <td>{g.group}{g.too_small && <span className="text-xs"> (too few)</span>}</td>
                <td className="tabular-nums">{g.n}</td><td className="tabular-nums">{pct(g.placement_rate)}</td><td className="tabular-nums">{pct(g.mean_predicted)}</td>
                <td className="tabular-nums">{n3(g.auc)}</td><td className="tabular-nums">{n3(g.tpr)}</td><td className="tabular-nums">{n3(g.fpr)}</td>
              </tr>
            ))}
          </Table>
          {a.flags.length > 0 && <p className="mt-1.5 text-xs text-faint">! Gaps above {n3(fairness.flag_thresholds.auc_gap)} are flagged for discussion in the report. They may reflect small groups or real differences in the data, not necessarily model bias.</p>}
        </div>
      ))}
    </Section>
  );
}

export function CellEvaluation() {
  const [model, setModel] = useState<ModelMetrics | null>(null);
  const [ext, setExt] = useState<ExtractionMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { adminApi.metrics().then((r) => { setModel(r.model); setExt(r.extraction); }).catch((e) => setError((e as Error).message)); }, []);

  async function rerun() {
    setBusy(true); setError(null);
    try { setExt(await adminApi.evaluateAnnotations()); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  const bc = model?.baseline_comparison;
  return (
    <>
      {error && <Notice tone="error">{error}</Notice>}
      <Section title="Skill extraction study (§4.3)" action={<Button variant="outline" size="sm" onClick={rerun} disabled={busy}>{busy ? "Evaluating…" : "Re-run on saved annotations"}</Button>}>
        {!ext ? <p className="text-sm text-muted">No evaluation yet. Annotate resumes on the Annotate tab, then re-run.</p> : (
          <>
            <p className="text-xs text-faint">{ext.n_documents} resumes · {ext.source} · {new Date(ext.evaluated_at).toLocaleString()}</p>
            {ext.synthetic_data && <Notice>These annotations are synthetic demo data, and synthetic resumes are far easier than real ones. Annotate 50 real resumes for the reported figure.</Notice>}
            <Tiles>
              <Tile label={<>{ext.meets_target ? "✓" : "✕"} Micro F1 (target &gt; {ext.target_f1})</>} value={n3(ext.micro.f1)} />
              <Tile label="Precision" value={n3(ext.micro.precision)} />
              <Tile label="Recall" value={n3(ext.micro.recall)} />
              <Tile label="F1 without fuzzy matching" value={n3(ext.ablation_without_fuzzy.f1)} hint="ablation" />
            </Tiles>
            <div className="mt-4 grid gap-5 md:grid-cols-2">
              <div>
                <h3 className="mb-1 text-xs font-semibold text-muted">Precision by matching method</h3>
                <Table head={["Method", "Correct / predicted", "Precision"]}>
                  {Object.entries(ext.precision_by_method).map(([k, v]) => <tr key={k}><td>{k}</td><td className="tabular-nums">{v.correct} / {v.predicted}</td><td className="tabular-nums">{n3(v.precision)}</td></tr>)}
                </Table>
              </div>
              <div>
                <h3 className="mb-1 text-xs font-semibold text-muted">Most frequent errors</h3>
                <Table head={["False positives", "False negatives"]}>
                  {Array.from({ length: Math.max(ext.top_false_positives.length, ext.top_false_negatives.length, 1) }).slice(0, 8).map((_, i) => (
                    <tr key={i}>
                      <td>{ext.top_false_positives[i] ? `${ext.top_false_positives[i][0]} (${ext.top_false_positives[i][1]})` : i === 0 ? "none" : ""}</td>
                      <td>{ext.top_false_negatives[i] ? `${ext.top_false_negatives[i][0]} (${ext.top_false_negatives[i][1]})` : i === 0 ? "none" : ""}</td>
                    </tr>
                  ))}
                </Table>
              </div>
            </div>
          </>
        )}
      </Section>

      <Section title="Baseline comparison: similarity vs outcome-trained classifier (§4.6)">
        <p className="text-sm text-muted">
          Hypothesis: resume–JD similarity (and LLM job-fit scores) correlate weakly with actual placement, while the outcome-trained classifier correlates
          substantially more strongly. Classifier scores are out-of-fold, so no student is scored by a model that saw them.
        </p>
        {!model ? <p className="mt-2 text-sm text-faint">Train a model first.</p>
          : !bc ? <p className="mt-2 text-sm text-faint">The training data had no <code>sim_*</code> columns. Run data intake (<code>python -m placeiq ingest</code>) with resumes and <code>jd_id</code>s to compute them.</p>
          : bc.skipped ? <p className="mt-2 text-sm text-faint">Skipped: {bc.skipped}</p>
          : (
            <>
              <ModelNotice m={model} />
              <div className="mt-3">
                <Table head={["Signal", "ROC-AUC", "Point-biserial r", "p-value", "Classifier AUC minus this [95% CI]", "Verdict"]}>
                  {Object.entries(bc.signals ?? {}).sort((a, b) => b[1].roc_auc - a[1].roc_auc).map(([sig, v]) => {
                    const d = bc.classifier_vs_similarity?.[sig];
                    const vd = d && verdict(d.ci95);
                    return (
                      <tr key={sig}>
                        <td>{signalLabel[sig] ?? sig}</td>
                        <td className="tabular-nums">{n3(v.roc_auc)}</td>
                        <td className="tabular-nums">{signed(v.point_biserial_r)}</td>
                        <td className="tabular-nums">{v.p_value < 0.001 ? "< 0.001" : v.p_value.toFixed(3)}</td>
                        <td className="tabular-nums">{d ? `${signed(d.auc_diff)} [${signed(d.ci95[0])}, ${signed(d.ci95[1])}]` : "(reference)"}</td>
                        <td className={vd?.cls}>{vd?.text ?? ""}</td>
                      </tr>
                    );
                  })}
                </Table>
              </div>
              <p className="mt-2 text-xs text-faint">n = {bc.n} students with both scores; 2,000 paired bootstrap resamples. A null or negative result is still a valid finding.</p>
            </>
          )}
      </Section>

      {model && <FairnessAudit fairness={model.fairness} />}
    </>
  );
}
