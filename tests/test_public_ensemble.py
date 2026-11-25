"""Public-dataset loader and the per-source ensemble."""
import numpy as np
import pandas as pd
import pytest

from placeiq.data import public
from placeiq.model.ensemble import SourceEnsemble


def test_loader_maps_both_datasets_without_inventing_columns():
    if not (public.PUBLIC_DIR / "collegePlace.csv").exists():
        pytest.skip("public datasets not downloaded")
    cp = public.load_college_placement()
    cr = public.load_campus_recruitment()
    assert set(cp["branch"].unique()) <= {"CSE", "IT", "ECE", "EEE", "ME", "CIVIL"}
    assert cp["projects"].isna().all() and cp["certifications"].isna().all()      # never imputed
    assert cr["branch"].isna().all() and cr["active_backlogs"].isna().all()
    assert len(cp) == len(pd.read_csv(public.PUBLIC_DIR / "collegePlace.csv").drop_duplicates())   # exact duplicates removed
    assert set(cp["placed"].unique()) == {0, 1} and set(cr["placed"].unique()) == {0, 1}


def _toy(n=400, seed=0):
    rng = np.random.default_rng(seed)
    a = pd.DataFrame({"source": "a", "cgpa": rng.uniform(5, 10, n), "internships": rng.integers(0, 3, n).astype(float),
                      "active_backlogs": rng.integers(0, 2, n).astype(float), "branch": rng.choice(["CSE", "ME"], n),
                      "projects": np.nan, "certifications": np.nan})
    a["placed"] = (a.cgpa + rng.normal(0, 1, n) > 7.5).astype(int)
    b = pd.DataFrame({"source": "b", "cgpa": rng.uniform(5, 10, n), "internships": rng.integers(0, 3, n).astype(float),
                      "active_backlogs": np.nan, "branch": "nan", "projects": rng.integers(0, 4, n).astype(float),
                      "certifications": rng.integers(0, 3, n).astype(float)})
    b["placed"] = (b.cgpa + b.projects * 0.5 + rng.normal(0, 1, n) > 8).astype(int)
    return pd.concat([a, b], ignore_index=True)


def test_ensemble_trains_per_source_and_explains_additively():
    df = _toy()
    m = SourceEnsemble().fit(df, df["placed"])
    assert [x["name"] for x in m.fitted_] == ["college_placement", "campus_recruitment"]
    full = pd.DataFrame([{"cgpa": 8.0, "internships": 1.0, "active_backlogs": 0.0, "branch": "CSE", "projects": 2.0, "certifications": 1.0}])
    p = m.predict_proba(full)[0, 1]
    rows, bases = m.explain(full)
    logit = np.log(p / (1 - p))
    assert abs(bases[0] + sum(rows[0].values()) - logit) < 1e-6
    assert rows[0]["cgpa"] > 0                       # high CGPA raises the estimate in both members
    # a training row seen by one member only is scored by that member alone
    only_a = df[df.source == "a"].head(3)
    la = m.fitted_[0]["pipe"].predict_proba(only_a[["cgpa", "internships", "active_backlogs", "branch"]])[:, 1]
    assert np.allclose(m.predict_proba(only_a)[:, 1], la, atol=1e-6)


def test_train_uses_ensemble_and_records_provenance(tmp_path, monkeypatch):
    import placeiq.model.train as t
    monkeypatch.setattr(t, "ARTIFACTS_DIR", tmp_path)
    monkeypatch.setattr(t, "MODEL_PATH", tmp_path / "m.joblib")
    monkeypatch.setattr(t, "METRICS_PATH", tmp_path / "metrics.json")
    df = _toy()
    df["source"] = df["source"].map({"a": "college_placement", "b": "campus_recruitment"})
    df["skills"] = ""
    res = t.train(df, make_plots=False)
    assert res["public_data"] and not res["synthetic_data"]
    assert {d["source"] for d in res["data_sources"]} == {"college_placement", "campus_recruitment"}
    assert res["models"]["logistic_regression"]["roc_auc_mean"] > 0.7
    from placeiq.explain.guidance import load_bundle, report
    rep = report(load_bundle(tmp_path / "m.joblib"), {"branch": "CSE", "cgpa": 6.5, "active_backlogs": 1, "internships": 0,
                                                       "projects": 0, "certifications": 0, "skills": []})
    assert 0 < rep["probability"] < 1 and rep["attributions"]
