"""What-if simulation: how the estimate changes if a student changes something they control.

Every number is the trained model's probability for an edited profile, so it's computed,
never generated. These are associations learned from past batches, not causal effects, and
the UI says so.
"""
from __future__ import annotations

import copy

import pandas as pd

from placeiq.extraction.skills import load_taxonomy
from placeiq.features.assemble import build_features, category_names, parse_skills

MIN_GAIN = 0.005  # ignore suggestions that move the estimate by less than half a point


def score(bundle: dict, profiles: list[dict]) -> list[float]:
    """Placement probability for each profile (no SHAP; fast enough for live sliders)."""
    if not profiles:
        return []
    X = build_features(pd.DataFrame(profiles))
    return [round(float(p), 4) for p in bundle["model"].predict_proba(X)[:, 1]]


def _example_skill(category: str, have: set[str]) -> str | None:
    for skill, entry in load_taxonomy().items():
        if entry["category"] == category and skill not in have:
            return skill
    return None


def candidate_changes(profile: dict) -> list[dict]:
    """Single, realistic steps a student could take before placement season."""
    p = profile
    out = []

    def add(key: str, label: str, edit: dict):
        new = copy.deepcopy(p)
        new.update(edit)
        out.append({"key": key, "label": label, "profile": new})

    add("internships", f"Do one more internship ({p['internships']} → {p['internships'] + 1})",
        {"internships": p["internships"] + 1})
    add("projects", f"Add one substantial project ({p['projects']} → {p['projects'] + 1})",
        {"projects": p["projects"] + 1})
    add("certifications", f"Earn one relevant certification ({p['certifications']} → {p['certifications'] + 1})",
        {"certifications": p["certifications"] + 1})
    if p["active_backlogs"] > 0:
        add("active_backlogs", f"Clear all active backlogs ({p['active_backlogs']} → 0)", {"active_backlogs": 0})
        if p["active_backlogs"] > 1:
            add("active_backlogs_one", f"Clear one backlog ({p['active_backlogs']} → {p['active_backlogs'] - 1})",
                {"active_backlogs": p["active_backlogs"] - 1})
    for step in (0.25, 0.5):
        if p["cgpa"] + step <= 10:
            add(f"cgpa_{step}", f"Raise CGPA by {step} ({p['cgpa']:g} → {p['cgpa'] + step:g})",
                {"cgpa": round(p["cgpa"] + step, 2)})
    have = set(parse_skills(p.get("skills", [])))
    for cat in category_names():
        example = _example_skill(cat, have)
        if example:
            label = cat.replace("_", " ")
            add(f"skill_{cat}", f"Learn one more {label} skill", {"skills": sorted(have | {example})})
    return out


def suggestions(bundle: dict, profile: dict, top_k: int = 6) -> dict:
    profile = {**profile, "skills": sorted(set(parse_skills(profile.get("skills", []))))}
    base = score(bundle, [profile])[0]
    changes = candidate_changes(profile)
    probs = score(bundle, [c["profile"] for c in changes])
    ranked = []
    for c, prob in zip(changes, probs):
        gain = round(prob - base, 4)
        if gain >= MIN_GAIN:
            ranked.append({"key": c["key"], "label": c["label"], "probability": prob, "delta": gain,
                           "changes": {k: v for k, v in c["profile"].items() if v != profile.get(k)}})
    ranked.sort(key=lambda r: -r["delta"])
    # Keep only the best skill category, so the list isn't dominated by near-identical skill steps.
    seen_skill, filtered = False, []
    for r in ranked:
        if r["key"].startswith("skill_"):
            if seen_skill:
                continue
            seen_skill = True
        filtered.append(r)
    return {"probability": base, "suggestions": filtered[:top_k]}
