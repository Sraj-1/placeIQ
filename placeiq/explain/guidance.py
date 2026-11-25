"""SHAP attributions → ranked, traceable guidance (synopsis §4.5).

Rules enforced here:
  - every guidance item carries the feature, its value and its SHAP contribution, so 100%
    of guidance is traceable to a computed attribution (Table 1);
  - only modifiable features produce recommendations;
  - text is template-filled from computed numbers; nothing generates numbers.
Contributions are in log-odds for logistic regression (additive, signed).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import joblib
import numpy as np
import pandas as pd
import shap

from placeiq.config import MODEL_PATH
from placeiq.features.assemble import CATEGORICAL, build_features, modifiable_features

_TEMPLATES = {
    "cgpa": "CGPA of {value:g} is lowering your estimate (contribution {contribution:+.2f}). Raising remaining-semester SGPA has the largest academic effect.",
    "active_backlogs": "{value:g} active backlog(s) lower your estimate (contribution {contribution:+.2f}). Clearing them is the most direct fix; most recruiters filter on this.",
    "internships": "{value:g} internship(s) on record (contribution {contribution:+.2f}). Peers with more internship exposure score higher.",
    "projects": "{value:g} project(s) listed (contribution {contribution:+.2f}). Add a substantial, deployable project.",
    "certifications": "{value:g} certification(s) (contribution {contribution:+.2f}). A relevant certification would help.",
    "n_skills": "{value:g} recognised skills on your resume (contribution {contribution:+.2f}). List the tools you have actually used.",
}
_SKILL_CAT_TEMPLATE = "{value:g} skill(s) in {label} (contribution {contribution:+.2f}). Building depth here would raise your estimate."


@dataclass
class Attribution:
    feature: str
    value: float | str
    contribution: float


@dataclass
class GuidanceItem:
    feature: str
    value: float
    contribution: float
    message: str


def load_bundle(path=MODEL_PATH) -> dict:
    return joblib.load(path)


def _group_onehot(names: list[str], values: np.ndarray, row: pd.Series) -> list[Attribution]:
    """Collapse one-hot columns ("cat__branch_CSE") back to one attribution per raw feature."""
    grouped: dict[str, float] = {}
    for name, v in zip(names, values):
        raw = name.split("__", 1)[1]
        for cat in CATEGORICAL:
            if raw.startswith(f"{cat}_"):
                raw = cat
        grouped[raw] = grouped.get(raw, 0.0) + float(v)
    return [Attribution(f, row[f] if f in CATEGORICAL else float(row[f]), round(c, 4)) for f, c in grouped.items()]


def explain(bundle: dict, records: pd.DataFrame) -> list[dict]:
    """Return probability + per-feature attributions for each record."""
    model = bundle["model"]
    X = build_features(records)
    if bundle["model_name"] == "ensemble":
        rows, bases = model.explain(X)
        probs = model.predict_proba(X)[:, 1]
        out = []
        for i in range(len(X)):
            attrs = []
            for feat in sorted(set(rows[i]) | {"cgpa", "active_backlogs", "internships", "projects", "certifications", "branch"}):
                value = X.iloc[i][feat] if feat in CATEGORICAL else float(X.iloc[i][feat])
                attrs.append(Attribution(feat, value, round(rows[i].get(feat, 0.0), 4)))
            out.append({"probability": round(float(probs[i]), 4), "base_value": round(bases[i], 4),
                        "attributions": sorted(attrs, key=lambda a: a.contribution)})
        return out
    pre, clf = model.named_steps["pre"], model.named_steps["clf"]
    Xt = pre.transform(X)
    bg = pre.transform(bundle["background"])
    names = list(pre.get_feature_names_out())

    if bundle["model_name"] == "logistic_regression":
        explainer = shap.LinearExplainer(clf, bg)
        sv = explainer.shap_values(Xt)
        base = float(np.ravel(explainer.expected_value)[0])
    else:
        explainer = shap.TreeExplainer(clf)
        sv = explainer.shap_values(Xt)
        sv = sv[..., 1] if np.ndim(sv) == 3 else sv[1]
        base = float(np.ravel(explainer.expected_value)[-1])

    probs = model.predict_proba(X)[:, 1]
    out = []
    for i in range(len(X)):
        attrs = _group_onehot(names, np.asarray(sv[i]), X.iloc[i])
        out.append({"probability": round(float(probs[i]), 4), "base_value": round(base, 4),
                    "attributions": sorted(attrs, key=lambda a: a.contribution)})
    return out


def guidance_from_attributions(attrs: list[Attribution], top_k: int = 5,
                               improves: dict[str, bool] | None = None) -> list[GuidanceItem]:
    """`improves` (feature → bool) comes from the model: does a realistic step in the advised
    direction actually raise the estimate? A feature can contribute negatively *because* it is
    above average with a negative weight (e.g. noise on a skill category); advising more of it
    would then be false, so such features are left out."""
    allowed = modifiable_features()
    items = []
    for a in sorted(attrs, key=lambda a: a.contribution):
        if a.contribution >= 0 or a.feature not in allowed:
            continue
        if improves is not None and not improves.get(a.feature, False):
            continue
        if a.feature.startswith("skills_"):
            label = a.feature.removeprefix("skills_").replace("_", " ")
            msg = _SKILL_CAT_TEMPLATE.format(value=a.value, label=label, contribution=a.contribution)
        else:
            msg = _TEMPLATES[a.feature].format(value=a.value, contribution=a.contribution)
        items.append(GuidanceItem(a.feature, float(a.value), a.contribution, msg))
    return items[:top_k]


_STEP_FOR_FEATURE = {"internships": "internships", "projects": "projects", "certifications": "certifications",
                     "active_backlogs": "active_backlogs", "cgpa": "cgpa_0.25"}


def improvement_check(bundle: dict, record: dict) -> dict[str, bool]:
    """For each modifiable feature: does one realistic step in the advised direction raise the
    model's probability for this student? Uses the same candidate steps as the what-if simulator."""
    from placeiq.explain.whatif import MIN_GAIN, candidate_changes, score

    base = score(bundle, [record])[0]
    changes = candidate_changes(record)
    gains = dict(zip((c["key"] for c in changes), (p - base for p in score(bundle, [c["profile"] for c in changes]))))
    out = {f: gains.get(k, 0.0) >= MIN_GAIN for f, k in _STEP_FOR_FEATURE.items()}
    skill_gains = {k.removeprefix("skill_"): g for k, g in gains.items() if k.startswith("skill_")}
    for cat, g in skill_gains.items():
        out[f"skills_{cat}"] = g >= MIN_GAIN
    out["n_skills"] = any(g >= MIN_GAIN for g in skill_gains.values())
    return out


def report(bundle: dict, record: dict) -> dict:
    """Full student-facing report for one corrected profile."""
    res = explain(bundle, pd.DataFrame([record]))[0]
    improves = improvement_check(bundle, record)
    return {
        "probability": res["probability"],
        "base_value": res["base_value"],
        "attributions": [asdict(a) for a in res["attributions"]],
        "guidance": [asdict(g) for g in guidance_from_attributions(res["attributions"], improves=improves)],
    }
