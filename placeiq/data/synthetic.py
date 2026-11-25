"""Synthetic cohort generator, FOR DEVELOPMENT AND DEMOS ONLY.

Lets every stage (ingest, extraction study, training, SHAP, baseline comparison, API,
dashboard) run end to end before real placement records arrive. The outcome is drawn from
a known logistic rule, so results prove the code works, not that anything predicts
placement. Never put numbers from this data in the report. Every output carries
`is_synthetic = 1`, and the UI shows a banner whenever the model was trained on it.

    python -m placeiq.data.synthetic --n 300 --out-dir placeiq-data/synthetic

writes:
    records.csv       raw-style records (student_id, resume_file, jd_id, outcome...), the
                      same layout the placement cell would provide; feed it to placeiq.ingest
    resumes/*.txt     one synthetic resume per student (aliases, typos, distractor words)
    annotations.csv   gold skills for the first 50 resumes (for the extraction study)
    cohort.csv        processed-style table, ready for training/dashboard without ingest
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from placeiq.config import JD_DIR, RANDOM_STATE, TAXONOMY_PATH

BRANCHES = ["CSE", "IT", "ECE", "EEE", "ME"]
BRANCH_NAMES = {
    "CSE": "Computer Science and Engineering", "IT": "Information Technology",
    "ECE": "Electronics and Communication Engineering", "EEE": "Electrical and Electronics Engineering",
    "ME": "Mechanical Engineering",
}
# Role preference by branch, and the skill categories each role draws on.
ROLE_BY_BRANCH = {
    "CSE": ["sde", "sde", "ml_engineer", "frontend_dev", "data_analyst", "devops"],
    "IT": ["sde", "frontend_dev", "data_analyst", "devops", "ml_engineer"],
    "ECE": ["embedded_engineer", "embedded_engineer", "sde", "data_analyst"],
    "EEE": ["embedded_engineer", "data_analyst", "sde"],
    "ME": ["data_analyst", "embedded_engineer", "sde"],
}
ROLE_CATEGORIES = {
    "sde": ["programming", "web_backend", "databases", "cs_fundamentals", "tools"],
    "data_analyst": ["data_science", "databases", "programming"],
    "ml_engineer": ["ml_ai", "data_science", "programming"],
    "frontend_dev": ["web_frontend", "programming", "tools", "design_product"],
    "embedded_engineer": ["hardware_embedded", "programming"],
    "devops": ["cloud_devops", "tools", "programming"],
}
DISTRACTORS = [
    "I excel at teamwork and like to express ideas clearly.",
    "Volunteered at the college tech fest; the rest of the team handled logistics.",
    "Go-getter attitude with strong communication skills.",
    "Captain of the college cricket team in Spring 2024.",
]


def _typo(word: str, rng) -> str:
    if len(word) < 7 or " " in word:
        return word
    i = int(rng.integers(1, len(word) - 2))
    return word[:i] + word[i + 1] + word[i] + word[i + 2:]


def _render_skill(skill: str, entry: dict, rng) -> str:
    options = entry.get("aliases", []) + entry.get("strict", [])
    alias = str(rng.choice(options))
    if rng.random() < 0.08:
        alias = _typo(alias, rng)
    elif rng.random() < 0.5 and not entry.get("strict"):
        alias = alias.title() if len(alias) > 3 else alias.upper()
    return alias


def _resume_text(row: dict, skills: list[str], taxonomy: dict, rng) -> str:
    rendered = [_render_skill(s, taxonomy[s], rng) for s in skills]
    lines = [
        f"CANDIDATE {row['student_id'][-4:]}",
        "EDUCATION",
        f"B.Tech, {BRANCH_NAMES[row['branch']]}, CGPA: {row['cgpa']:.2f}/10",
        "SKILLS",
        ", ".join(rendered),
        "PROJECTS",
    ]
    for p in range(row["projects"]):
        used = ", ".join(rng.choice(rendered, size=min(3, len(rendered)), replace=False))
        lines += [f"PROJECT {chr(65 + p)} | {2023 + p % 2}", f"• Built using {used}", "• Deployed and documented the system"]
    if row["internships"]:
        lines.append("INTERNSHIPS")
        for k in range(row["internships"]):
            lines += [f"SOFTWARE INTERN – ORGANISATION {k + 1} | Jun 2024 – Aug 2024", "• Worked with the engineering team"]
    if row["certifications"]:
        lines.append("CERTIFICATIONS")
        lines += [f"• Online certification course {k + 1}" for k in range(row["certifications"])]
    lines += ["ACHIEVEMENTS", str(rng.choice(DISTRACTORS))]
    return "\n".join(lines)


def generate(n: int = 300, seed: int = RANDOM_STATE, with_text: bool = False) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    by_cat: dict[str, list[str]] = {}
    for s, e in taxonomy.items():
        by_cat.setdefault(e["category"], []).append(s)
    all_skills = list(taxonomy)
    jd_ids = {p.stem for p in JD_DIR.glob("*.txt")}

    branch = rng.choice(BRANCHES, size=n, p=[0.35, 0.25, 0.2, 0.1, 0.1])
    cgpa = np.clip(rng.normal(7.4, 0.9, n), 5.0, 10.0).round(2)
    backlogs = rng.poisson(np.where(cgpa < 6.8, 1.2, 0.2))
    internships = rng.poisson(0.8, n)
    projects = np.clip(rng.poisson(2.5, n), 0, 8)
    certs = np.clip(rng.poisson(1.2, n), 0, 8)

    rows, relevant = [], []
    for i in range(n):
        role = str(rng.choice(ROLE_BY_BRANCH[branch[i]]))
        k = int(np.clip(rng.poisson(8) + (branch[i] == "CSE") * 3, 2, 24))
        n_rel = int(rng.binomial(k, 0.6))
        pool = sorted({s for c in ROLE_CATEGORIES[role] for s in by_cat.get(c, [])})
        rel = list(rng.choice(pool, size=min(n_rel, len(pool)), replace=False))
        rest = [s for s in all_skills if s not in rel]
        skills = sorted(set(rel) | set(rng.choice(rest, size=k - len(rel), replace=False)))
        relevant.append(len(rel))
        rows.append({"student_id": f"SYN{2024 + i % 2}{i:04d}", "role": role, "skills": skills})

    logit = (-9.0 + 1.1 * cgpa - 1.0 * backlogs + 0.7 * internships + 0.25 * projects + 0.1 * certs
             + 0.06 * np.array(relevant) + 0.4 * np.isin(branch, ["CSE", "IT"]))
    placed = rng.binomial(1, 1 / (1 + np.exp(-logit)))
    rounds = np.where(placed == 1, rng.integers(3, 6, n), rng.integers(0, 4, n))

    df = pd.DataFrame({
        "student_id": [r["student_id"] for r in rows],
        "student_hash": [f"syn{i:04d}" for i in range(n)],
        "batch_year": [2024 + i % 2 for i in range(n)],
        "branch": branch, "cgpa": cgpa, "active_backlogs": backlogs, "internships": internships,
        "projects": projects, "certifications": certs,
        "skills": [";".join(r["skills"]) for r in rows],
        "jd_id": [r["role"] if r["role"] in jd_ids else "" for r in rows],
        "rounds_cleared": rounds, "placed": placed, "is_synthetic": 1,
        # Audit-only attribute with NO effect on the synthetic outcome.
        "gender": rng.choice(["M", "F"], size=n, p=[0.65, 0.35]),
        # Stand-in for career-ops' LLM job-fit score (1–5): driven by skill match with the role
        # plus noise, NOT by the outcome, as an LLM reading CV vs JD would be.
        "careerops_score": np.clip(np.round(2.2 + 0.18 * np.array(relevant) + rng.normal(0, 0.6, n), 1), 1, 5),
    })
    if with_text:
        df["resume_text"] = [_resume_text(df.iloc[i].to_dict(), rows[i]["skills"], taxonomy, rng) for i in range(n)]
    return df


def write_bundle(n: int, out_dir: Path, seed: int = RANDOM_STATE, n_annotated: int = 50) -> pd.DataFrame:
    out_dir = Path(out_dir)
    (out_dir / "resumes").mkdir(parents=True, exist_ok=True)
    df = generate(n, seed, with_text=True)
    for row in df.itertuples():
        (out_dir / "resumes" / f"{row.student_id}.txt").write_text(row.resume_text, encoding="utf-8")
    raw = df.assign(resume_file=df.student_id + ".txt")
    raw[["student_id", "batch_year", "branch", "cgpa", "active_backlogs", "internships", "projects",
         "certifications", "rounds_cleared", "placed", "resume_file", "jd_id", "is_synthetic", "gender", "careerops_score"]] \
        .to_csv(out_dir / "records.csv", index=False)
    pd.DataFrame({"resume_id": df.student_id[:n_annotated], "gold_skills": df.skills[:n_annotated],
                  "annotator": "synthetic", "notes": ""}).to_csv(out_dir / "annotations.csv", index=False)
    df.drop(columns=["resume_text", "student_id"]).to_csv(out_dir / "cohort.csv", index=False)
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--out-dir", default="placeiq-data/synthetic")
    args = ap.parse_args()
    df = write_bundle(args.n, Path(args.out_dir))
    print(f"Wrote SYNTHETIC bundle ({len(df)} students, placed rate {df.placed.mean():.2f}) to {args.out_dir}")
