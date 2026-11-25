"""Fairness audit of the classifier across student groups (branch, gender, batch).

Uses out-of-fold probabilities, so each student is scored by a model that never saw them.
Per group: size, actual placement rate, mean predicted probability (calibration-in-the-large),
ROC-AUC, and at the 0.5 threshold the true-positive rate (placed students correctly flagged)
and false-positive rate. Disparities reported:
  - AUC gap            max - min AUC: does the model rank students equally well in every group?
  - TPR gap            "equal opportunity" difference
  - FPR gap            difference in false alarms
  - calibration gap    largest |mean predicted - actual rate| across groups
Groups under MIN_GROUP students are listed but excluded from the gaps, because their metrics
are too noisy to compare. Sensitive attributes (e.g. gender) are never model features.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

MIN_GROUP = 15
THRESHOLD = 0.5
# Gaps above these are flagged for discussion in the report (common rules of thumb).
FLAG = {"auc_gap": 0.10, "tpr_gap": 0.10, "fpr_gap": 0.10, "calibration_gap": 0.10}


def _rate(num: int, den: int) -> float | None:
    return round(num / den, 4) if den else None


def group_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    pred = p >= THRESHOLD
    pos, neg = y == 1, y == 0
    return {
        "n": int(len(y)),
        "placement_rate": round(float(y.mean()), 4),
        "mean_predicted": round(float(p.mean()), 4),
        "auc": round(float(roc_auc_score(y, p)), 4) if len(np.unique(y)) == 2 else None,
        "tpr": _rate(int((pred & pos).sum()), int(pos.sum())),
        "fpr": _rate(int((pred & neg).sum()), int(neg.sum())),
    }


def audit(df: pd.DataFrame, prob_col: str, attributes: list[str]) -> dict:
    out = {}
    for attr in attributes:
        if attr not in df.columns:
            continue
        col = df[attr].astype(object).where(df[attr].notna(), "").astype(str).str.strip()
        groups = []
        for value in sorted(v for v in col.unique() if v and v.lower() not in ("nan", "none")):
            mask = (col == value).to_numpy()
            m = group_metrics(df.loc[mask, "placed"].to_numpy(dtype=int), df.loc[mask, prob_col].to_numpy(dtype=float))
            m["group"] = value
            m["too_small"] = m["n"] < MIN_GROUP
            groups.append(m)
        usable = [g for g in groups if not g["too_small"]]

        def gap(key):
            vals = [g[key] for g in usable if g[key] is not None]
            return round(max(vals) - min(vals), 4) if len(vals) >= 2 else None

        gaps = {"auc_gap": gap("auc"), "tpr_gap": gap("tpr"), "fpr_gap": gap("fpr"),
                "calibration_gap": round(max(abs(g["mean_predicted"] - g["placement_rate"]) for g in usable), 4)
                if usable else None}
        out[attr] = {"groups": groups, **gaps,
                     "flags": [k for k, v in gaps.items() if v is not None and v > FLAG[k]],
                     "comparable_groups": len(usable)}
    return {"threshold": THRESHOLD, "min_group": MIN_GROUP, "flag_thresholds": FLAG, "attributes": out}
