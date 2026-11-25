"""Classifier training and evaluation (synopsis §4.4, §4.7).

    python -m placeiq.model.train --data placeiq-data/processed/historical.csv

- Primary: L2-regularised logistic regression, class_weight="balanced".
- Secondary: Random Forest, to test whether non-linear interactions add measurable gain.
- Repeated stratified k-fold CV; ROC-AUC (mean ± sd) is the headline metric.
- Out-of-fold predictions give per-class precision/recall, a confusion matrix and a
  bootstrap 95% CI on AUC (required if n < 150).
- Accuracy is reported for completeness next to the majority-class baseline, never alone.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold, cross_val_predict, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from placeiq.baseline.compare import compare, paired_auc_diff
from placeiq.model.fairness import audit as fairness_audit
from placeiq.config import ARTIFACTS_DIR, CV_FOLDS, METRICS_PATH, MODEL_PATH, RANDOM_STATE, TARGET
from placeiq.features.assemble import CATEGORICAL, build_features, numeric_features


def make_preprocessor() -> ColumnTransformer:
    return ColumnTransformer([
        ("num", StandardScaler(), numeric_features()),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL),
    ])


def needs_ensemble(df: pd.DataFrame) -> bool:
    """Multi-source data with columns missing by design (e.g. the public datasets) is trained with
    one sub-model per source instead of imputing values that were never observed."""
    return "source" in df.columns and df["source"].nunique() > 1


def make_models(ensemble: bool = False) -> dict:
    if ensemble:
        from placeiq.model.ensemble import SourceEnsemble
        return {"logistic_regression": SourceEnsemble(kind="lr"), "random_forest": SourceEnsemble(kind="rf")}
    return {
        "logistic_regression": Pipeline([
            ("pre", make_preprocessor()),
            ("clf", LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000)),
        ]),
        "random_forest": Pipeline([
            ("pre", make_preprocessor()),
            ("clf", RandomForestClassifier(n_estimators=400, min_samples_leaf=5, class_weight="balanced",
                                           random_state=RANDOM_STATE, n_jobs=-1)),
        ]),
    }


def bootstrap_auc_ci(y: np.ndarray, p: np.ndarray, n_boot: int = 2000, seed: int = RANDOM_STATE) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    aucs = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(y[idx])) < 2:
            continue
        aucs.append(roc_auc_score(y[idx], p[idx]))
    return float(np.percentile(aucs, 2.5)), float(np.percentile(aucs, 97.5))


def evaluate(model: Pipeline, X: pd.DataFrame, y: np.ndarray) -> tuple[dict, np.ndarray]:
    folds = min(CV_FOLDS, int(np.bincount(y).min()))
    if folds < 2:
        raise ValueError("Need at least 2 examples of each class for cross-validation.")
    rcv = RepeatedStratifiedKFold(n_splits=folds, n_repeats=5, random_state=RANDOM_STATE)
    aucs = cross_val_score(model, X, y, cv=rcv, scoring="roc_auc")
    oof = cross_val_predict(model, X, y, cv=StratifiedKFold(folds, shuffle=True, random_state=RANDOM_STATE),
                            method="predict_proba")[:, 1]
    pred = (oof >= 0.5).astype(int)
    lo, hi = bootstrap_auc_ci(y, oof)
    return {
        "cv_folds": folds,
        "roc_auc_mean": round(float(aucs.mean()), 4),
        "roc_auc_sd": round(float(aucs.std()), 4),
        "oof_roc_auc": round(float(roc_auc_score(y, oof)), 4),
        "oof_roc_auc_95ci": [round(lo, 4), round(hi, 4)],
        "classification_report": classification_report(y, pred, target_names=["not_placed", "placed"],
                                                       output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(y, pred).tolist(),
        "accuracy": round(float(accuracy_score(y, pred)), 4),
        "majority_class_accuracy": round(float(max(y.mean(), 1 - y.mean())), 4),
    }, oof


FAIRNESS_ATTRIBUTES = ["branch", "gender", "batch_year"]


def coefficient_table(model: Pipeline) -> list[dict]:
    """Standardised LR coefficients (log-odds per 1 SD, or per category vs others)."""
    clf = model.named_steps["clf"]
    if not hasattr(clf, "coef_"):
        return []
    names = model.named_steps["pre"].get_feature_names_out()
    rows = [{"feature": n.split("__", 1)[1], "coefficient": round(float(c), 4)} for n, c in zip(names, clf.coef_[0])]
    return sorted(rows, key=lambda r: -abs(r["coefficient"]))


def train(df: pd.DataFrame, primary: str = "logistic_regression", source: str = "uploaded data",
          make_plots: bool = True) -> dict:
    X = build_features(df)
    y = df[TARGET].astype(int).to_numpy()
    if len(np.unique(y)) < 2:
        raise ValueError("The outcome column needs both placed (1) and not placed (0) students.")
    synthetic = bool("is_synthetic" in df.columns and pd.to_numeric(df["is_synthetic"], errors="coerce").fillna(0).astype(bool).any())
    results = {"n_records": int(len(y)), "positive_rate": round(float(y.mean()), 4),
               "indicative_only": bool(len(y) < 150), "synthetic_data": synthetic, "source": source,
               "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "primary_model": primary, "models": {}}
    oof_preds = {}
    ensemble = needs_ensemble(df)
    if ensemble:
        if primary != "logistic_regression":
            raise ValueError("Multi-source data supports the logistic-regression ensemble only.")
        X = pd.concat([X.reset_index(drop=True), df[["source"]].reset_index(drop=True)], axis=1)
        counts = df["source"].value_counts().to_dict()
        results["public_data"] = bool(df["source"].astype(str).isin(["campus_recruitment", "college_placement"]).any())
        results["data_sources"] = [{"source": k, "rows": int(v)} for k, v in counts.items()]
        if results["public_data"]:
            from placeiq.data.public import DATA_NOTES, SOURCES
            for d in results["data_sources"]:
                d.update(SOURCES.get(d["source"], {}))
            results["data_notes"] = DATA_NOTES
    results["model_type"] = "per-source ensemble (logistic regression)" if ensemble else "logistic regression"
    for name, model in make_models(ensemble).items():
        results["models"][name], oof_preds[name] = evaluate(model, X, y)

    lr, rf = oof_preds["logistic_regression"], oof_preds["random_forest"]
    results["random_forest_vs_logistic"] = paired_auc_diff(y, rf, lr)

    final = make_models(ensemble)[primary].fit(X, y)
    if ensemble:
        results["coefficients"] = final.coefficient_table()
        results["ensemble_members"] = final.member_summary()
    else:
        results["coefficients"] = coefficient_table(make_models()["logistic_regression"].fit(X, y))

    oof = pd.DataFrame({"student_hash": df["student_hash"].values if "student_hash" in df else np.arange(len(df)),
                        "placed": y, **{f"oof_{k}": v for k, v in oof_preds.items()}})
    sim_cols = [c for c in df.columns if c.startswith("sim_")]
    for c in sim_cols:
        oof[c] = pd.to_numeric(df[c], errors="coerce").values
    if sim_cols:
        scored = oof.dropna(subset=sim_cols)
        if len(scored) >= 20 and scored["placed"].nunique() == 2:
            results["baseline_comparison"] = compare(scored)
        else:
            results["baseline_comparison"] = {"skipped": f"only {len(scored)} students have similarity scores"}

    # Fairness audit on out-of-fold predictions (audit-only columns; never model features).
    group_cols = [c for c in FAIRNESS_ATTRIBUTES if c in df.columns]
    for c in group_cols:
        oof[c] = df[c].values
    results["fairness"] = fairness_audit(oof, f"oof_{primary}", group_cols)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": final, "model_name": "ensemble" if ensemble else primary,
                 "background": X.sample(min(100, len(X)), random_state=RANDOM_STATE),
                 "synthetic_data": synthetic, "trained_at": results["trained_at"]}, MODEL_PATH)
    oof.to_csv(ARTIFACTS_DIR / "oof_predictions.csv", index=False)
    if make_plots:
        from placeiq.reporting import make_figures
        results["figures"] = make_figures(oof, results, ARTIFACTS_DIR / "figures")
    METRICS_PATH.write_text(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--primary", default="logistic_regression", choices=list(make_models()))
    args = ap.parse_args()
    res = train(pd.read_csv(args.data), args.primary, source=args.data)
    print(f"n={res['n_records']}  positive rate={res['positive_rate']}  indicative_only={res['indicative_only']}")
    for name, m in res["models"].items():
        print(f"{name:20s} AUC {m['roc_auc_mean']:.3f} ± {m['roc_auc_sd']:.3f}  "
              f"(OOF {m['oof_roc_auc']:.3f}, 95% CI {m['oof_roc_auc_95ci']})  "
              f"acc {m['accuracy']:.3f} vs majority {m['majority_class_accuracy']:.3f}")
    if res["synthetic_data"]:
        print("NOTE: trained on SYNTHETIC data. These numbers are not results.")
    bc = res.get("baseline_comparison", {})
    for sig, v in bc.get("signals", {}).items():
        print(f"  signal {sig:28s} AUC {v['roc_auc']:.3f}  r_pb {v['point_biserial_r']:+.3f}")
    print(f"Saved model → {MODEL_PATH}, metrics → {METRICS_PATH}")
