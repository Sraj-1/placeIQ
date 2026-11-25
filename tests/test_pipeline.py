import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import placeiq.config as cfg
from placeiq.baseline.compare import compare
from placeiq.data.synthetic import generate
from placeiq.eligibility.filter import eligible_companies
from placeiq.explain import guidance
from placeiq.features.assemble import build_features, modifiable_features


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    out = tmp_path_factory.mktemp("artifacts")
    mp = pytest.MonkeyPatch()
    from placeiq.model import train as train_mod
    for mod in (cfg, train_mod, guidance):
        for name, val in {"ARTIFACTS_DIR": out, "MODEL_PATH": out / "model.joblib",
                          "METRICS_PATH": out / "metrics.json"}.items():
            if hasattr(mod, name):
                mp.setattr(mod, name, val)
    df = generate(300)
    res = train_mod.train(df)
    yield df, res, guidance.load_bundle(out / "model.joblib"), out
    mp.undo()


def test_no_leaky_features():
    X = build_features(generate(20))
    assert "rounds_cleared" not in X.columns and "placed" not in X.columns


def test_training_reports_auc_not_just_accuracy(trained):
    _, res, _, _ = trained
    lr = res["models"]["logistic_regression"]
    assert lr["roc_auc_mean"] > 0.7  # synthetic data has real signal by construction
    assert "majority_class_accuracy" in lr and len(lr["oof_roc_auc_95ci"]) == 2


def test_guidance_traceable_and_modifiable(trained):
    df, _, bundle, _ = trained
    weak = df.sort_values("cgpa").iloc[0].to_dict()
    rep = guidance.report(bundle, weak)
    contribs = {a["feature"]: a["contribution"] for a in rep["attributions"]}
    assert rep["guidance"], "a weak profile should get at least one recommendation"
    for g in rep["guidance"]:
        assert g["feature"] in modifiable_features()
        assert g["contribution"] == contribs[g["feature"]] < 0
        assert f"{g['contribution']:+.2f}" in g["message"]
    assert all(a["feature"] != "branch" for a in rep["guidance"])


def test_attributions_sum_to_logit(trained):
    df, _, bundle, _ = trained
    rec = df.iloc[0].to_dict()
    rep = guidance.report(bundle, rec)
    logit = np.log(rep["probability"] / (1 - rep["probability"]))
    assert abs(rep["base_value"] + sum(a["contribution"] for a in rep["attributions"]) - logit) < 0.05


def test_eligibility():
    c = [{"name": "X", "min_cgpa": 7.0, "max_active_backlogs": 0, "branches": ["CSE"], "required_skills_any": ["python"]}]
    ok = {"cgpa": 8, "active_backlogs": 0, "branch": "CSE", "skills": ["python"]}
    assert eligible_companies(ok, c)["eligible"] == ["X"]
    bad = {**ok, "cgpa": 6.5, "skills": ["java"]}
    assert len(eligible_companies(bad, c)["ineligible"][0]["reasons"]) == 2


def test_compare_runs():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 200)
    df = pd.DataFrame({"placed": y, "sim_tfidf": rng.random(200), "oof_logistic_regression": y * 0.6 + rng.random(200) * 0.4})
    res = compare(df)
    assert res["signals"]["oof_logistic_regression"]["roc_auc"] > res["signals"]["sim_tfidf"]["roc_auc"]


@pytest.fixture()
def client(trained, monkeypatch, tmp_path):
    _, _, bundle, out = trained
    from placeiq.api import main
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 't.db').as_posix()}")
    monkeypatch.setenv("PLACEIQ_SALT", "test-salt")
    monkeypatch.setattr(main, "MODEL_PATH", out / "model.joblib")
    monkeypatch.setattr(main, "_bundle", bundle)
    return TestClient(main.app)


PROFILE = {"branch": "cse", "cgpa": 6.4, "active_backlogs": 2, "internships": 0, "projects": 1,
           "certifications": 0, "skills": ["python", "sql"]}


def test_api_student_flow(client):
    assert client.get("/api/health").json()["model_loaded"]
    r = client.post("/api/predict", json=PROFILE)
    assert r.status_code == 200, r.text
    assert 0 <= r.json()["probability"] <= 1 and "companies" in r.json()
    assert client.post("/api/predict", json={**PROFILE, "skills": ["basket weaving"]}).status_code == 422
    assert client.post("/api/parse", files={"file": ("x.pdf", b"not a pdf", "application/pdf")}).status_code == 415

    key = {"roll_number": "01234567890", "batch_year": 2026}
    assert client.post("/api/students", json={**key, "consent": False, "profile": PROFILE}).status_code == 400
    assert client.post("/api/students", json={**key, "consent": True, "profile": PROFILE}).json()["updated"] is False
    assert client.post("/api/students", json={**key, "consent": True, "profile": {**PROFILE, "cgpa": 8.0}}).json()["updated"] is True
    assert client.get("/api/admin/batches").json() == [{"batch_year": 2026, "count": 1}]
    csv = client.get("/api/admin/students/export?batch_year=2026").text
    assert "01234567890" not in csv and "8.0" in csv
    assert client.post("/api/students/withdraw", json=key).json()["deleted"]
    assert client.post("/api/students/withdraw", json=key).status_code == 404


def test_api_placement_cell_needs_no_key(client):
    assert client.get("/api/admin/batches").status_code == 200
    assert client.get("/api/admin/metrics").status_code == 200


def test_api_admin_cohort_and_figures(client):
    s = client.post("/api/admin/cohort",
                    json={"profiles": [PROFILE, {**PROFILE, "cgpa": 9.1, "active_backlogs": 0}]})
    assert s.status_code == 200 and s.json()["n_students"] == 2
    for i in range(3):
        client.post("/api/students", json={"roll_number": f"R{i:05d}", "batch_year": 2027, "consent": True,
                                           "profile": {**PROFILE, "cgpa": 6 + i}})
    db_summary = client.get("/api/admin/cohort?batch_year=2027").json()
    assert db_summary["n_students"] == 3 and db_summary["synthetic_records"] == 0
    assert client.get("/api/admin/figures/..%2F..%2Fsecret.png").status_code in (400, 404)
    assert client.delete("/api/admin/students?batch_year=2027").json()["deleted"] == 3


def test_api_annotations(client, tmp_path, monkeypatch):
    from placeiq.extraction import evaluate as ev
    monkeypatch.setattr(ev, "EXTRACTION_METRICS_PATH", tmp_path / "em.json")
    monkeypatch.setattr(ev, "ARTIFACTS_DIR", tmp_path)
    text = "SKILLS\nPython, Java, Docker and MySQL. Email me at someone@example.com"
    r = client.put("/api/admin/annotations/r001",
                   json={"text": text, "gold_skills": ["python", "java", "docker", "mysql"], "annotator": "AB"})
    assert r.status_code == 200, r.text
    got = client.get("/api/admin/annotations/r001").json()
    assert "@" not in got["text"] and {p["skill"] for p in got["predicted"]} == {"python", "java", "docker", "mysql"}
    res = client.post("/api/admin/annotations/evaluate").json()
    assert res["micro"]["f1"] == 1.0 and res["synthetic_data"] is False
    assert client.put("/api/admin/annotations/bad id!", json={"text": text}).status_code in (400, 404)
