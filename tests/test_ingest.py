import pandas as pd

from placeiq.data.synthetic import write_bundle
from placeiq.ingest import ingest, load_jds


def test_ingest_hashes_ids_extracts_skills_and_scores(tmp_path, monkeypatch):
    monkeypatch.setenv("PLACEIQ_SALT", "test-salt")
    resumes = tmp_path / "resumes"
    resumes.mkdir()
    (resumes / "a.txt").write_text("SKILLS\nPython, SQL, Docker, Git\nContact: a@b.com +91 9876543210", encoding="utf-8")
    (resumes / "b.txt").write_text("SKILLS\nVerilog, Arduino, C and Embedded Systems", encoding="utf-8")
    records = pd.DataFrame({
        "student_id": ["0101", "0202", "0303"], "batch_year": [2025] * 3, "branch": ["cse", "ECE", "IT"],
        "cgpa": [8.1, 7.0, 6.5], "active_backlogs": [0, 1, 0], "internships": [1, 0, 0], "projects": [3, 2, 1],
        "certifications": [1, 0, 0], "rounds_cleared": [4, 1, 0], "placed": [1, 0, 0],
        "resume_file": ["a.txt", "b.txt", "missing.txt"], "jd_id": ["sde", "embedded_engineer", "sde"],
        "skills": ["", "", "java;not-a-skill"],
    })
    out, stats = ingest(records, resumes, load_jds(), use_sbert=False)

    assert "student_id" not in out.columns and not out.student_hash.isin(records.student_id).any()
    assert out.student_hash.str.len().eq(16).all()
    assert set(out.loc[0, "skills"].split(";")) == {"python", "sql", "docker", "git"}
    assert {"verilog", "arduino", "c", "embedded systems"} <= set(out.loc[1, "skills"].split(";"))
    assert out.loc[2, "skills"] == "java"                      # given skills win; unknown ones dropped
    assert out.loc[0, "branch"] == "CSE"
    assert stats["similarity_scored"] == 2 and stats["missing_resume_files"] == 1
    assert stats["unknown_skills_dropped"] == 1
    assert out.loc[0, "sim_skill_overlap"] > 0 and pd.isna(out.loc[2, "sim_tfidf"])


def test_synthetic_bundle_is_labelled(tmp_path):
    df = write_bundle(40, tmp_path, n_annotated=10)
    assert (df.is_synthetic == 1).all()
    assert len(list((tmp_path / "resumes").glob("*.txt"))) == 40
    raw = pd.read_csv(tmp_path / "records.csv")
    assert {"student_id", "resume_file", "jd_id", "placed", "is_synthetic"} <= set(raw.columns)
    assert len(pd.read_csv(tmp_path / "annotations.csv")) == 10


def test_ingest_maps_careerops_score_to_llm_baseline(tmp_path, monkeypatch):
    monkeypatch.setenv("PLACEIQ_SALT", "test-salt")
    records = pd.DataFrame({"student_id": ["a", "b", "c"], "branch": ["CSE"] * 3, "cgpa": [7, 8, 6], "active_backlogs": [0] * 3,
                            "internships": [1] * 3, "projects": [2] * 3, "certifications": [0] * 3, "placed": [1, 0, 1],
                            "skills": ["python"] * 3, "careerops_score": [4.0, "", 9]})
    out, stats = ingest(records, None, {}, use_sbert=False)
    assert out.loc[0, "sim_llm_fit"] == 0.8 and pd.isna(out.loc[1, "sim_llm_fit"]) and pd.isna(out.loc[2, "sim_llm_fit"])
    assert stats["llm_fit_scores"] == 1
    assert "careerops_score" not in out.columns
