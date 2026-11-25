"""Tests for the what-if simulator, roadmap, training groups and fairness audit."""
import numpy as np
import pandas as pd
import pytest

from placeiq.cohort import NO_GAP, summarize
from placeiq.data.synthetic import generate
from placeiq.explain.whatif import score, suggestions
from placeiq.features.assemble import build_features, modifiable_features
from placeiq.model.fairness import audit
from placeiq.roadmap import company_gaps, role_profiles, roadmap

WEAK = {"branch": "CSE", "cgpa": 6.4, "active_backlogs": 2, "internships": 0, "projects": 1,
        "certifications": 0, "skills": ["python"]}


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    import placeiq.model.train as t
    out = tmp_path_factory.mktemp("art")
    mp = pytest.MonkeyPatch()
    mp.setattr(t, "ARTIFACTS_DIR", out)
    mp.setattr(t, "MODEL_PATH", out / "m.joblib")
    mp.setattr(t, "METRICS_PATH", out / "metrics.json")
    res = t.train(generate(300), make_plots=False)
    from placeiq.explain.guidance import load_bundle
    yield load_bundle(out / "m.joblib"), res
    mp.undo()


def test_whatif_scores_match_model_and_rank_gains(bundle):
    b, _ = bundle
    base = score(b, [WEAK])[0]
    res = suggestions(b, WEAK)
    assert res["probability"] == base
    deltas = [s["delta"] for s in res["suggestions"]]
    assert deltas == sorted(deltas, reverse=True) and all(d > 0 for d in deltas)
    for s in res["suggestions"]:      # every number is reproducible from the model
        assert score(b, [{**WEAK, **s["changes"]}])[0] == s["probability"]
        assert abs(s["probability"] - base - s["delta"]) < 1e-3
    keys = {s["key"] for s in res["suggestions"]}
    assert "active_backlogs" in keys            # clearing backlogs must help a student with 2
    assert sum(k.startswith("skill_") for k in keys) <= 1


def test_whatif_skips_impossible_steps(bundle):
    b, _ = bundle
    strong = {**WEAK, "cgpa": 9.9, "active_backlogs": 0}
    keys = {s["key"] for s in suggestions(b, strong, top_k=50)["suggestions"]}
    assert not {"active_backlogs", "cgpa_0.25", "cgpa_0.5"} & keys


def test_roadmap_roles_and_companies(bundle):
    b, _ = bundle
    roles = role_profiles()
    assert "sde" in roles and {"data structures", "algorithms", "sql"} <= set(roles["sde"]["skills"])
    r = roadmap(b, {**WEAK, "skills": ["python", "sql", "java"]})
    sde = next(x for x in r["roles"] if x["id"] == "sde")
    assert {"python", "sql", "java"} <= set(sde["have"]) and "data structures" in sde["missing"]
    assert sde["coverage"] == round(len(sde["have"]) / (len(sde["have"]) + len(sde["missing"])), 4)
    assert sde["delta_if_learned"] == round(sde["probability_if_learned"] - score(b, [{**WEAK, "skills": ["python", "sql", "java"]}])[0], 4)
    n_companies = sum(len(v) for v in r["companies"].values())
    assert n_companies == 15
    for entry in r["companies"]["near"]:
        assert entry["gaps"] and all(g["fixable"] for g in entry["gaps"])
    for entry in r["companies"]["out_of_reach"]:
        assert any(not g["fixable"] for g in entry["gaps"])


def test_company_gap_classification():
    c = {"name": "X", "min_cgpa": 7.0, "max_active_backlogs": 0, "branches": ["CSE"], "required_skills_any": ["sql"]}
    p = {"branch": "CSE", "cgpa": 6.7, "active_backlogs": 1, "skills": ["python"]}
    gaps = {g["type"]: g for g in company_gaps(p, c)}
    assert gaps["cgpa"]["fixable"] and gaps["backlogs"]["fixable"] and gaps["skills"]["options"] == ["sql"]
    assert not company_gaps({**p, "cgpa": 6.0, "branch": "ME"}, c)[0]["fixable"]   # branch gap first, unfixable
    assert company_gaps({"branch": "CSE", "cgpa": 7.2, "active_backlogs": 0, "skills": ["sql"]}, c) == []


def test_roadmap_works_without_model():
    r = roadmap(None, WEAK)
    assert r["roles"] and "probability_if_learned" not in r["roles"][0]


def test_training_groups_partition_the_batch(bundle):
    b, _ = bundle
    batch = generate(80, seed=11)
    s = summarize(b, batch)
    groups = s["training_groups"]
    assert sum(g["students"] for g in groups) == 80
    assert all(g["feature"] in modifiable_features() | {NO_GAP} for g in groups)
    assert all(g["at_risk"] + g["borderline"] + g["ready"] == g["students"] for g in groups)
    actionable = [g for g in groups if g["feature"] != NO_GAP]
    assert [g["students"] for g in actionable] == sorted((g["students"] for g in actionable), reverse=True)
    assert all(g["mean_contribution"] < 0 for g in actionable)


def test_fairness_audit_metrics(bundle):
    _, res = bundle
    f = res["fairness"]["attributes"]
    assert {"branch", "gender", "batch_year"} <= set(f)
    assert "gender" not in build_features(generate(10)).columns
    g = f["gender"]
    assert sum(x["n"] for x in g["groups"]) == 300
    assert g["comparable_groups"] == 2 and g["auc_gap"] is not None


def test_fairness_hand_computed():
    df = pd.DataFrame({"placed": [1, 1, 0, 0] * 5 + [1, 0, 0, 0] * 5,
                       "p": [0.9, 0.6, 0.4, 0.2] * 5 + [0.4, 0.6, 0.3, 0.1] * 5,
                       "grp": ["A"] * 20 + ["B"] * 20})
    a = audit(df, "p", ["grp"])["attributes"]["grp"]
    A, B = a["groups"]
    assert A["tpr"] == 1.0 and A["fpr"] == 0.0 and A["auc"] == 1.0
    assert B["tpr"] == 0.0 and B["fpr"] == round(1 / 3, 4)
    assert a["tpr_gap"] == 1.0 and "tpr_gap" in a["flags"]
    small = audit(df.iloc[:30], "p", ["grp"])["attributes"]["grp"]   # group B has 10 < 15 students
    assert small["comparable_groups"] == 1 and small["auc_gap"] is None


def test_api_endpoints(bundle, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from placeiq.api import main
    import joblib
    b, _ = bundle
    path = tmp_path / "m.joblib"
    joblib.dump(b, path)
    monkeypatch.setattr(main, "MODEL_PATH", path)
    monkeypatch.setattr(main, "_bundle", b)
    c = TestClient(main.app)
    r = c.post("/api/score", json={"profiles": [WEAK, {**WEAK, "internships": 3}]})
    assert r.status_code == 200 and len(r.json()["probabilities"]) == 2
    assert c.post("/api/score", json={"profiles": []}).status_code == 422
    w = c.post("/api/whatif", json=WEAK).json()
    assert w["suggestions"] and np.isclose(w["probability"], r.json()["probabilities"][0])
    rm = c.post("/api/roadmap", json=WEAK).json()
    assert rm["roles"] and set(rm["companies"]) == {"eligible", "near", "out_of_reach"}


def test_guidance_only_advises_steps_that_raise_the_estimate(bundle):
    from placeiq.explain.guidance import report
    b, _ = bundle
    rec = {"branch": "CSE", "cgpa": 7.4, "active_backlogs": 1, "internships": 1, "projects": 2, "certifications": 1,
           "skills": ["algorithms", "android", "css", "data structures", "flask", "git", "html", "java", "javascript",
                      "kotlin", "linux", "mysql", "node.js", "object oriented programming", "python", "react",
                      "rest api", "sql", "sqlite"]}
    rep = report(b, rec)
    base = score(b, [rec])[0]
    from placeiq.explain.whatif import candidate_changes
    by_key = {c["key"]: c["profile"] for c in candidate_changes(rec)}
    for g in rep["guidance"]:
        f = g["feature"]
        key = {"cgpa": "cgpa_0.25"}.get(f, f)
        if f.startswith("skills_"):
            key = "skill_" + f.removeprefix("skills_")
        if key in by_key:
            assert score(b, [by_key[key]])[0] > base, f"advice for {f} would not raise the estimate"
