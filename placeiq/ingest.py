"""Build the anonymised training table from raw placement-cell records (synopsis §4.2, §4.6).

    python -m placeiq.ingest --records raw/records.csv --resumes raw/resumes --out placeiq-data/processed/historical.csv

Input columns (records CSV):
    student_id                      roll/enrolment number; hashed here and never written out
    batch_year, branch, cgpa, active_backlogs, internships, projects, certifications,
    rounds_cleared, placed          as in data/templates/historical_records_template.csv
    skills          (optional)      ';'-separated canonical skills; if blank, extracted from the resume
    resume_file     (optional)      file name inside --resumes (.pdf or .txt)
    jd_id           (optional)      job description in placeiq-data/jds/<jd_id>.txt the student applied to
    is_synthetic    (optional)      carried through so synthetic runs are always labelled
    gender          (optional)      e.g. M / F / O; used only for the fairness audit, never as a feature
    careerops_score (optional)      mean career-ops LLM job-fit score (1–5) from placeiq-outcome.mjs; becomes the
                                    `sim_llm_fit` BASELINE signal (scaled to 0–1), never a model feature

For each student with a resume and a jd_id, the similarity baseline (TF-IDF, Sentence-BERT,
hybrid, skill overlap) is computed here, at ingestion, and only the scores are kept. That is
what allows the raw resumes to be deleted afterwards, as §4.2 requires.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from placeiq.config import JD_DIR, ensure_env
from placeiq.data.anonymize import hash_identifier, strip_contact_info
from placeiq.extraction.pdf_text import extract_text
from placeiq.extraction.skills import extract_skills, load_taxonomy

log = logging.getLogger("placeiq.ingest")

OUT_COLUMNS = ["student_hash", "batch_year", "branch", "cgpa", "active_backlogs", "internships", "projects",
               "certifications", "skills", "rounds_cleared", "placed", "jd_id", "is_synthetic"]
# Optional audit-only columns carried through unchanged (fairness audit; never model features).
OPTIONAL_PASSTHROUGH = ["gender"]
REQUIRED = ["student_id", "branch", "cgpa", "active_backlogs", "internships", "projects", "certifications", "placed"]


def load_jds(jd_dir: Path = JD_DIR) -> dict[str, str]:
    return {p.stem: p.read_text(encoding="utf-8") for p in sorted(Path(jd_dir).glob("*.txt"))}


def read_resume(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return extract_text(str(path))
    return path.read_text(encoding="utf-8", errors="ignore")


def ingest(records: pd.DataFrame, resumes_dir: Path | None, jds: dict[str, str], use_sbert: bool = True) -> tuple[pd.DataFrame, dict]:
    missing = [c for c in REQUIRED if c not in records.columns]
    if missing:
        raise ValueError(f"records CSV is missing columns: {missing}")
    taxonomy = load_taxonomy()
    baseline = None
    if jds and resumes_dir is not None and "jd_id" in records.columns:
        from placeiq.baseline.similarity import SimilarityBaseline
        try:
            baseline = SimilarityBaseline(jds, use_sbert=use_sbert)
        except Exception as exc:  # e.g. SBERT model not downloadable offline
            log.warning("Sentence-BERT unavailable (%s); continuing with TF-IDF and skill overlap only", exc)
            baseline = SimilarityBaseline(jds, use_sbert=False)

    stats = {"rows": len(records), "resumes_read": 0, "skills_extracted": 0, "similarity_scored": 0,
             "unknown_skills_dropped": 0, "missing_resume_files": 0, "llm_fit_scores": 0}
    out = []
    for r in records.to_dict("records"):
        text = ""
        fname = str(r.get("resume_file") or "").strip()
        if resumes_dir is not None and fname and fname.lower() != "nan":
            path = Path(resumes_dir) / fname
            if path.exists():
                text = strip_contact_info(read_resume(path))
                stats["resumes_read"] += 1
            else:
                stats["missing_resume_files"] += 1

        given = str(r.get("skills") or "")
        given = [] if given.lower() == "nan" else [s.strip().lower() for s in given.split(";") if s.strip()]
        if given:
            stats["unknown_skills_dropped"] += sum(s not in taxonomy for s in given)
            skills = sorted({s for s in given if s in taxonomy})
        elif text:
            skills = sorted(extract_skills(text))
            stats["skills_extracted"] += 1
        else:
            skills = []

        row = {
            "student_hash": hash_identifier(str(r["student_id"])),
            "batch_year": r.get("batch_year"), "branch": str(r["branch"]).strip().upper(),
            "cgpa": r["cgpa"], "active_backlogs": r["active_backlogs"], "internships": r["internships"],
            "projects": r["projects"], "certifications": r["certifications"], "skills": ";".join(skills),
            "rounds_cleared": r.get("rounds_cleared"), "placed": int(r["placed"]),
            "jd_id": str(r.get("jd_id") or "").replace("nan", ""), "is_synthetic": int(r.get("is_synthetic") or 0),
        }
        llm = pd.to_numeric(pd.Series([r.get("careerops_score")]), errors="coerce").iloc[0]
        if pd.notna(llm) and 0 < llm <= 5:
            row["sim_llm_fit"] = round(float(llm) / 5, 4)
            stats["llm_fit_scores"] += 1
        if baseline is not None and text and row["jd_id"] in jds:
            row.update(baseline.score_resume(text, row["jd_id"]))
            stats["similarity_scored"] += 1
        out.append(row)

    df = pd.DataFrame(out)
    extra = [c for c in OPTIONAL_PASSTHROUGH if c in records.columns]
    for c in extra:
        df[c] = records[c].astype(str).str.strip().str.upper().replace({"NAN": ""}).values
    sim_cols = sorted(c for c in df.columns if c.startswith("sim_"))
    return df[OUT_COLUMNS + extra + sim_cols], stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", required=True)
    ap.add_argument("--resumes", default=None, help="folder containing the resume files")
    ap.add_argument("--jds", default=str(JD_DIR))
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-sbert", action="store_true", help="skip Sentence-BERT (faster, fully offline)")
    args = ap.parse_args()
    ensure_env()
    df, stats = ingest(pd.read_csv(args.records), Path(args.resumes) if args.resumes else None,
                       load_jds(Path(args.jds)), use_sbert=not args.no_sbert)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} anonymised rows to {args.out}")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    if stats["resumes_read"]:
        print("Reminder (§4.2): features and similarity scores are extracted. Delete the raw resume files now.")
