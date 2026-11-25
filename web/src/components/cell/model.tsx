"use client";
// PlaceIQ placement cell: train and deploy the classifier; metrics, coefficients, figures.
import { useEffect, useState } from "react";
import { adminApi, featureLabel, type ModelMetrics } from "@/lib/client";
import { Badge, Button, DivergingBars, Notice, Section, Table, Tile, Tiles, inputCls, n3, pct, signed } from "@/components/ui";
import { Figure } from "@/components/figure";

const MODEL_NAMES: Record<string, string> = { logistic_regression: "Logistic regression", random_forest: "Random forest" };

export function ModelNotice({ m }: { m: ModelMetrics }) {
  if (m.synthetic_data) return <Notice>This model was trained on <strong>synthetic demo data</strong>. Its numbers prove the pipeline works, not that anything predicts placement. Don&apos;t report them.</Notice>;
  if (m.indicative_only) return <Notice tone="info">Trained on {m.n_records} records (fewer than 150). Report results as indicative, with the confidence intervals shown.</Notice>;
  if (m.public_data) return (
    <Notice tone="info">
      Trained on <strong>public placement datasets</strong> ({m.data_sources?.map((d) => `${d.title ?? d.source}: ${d.rows.toLocaleString()}`).join("; ")}), with one
      sub-model per dataset. These are not your college&apos;s records: retrain on real data before reporting results as findings.
    </Notice>
  );
  return null;
}

export function CellModel({ onTrained, trainingEnabled = true }: { onTrained: () => void; trainingEnabled?: boolean }) {
  const [m, setM] = useState<ModelMetrics | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [primary, setPrimary] = useState("logistic_regression");
  const [busy, setBusy] = useState(false);

  useEffect(() => { adminApi.metrics().then((r) => setM(r.model)).catch((e) => setError((e as Error).message)).finally(() => setLoaded(true)); }, []);

  async function train() {
    if (!file) return;
    setBusy(true); setError(null);
    try { setM(await adminApi.train(file, primary)); setFile(null); onTrained(); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  const p = m?.models[m.primary_model];
  return (
    <>
      {!trainingEnabled ? (
        <Section title="Train the classifier">
          <Notice tone="info">
            Retraining is turned off on this online deployment (the free server is too small). To use new data: run PlaceIQ on your
            own computer with <code>start.bat</code>, train on the Model page there, then redeploy so the new model is built into the app.
          </Notice>
        </Section>
      ) : (
      <Section title="Train the classifier">
        <p className="text-sm text-muted">
          Upload the anonymised historical CSV from data intake (<code>python -m placeiq ingest</code>) (layout:
          <code> placeiq-data/templates/historical_records_template.csv</code>). Training runs repeated stratified 5-fold
          cross-validation for logistic regression and random forest, then replaces the live model. With <code>sim_*</code> columns
          the baseline comparison runs too.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <input type="file" accept=".csv,text/csv" aria-label="Historical records CSV" className="text-sm" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <select aria-label="Model to deploy" className={`${inputCls} w-auto`} value={primary} onChange={(e) => setPrimary(e.target.value)}>
            <option value="logistic_regression">Deploy: logistic regression (recommended)</option>
            <option value="random_forest">Deploy: random forest</option>
          </select>
          <Button onClick={train} disabled={!file || busy}>{busy ? "Training… (up to a minute)" : "Train and deploy"}</Button>
        </div>
        {error && <Notice tone="error">{error}</Notice>}
      </Section>
      )}

      {loaded && !m && !error && <Section><p className="text-sm text-muted">No model trained yet. Upload a historical CSV above, or run <code>python -m placeiq demo</code>.</p></Section>}

      {m && p && (
        <>
          <ModelNotice m={m} />
          <Tiles>
            <Tile label="Records" value={m.n_records} hint={`${pct(m.positive_rate)} placed`} />
            <Tile label={`CV ROC-AUC (${MODEL_NAMES[m.primary_model]})`} value={n3(p.roc_auc_mean)} hint={`± ${n3(p.roc_auc_sd)} · target > 0.70`} />
            <Tile label="Out-of-fold AUC, 95% CI" value={n3(p.oof_roc_auc)} hint={`${n3(p.oof_roc_auc_95ci[0])} – ${n3(p.oof_roc_auc_95ci[1])}`} />
            <Tile label="Trained" value={<span className="text-base">{new Date(m.trained_at).toLocaleString()}</span>} hint={m.source} />
          </Tiles>
          <Section title="Model comparison (cross-validated)">
            <Table head={["Model", "ROC-AUC", "OOF AUC [95% CI]", "Precision / recall: placed", "Precision / recall: not placed", "Accuracy (majority baseline)"]}>
              {Object.entries(m.models).map(([name, r]) => (
                <tr key={name}>
                  <td>{MODEL_NAMES[name] ?? name}{name === m.primary_model && <Badge tone="info" className="ml-2">deployed</Badge>}</td>
                  <td className="tabular-nums">{n3(r.roc_auc_mean)} ± {n3(r.roc_auc_sd)}</td>
                  <td className="tabular-nums">{n3(r.oof_roc_auc)} [{n3(r.oof_roc_auc_95ci[0])}, {n3(r.oof_roc_auc_95ci[1])}]</td>
                  <td className="tabular-nums">{n3(r.classification_report.placed.precision)} / {n3(r.classification_report.placed.recall)}</td>
                  <td className="tabular-nums">{n3(r.classification_report.not_placed.precision)} / {n3(r.classification_report.not_placed.recall)}</td>
                  <td className="tabular-nums">{n3(r.accuracy)} ({n3(r.majority_class_accuracy)})</td>
                </tr>
              ))}
            </Table>
            <p className="mt-2 text-xs text-faint">
              Random forest minus logistic regression: AUC {signed(m.random_forest_vs_logistic.auc_diff)} (95% CI {signed(m.random_forest_vs_logistic.ci95[0])} to {signed(m.random_forest_vs_logistic.ci95[1])}).{" "}
              {m.random_forest_vs_logistic.ci95[0] > 0 ? "Non-linear interactions add a measurable gain." : "The interval includes zero, so non-linear interactions add no measurable gain. The simpler, explainable model is justified."}
            </p>
          </Section>
          <div className="grid gap-x-5 lg:grid-cols-2">
            <Section title="Logistic regression coefficients">
              <p className="mb-3 text-xs text-faint">Standardised: change in log-odds of placement per 1 SD of each feature.</p>
              <DivergingBars legend={["Raises placement odds", "Lowers placement odds"]} fmt={(v) => signed(v, 2)}
                items={m.coefficients.slice(0, 12).map((c) => ({ label: featureLabel(c.feature), value: c.coefficient }))} />
            </Section>
            <Section title="Confusion matrix"><Figure name="confusion_matrix.png" alt="Confusion matrix of the deployed model" version={m.trained_at} /></Section>
          </div>
          <div className="grid gap-x-5 lg:grid-cols-2">
            <Section title="ROC curves"><Figure name="roc_curves.png" alt="ROC curves for classifiers and similarity signals" version={m.trained_at} /></Section>
            <Section title="Calibration"><Figure name="calibration.png" alt="Calibration curve" version={m.trained_at} /></Section>
          </div>
          <p className="mt-3 text-xs text-faint">Figures are saved in <code>placeiq-data/artifacts/figures/</code> for the project report.</p>
        </>
      )}
    </>
  );
}
