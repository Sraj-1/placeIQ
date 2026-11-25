"""SourceEnsemble: one sub-model per dataset, each trained only on the columns that dataset has.

When training data comes from several sources with different columns (e.g. one public dataset
has backlogs and branch, another has projects and certifications), imputing the missing columns
would invent data. Instead each member is fit on the rows where its own columns are observed,
and predictions average the members' log-odds (equal weights). A student who enters every field
gets the combined view; a training row is scored only by the members that can see it.

For logistic-regression members, explanations are exact and additive (the same quantity SHAP's
LinearExplainer gives for a linear model): contribution_j = Σ_m w_m · coef_mj · (z_mj − mean_mj),
on each member's standardised features. Random-forest members are supported for the
cross-validated comparison only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from placeiq.config import RANDOM_STATE

# The two public datasets' observed columns (see placeiq.data.public).
DEFAULT_MEMBERS = (
    ("college_placement", ("cgpa", "internships", "active_backlogs"), ("branch",)),
    ("campus_recruitment", ("cgpa", "internships", "projects", "certifications"), ()),
)


def _observed(X: pd.DataFrame, num: tuple, cat: tuple) -> np.ndarray:
    mask = X[list(num)].notna().all(axis=1).to_numpy().copy() if num else np.ones(len(X), bool)
    for c in cat:
        v = X[c].astype(str).str.strip().str.lower()
        mask = mask & ~v.isin(["", "nan", "none"]).to_numpy()
    return mask


class SourceEnsemble(ClassifierMixin, BaseEstimator):
    def __init__(self, members=DEFAULT_MEMBERS, kind="lr"):
        self.members = members
        self.kind = kind

    def _make(self, num, cat):
        pre = ColumnTransformer([("num", StandardScaler(), list(num))]
                                + ([("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), list(cat))] if cat else []))
        clf = (LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000) if self.kind == "lr"
               else RandomForestClassifier(n_estimators=300, min_samples_leaf=5, class_weight="balanced",
                                           random_state=RANDOM_STATE, n_jobs=-1))
        return Pipeline([("pre", pre), ("clf", clf)])

    def fit(self, X: pd.DataFrame, y):
        y = np.asarray(y).astype(int)
        self.classes_ = np.array([0, 1])
        self.fitted_ = []
        for name, num, cat in self.members:
            mask = _observed(X, num, cat)
            if mask.sum() < 20 or len(np.unique(y[mask])) < 2:
                continue
            pipe = clone(self._make(num, cat)).fit(X.loc[mask, list(num) + list(cat)], y[mask])
            Z = pipe.named_steps["pre"].transform(X.loc[mask, list(num) + list(cat)])
            self.fitted_.append({"name": name, "num": tuple(num), "cat": tuple(cat), "pipe": pipe,
                                 "zmean": Z.mean(axis=0), "n": int(mask.sum())})
        if not self.fitted_:
            raise ValueError("No ensemble member had enough observed rows to train.")
        return self

    def _member_logits(self, X: pd.DataFrame):
        out = []
        for m in self.fitted_:
            mask = _observed(X, m["num"], m["cat"])
            logit = np.full(len(X), np.nan)
            if mask.any():
                p = m["pipe"].predict_proba(X.loc[mask, list(m["num"]) + list(m["cat"])])[:, 1]
                p = np.clip(p, 1e-6, 1 - 1e-6)
                logit[mask] = np.log(p / (1 - p))
            out.append(logit)
        return np.vstack(out)

    def decision_function(self, X: pd.DataFrame) -> np.ndarray:
        L = self._member_logits(X)
        with np.errstate(invalid="ignore"):
            avg = np.nanmean(L, axis=0)
        return np.nan_to_num(avg, nan=0.0)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        p = 1 / (1 + np.exp(-self.decision_function(X)))
        return np.column_stack([1 - p, p])

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)

    # ---- explanations (logistic-regression members only) -------------------------
    def explain(self, X: pd.DataFrame) -> tuple[list[dict[str, float]], list[float]]:
        """Per-row additive log-odds contributions by raw feature, and per-row base values."""
        if self.kind != "lr":
            raise ValueError("Explanations are available for the logistic-regression ensemble only.")
        rows = [dict() for _ in range(len(X))]
        bases = np.zeros(len(X))
        counts = np.zeros(len(X))
        for m in self.fitted_:
            mask = _observed(X, m["num"], m["cat"])
            counts += mask
        for m in self.fitted_:
            mask = _observed(X, m["num"], m["cat"])
            if not mask.any():
                continue
            pre, clf = m["pipe"].named_steps["pre"], m["pipe"].named_steps["clf"]
            Z = pre.transform(X.loc[mask, list(m["num"]) + list(m["cat"])])
            names = [n.split("__", 1)[1] for n in pre.get_feature_names_out()]
            raw = [next((c for c in m["cat"] if n.startswith(f"{c}_")), n) for n in names]
            coef = clf.coef_[0]
            base_m = float(clf.intercept_[0] + coef @ m["zmean"])
            contrib = (Z - m["zmean"]) * coef
            for i, row_idx in enumerate(np.flatnonzero(mask)):
                w = 1.0 / counts[row_idx]
                bases[row_idx] += w * base_m
                for j, feat in enumerate(raw):
                    rows[row_idx][feat] = rows[row_idx].get(feat, 0.0) + w * float(contrib[i, j])
        return rows, bases.tolist()

    def coefficient_table(self) -> list[dict]:
        """Standardised coefficients per member (weighted by 1/members), merged by feature name."""
        if self.kind != "lr":
            return []
        merged: dict[str, float] = {}
        w = 1.0 / len(self.fitted_)
        for m in self.fitted_:
            pre, clf = m["pipe"].named_steps["pre"], m["pipe"].named_steps["clf"]
            for n, c in zip(pre.get_feature_names_out(), clf.coef_[0]):
                key = n.split("__", 1)[1]
                merged[key] = merged.get(key, 0.0) + w * float(c)
        rows = [{"feature": k, "coefficient": round(v, 4)} for k, v in merged.items()]
        return sorted(rows, key=lambda r: -abs(r["coefficient"]))

    def member_summary(self) -> list[dict]:
        return [{"name": m["name"], "rows": m["n"], "features": list(m["num"]) + list(m["cat"])} for m in self.fitted_]
