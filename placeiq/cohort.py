"""Batch aggregation for the placement-cell dashboard (synopsis §3.2 objective 6).

Training groups: each student is assigned to the *modifiable* factor that lowers their
estimate the most (their SHAP attribution). Counting students per factor tells the
placement cell which training sessions would reach the most people. Students with no
negative modifiable factor form the "no major gap" group.
"""
from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np
import pandas as pd

from placeiq.explain.guidance import explain
from placeiq.features.assemble import modifiable_features, parse_skills

READINESS_BANDS = [(0.0, 0.4, "at_risk"), (0.4, 0.7, "borderline"), (0.7, 1.01, "ready")]
NO_GAP = "none"


def band(p: float) -> str:
    return next(label for lo, hi, label in READINESS_BANDS if lo <= p < hi)


def primary_gap(attributions) -> tuple[str, float]:
    """The modifiable feature with the most negative contribution, or ("none", 0)."""
    allowed = modifiable_features()
    worst = min((a for a in attributions if a.feature in allowed and a.contribution < 0),
                key=lambda a: a.contribution, default=None)
    return (worst.feature, worst.contribution) if worst else (NO_GAP, 0.0)


def primary_gaps(bundle: dict, records: pd.DataFrame) -> list[str]:
    return [primary_gap(r["attributions"])[0] for r in explain(bundle, records)]


def training_groups(results: list[dict]) -> list[dict]:
    groups: dict[str, dict] = defaultdict(lambda: {"students": 0, "probs": [], "contribs": [], "bands": Counter()})
    for r in results:
        feature, contribution = primary_gap(r["attributions"])
        g = groups[feature]
        g["students"] += 1
        g["probs"].append(r["probability"])
        g["contribs"].append(contribution)
        g["bands"][band(r["probability"])] += 1
    n = len(results) or 1
    out = [{"feature": f, "students": g["students"], "share": round(g["students"] / n, 4),
            "mean_probability": round(float(np.mean(g["probs"])), 4),
            "mean_contribution": round(float(np.mean(g["contribs"])), 4),
            "at_risk": g["bands"]["at_risk"], "borderline": g["bands"]["borderline"], "ready": g["bands"]["ready"]}
           for f, g in groups.items()]
    # Biggest actionable groups first; "no major gap" last.
    return sorted(out, key=lambda g: (g["feature"] == NO_GAP, -g["students"]))


def summarize(bundle: dict, records: pd.DataFrame, top_n: int = 10) -> dict:
    results = explain(bundle, records)
    probs = np.array([r["probability"] for r in results])

    # Which factors pull the batch down most: mean negative contribution per feature.
    drag: Counter = Counter()
    for r in results:
        for a in r["attributions"]:
            if a.contribution < 0:
                drag[a.feature] += a.contribution
    n = len(results)

    skill_freq = Counter(s for v in records["skills"] for s in set(parse_skills(v)))
    return {
        "n_students": n,
        "mean_probability": round(float(probs.mean()), 4) if n else None,
        "bands": dict(Counter(band(p) for p in probs)),
        "by_branch": records.assign(p=probs).groupby("branch")["p"].agg(["count", "mean"]).round(4)
                            .reset_index().to_dict("records"),
        "top_negative_factors": [{"feature": f, "mean_contribution": round(v / n, 4)}
                                 for f, v in sorted(drag.items(), key=lambda kv: kv[1])[:top_n]],
        "training_groups": training_groups(results),
        "skill_coverage": [{"skill": s, "share": round(c / n, 4)} for s, c in skill_freq.most_common(top_n * 3)],
    }
