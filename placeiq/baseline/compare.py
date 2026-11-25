"""The core experiment (synopsis §4.6): which signal predicts placement — similarity or PlaceIQ?

    python -m placeiq.baseline.compare --scores placeiq-data/processed/similarity_scores.csv \
        --oof placeiq-data/artifacts/oof_predictions.csv

`--scores`: student_hash plus sim_* columns (from SimilarityBaseline.score_resume at ingestion).
`--oof`: written by placeiq.model.train; out-of-fold classifier probabilities, so the
classifier is never scored on students it was trained on.
Reports, per signal: ROC-AUC with bootstrap CI, point-biserial correlation with the outcome,
and the paired-bootstrap AUC difference vs the classifier. A null or negative result is
still a reportable finding.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
from scipy.stats import pointbiserialr
from sklearn.metrics import roc_auc_score

from placeiq.config import RANDOM_STATE


def paired_auc_diff(y, a, b, n_boot: int = 2000, seed: int = RANDOM_STATE) -> dict:
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(y[idx])) < 2:
            continue
        diffs.append(roc_auc_score(y[idx], a[idx]) - roc_auc_score(y[idx], b[idx]))
    diffs = np.array(diffs)
    return {"auc_diff": round(float(roc_auc_score(y, a) - roc_auc_score(y, b)), 4),
            "ci95": [round(float(np.percentile(diffs, 2.5)), 4), round(float(np.percentile(diffs, 97.5)), 4)],
            "p_not_better": round(float((diffs <= 0).mean()), 4)}


def compare(df: pd.DataFrame, classifier_col: str = "oof_logistic_regression") -> dict:
    y = df["placed"].astype(int).to_numpy()
    signals = [c for c in df.columns if c.startswith("sim_")] + [classifier_col]
    out = {"n": int(len(y)), "signals": {}, "classifier_vs_similarity": {}}
    for s in signals:
        x = df[s].to_numpy(dtype=float)
        r, p = pointbiserialr(y, x)
        out["signals"][s] = {"roc_auc": round(float(roc_auc_score(y, x)), 4),
                             "point_biserial_r": round(float(r), 4), "p_value": round(float(p), 4)}
    clf = df[classifier_col].to_numpy(dtype=float)
    for s in signals[:-1]:
        out["classifier_vs_similarity"][s] = paired_auc_diff(y, clf, df[s].to_numpy(dtype=float))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", required=True)
    ap.add_argument("--oof", default="placeiq-data/artifacts/oof_predictions.csv")
    args = ap.parse_args()
    merged = pd.read_csv(args.oof).merge(pd.read_csv(args.scores), on="student_hash", how="inner")
    print(json.dumps(compare(merged), indent=2))
