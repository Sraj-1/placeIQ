"""Feature assembly (synopsis §4.1, §4.4).

With ~200 records, one binary column per skill (160+) would overfit badly, so skills enter
the model as per-category counts plus a total. Individual skills still drive the
eligibility filter and the cohort skill-gap view.

`rounds_cleared` is deliberately excluded: it is measured during the placement process and
is almost a restatement of the outcome, so using it would leak the label.
"""
from __future__ import annotations

import pandas as pd

from placeiq.extraction.skills import skill_categories

NUMERIC_BASE = ["cgpa", "active_backlogs", "internships", "projects", "certifications"]
CATEGORICAL = ["branch"]
LEAKY_COLUMNS = {"rounds_cleared", "placed"}
# Audit-only attributes: used for the fairness audit, never as model inputs.
SENSITIVE_COLUMNS = {"gender"}

# Features a student can still change before placement season. Branch is fixed; CGPA is
# treated as modifiable but guidance should phrase it as "protect/raise remaining SGPA".
MODIFIABLE = {"cgpa", "active_backlogs", "internships", "projects", "certifications", "n_skills"}


def category_names() -> list[str]:
    return sorted(set(skill_categories().values()))


def skill_feature_names() -> list[str]:
    return ["n_skills"] + [f"skills_{c}" for c in category_names()]


def numeric_features() -> list[str]:
    return NUMERIC_BASE + skill_feature_names()


def modifiable_features() -> set[str]:
    return MODIFIABLE | {f"skills_{c}" for c in category_names()}


def parse_skills(value) -> list[str]:
    if isinstance(value, (list, set, tuple)):
        return [str(s).strip().lower() for s in value if str(s).strip()]
    if not isinstance(value, str) or not value.strip():
        return []
    return [s.strip().lower() for s in value.split(";") if s.strip()]


def skill_counts(skills: list[str]) -> dict[str, int]:
    cats = skill_categories()
    counts = {f"skills_{c}": 0 for c in category_names()}
    known = [s for s in set(skills) if s in cats]
    for s in known:
        counts[f"skills_{cats[s]}"] += 1
    counts["n_skills"] = len(known)
    return counts


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Records (one row per student, `skills` as ';'-joined string or list) → model input."""
    missing = [c for c in NUMERIC_BASE + CATEGORICAL + ["skills"] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    skills = df["skills"].apply(parse_skills).apply(skill_counts).apply(pd.Series)
    out = pd.concat([df[NUMERIC_BASE].astype(float).reset_index(drop=True),
                     skills.reset_index(drop=True).astype(float),
                     df[CATEGORICAL].astype(str).reset_index(drop=True)], axis=1)
    out = out[numeric_features() + CATEGORICAL]
    assert not (LEAKY_COLUMNS | SENSITIVE_COLUMNS) & set(out.columns)
    return out
