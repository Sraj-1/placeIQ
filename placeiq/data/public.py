"""Public placement datasets, mapped into PlaceIQ's training schema.

Used as a stand-in until the institution's own records are collected. Neither dataset comes
from GTBIT, and both show signs of being generated themselves (see DATA_NOTES), so results are
"trained on public benchmark data", never real institutional outcomes.

Sources (downloaded into placeiq-data/public/):
  1. Campus Recruitment CSV, huggingface.co/datasets/Krooz/Campus_Recruitment_CSV (CC0-1.0).
     10,000 students: CGPA, Internships, Projects, Workshops/Certifications, PlacementStatus
     (+ aptitude, soft skills, SSC/HSC marks, not used: PlaceIQ has no such inputs).
  2. College Placement (collegePlace.csv), github.com/Asmi-va/College_placement_predictor,
     a copy of a public Kaggle dataset; no licence stated. 2,966 rows of Indian engineering
     students: Stream, CGPA, Internships, HistoryOfBacklogs, Gender, PlacedOrNot.

Each row keeps only the columns its dataset really has; the rest stay missing (NaN) and are
never imputed. The SourceEnsemble model trains one sub-model per dataset on its own columns.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from placeiq.config import PQ_DIR

PUBLIC_DIR = PQ_DIR / "public"
OUT = PUBLIC_DIR / "placeiq_public_training.csv"

STREAM_TO_BRANCH = {
    "computer science": "CSE",
    "information technology": "IT",
    "electronics and communication": "ECE",
    "electrical": "EEE",
    "mechanical": "ME",
    "civil": "CIVIL",
}

SOURCES = {
    "campus_recruitment": {
        "title": "Campus Recruitment CSV (Hugging Face, CC0-1.0)",
        "url": "https://huggingface.co/datasets/Krooz/Campus_Recruitment_CSV",
    },
    "college_placement": {
        "title": "College Placement dataset (collegePlace.csv, public Kaggle copy)",
        "url": "https://github.com/Asmi-va/College_placement_predictor",
    },
}

DATA_NOTES = [
    "Neither dataset is from your college; results show general patterns, not GTBIT outcomes.",
    "College Placement: 1,829 of 2,966 rows were exact duplicates and are removed; every student with CGPA 8+ is placed, which suggests generated data.",
    "College Placement records any backlog history (yes/no), used here as active backlogs 0 or 1.",
    "Campus Recruitment: projects and certifications relate to placement non-monotonically, a sign of generated data.",
    "Neither dataset has skills, so skill categories carry no learned weight until real data is used.",
]


def load_campus_recruitment(public_dir: Path = PUBLIC_DIR) -> pd.DataFrame:
    parts = [pd.read_csv(public_dir / f"campus_recruitment_{s}.csv") for s in ("train", "validation", "test")]
    cr = pd.concat(parts, ignore_index=True).drop_duplicates()
    return pd.DataFrame({
        "source": "campus_recruitment",
        "branch": np.nan,
        "cgpa": cr["CGPA"].astype(float),
        "active_backlogs": np.nan,
        "internships": cr["Internships"].astype(float),
        "projects": cr["Projects"].astype(float),
        "certifications": cr["Workshops/Certifications"].astype(float),
        "skills": "",
        "gender": np.nan,
        "placed": (cr["PlacementStatus"].str.strip().str.lower() == "placed").astype(int),
    })


def load_college_placement(public_dir: Path = PUBLIC_DIR) -> pd.DataFrame:
    cp = pd.read_csv(public_dir / "collegePlace.csv").drop_duplicates()
    branch = cp["Stream"].str.strip().str.lower().map(STREAM_TO_BRANCH)
    if branch.isna().any():
        raise ValueError(f"Unknown streams: {sorted(cp.loc[branch.isna(), 'Stream'].unique())}")
    return pd.DataFrame({
        "source": "college_placement",
        "branch": branch,
        "cgpa": cp["CGPA"].astype(float),
        "active_backlogs": cp["HistoryOfBacklogs"].astype(float),
        "internships": cp["Internships"].astype(float),
        "projects": np.nan,
        "certifications": np.nan,
        "skills": "",
        "gender": cp["Gender"].str.strip().str[0].str.upper(),
        "placed": cp["PlacedOrNot"].astype(int),
    })


def build(public_dir: Path = PUBLIC_DIR, out: Path = OUT) -> pd.DataFrame:
    missing = [f for f in ("campus_recruitment_train.csv", "campus_recruitment_validation.csv",
                           "campus_recruitment_test.csv", "collegePlace.csv") if not (public_dir / f).exists()]
    if missing:
        raise FileNotFoundError(f"Missing public dataset files in {public_dir}: {missing}")
    df = pd.concat([load_college_placement(public_dir), load_campus_recruitment(public_dir)], ignore_index=True)
    df.insert(0, "student_hash", [f"pub{i:05d}" for i in range(len(df))])
    df["is_synthetic"] = 0
    df.to_csv(out, index=False)
    return df


if __name__ == "__main__":
    d = build()
    print(f"Wrote {len(d)} rows to {OUT}")
    print(d.groupby("source")["placed"].agg(["count", "mean"]).round(3))
