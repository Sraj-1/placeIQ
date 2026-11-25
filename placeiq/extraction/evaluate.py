"""Skill-extraction evaluation against hand-annotated resumes (synopsis §4.3, Table 1).

    python -m placeiq.extraction.evaluate --gold annotations.csv --texts <folder of <resume_id>.txt>
    python -m placeiq.extraction.evaluate --from-db          # annotations saved in the web tool

Reports micro and macro precision / recall / F1, precision per matching method
(exact / strict / fuzzy), an ablation without fuzzy matching, and the most frequent
false positives and negatives for error analysis. Results are saved to
placeiq-data/artifacts/extraction_metrics.json, which the Evaluation page shows.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from placeiq.config import ARTIFACTS_DIR
from placeiq.extraction.skills import extract_skill_matches, load_taxonomy

EXTRACTION_METRICS_PATH = ARTIFACTS_DIR / "extraction_metrics.json"
TARGET_F1 = 0.80


def prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4)}


def score(predicted: dict[str, set[str]], gold: dict[str, set[str]]) -> dict:
    tp = fp = fn = 0
    per_doc = []
    fp_skills, fn_skills = Counter(), Counter()
    for rid, g in gold.items():
        p = predicted.get(rid, set())
        dtp, dfp, dfn = len(p & g), len(p - g), len(g - p)
        tp, fp, fn = tp + dtp, fp + dfp, fn + dfn
        per_doc.append(prf(dtp, dfp, dfn))
        fp_skills.update(p - g)
        fn_skills.update(g - p)
    macro = {k: round(sum(d[k] for d in per_doc) / len(per_doc), 4) for k in ("precision", "recall", "f1")} if per_doc else {}
    return {
        "n_documents": len(gold),
        "micro": prf(tp, fp, fn),
        "macro_over_documents": macro,
        "top_false_positives": fp_skills.most_common(15),
        "top_false_negatives": fn_skills.most_common(15),
    }


def evaluate_texts(texts: dict[str, str], gold: dict[str, set[str]]) -> dict:
    """Full study: main scores, per-method precision and the no-fuzzy ablation."""
    matches = {rid: extract_skill_matches(texts.get(rid, "")) for rid in gold}
    predicted = {rid: {m.skill for m in ms} for rid, ms in matches.items()}
    result = score(predicted, gold)
    by_method: dict[str, list[int]] = {}
    for rid, ms in matches.items():
        for m in ms:
            hit = by_method.setdefault(m.method, [0, 0])
            hit[0] += m.skill in gold[rid]
            hit[1] += 1
    result["precision_by_method"] = {k: {"correct": c, "predicted": n, "precision": round(c / n, 4)}
                                     for k, (c, n) in sorted(by_method.items())}
    no_fuzzy = {rid: {m.skill for m in ms if m.method != "fuzzy"} for rid, ms in matches.items()}
    result["ablation_without_fuzzy"] = score(no_fuzzy, gold)["micro"]
    result["target_f1"] = TARGET_F1
    result["meets_target"] = result["micro"]["f1"] > TARGET_F1
    result["evaluated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return result


def parse_gold(series_ids, series_skills) -> dict[str, set[str]]:
    taxonomy = load_taxonomy()
    gold = {}
    for rid, raw in zip(series_ids, series_skills):
        skills = {s.strip().lower() for s in str(raw).split(";") if s.strip() and str(raw) != "nan"}
        unknown = skills - set(taxonomy)
        if unknown:
            raise ValueError(f"{rid}: gold labels not in taxonomy: {sorted(unknown)}")
        gold[str(rid)] = skills
    return gold


def load_gold(path: str | Path) -> dict[str, set[str]]:
    df = pd.read_csv(path)
    return parse_gold(df.resume_id, df.gold_skills)


def save(result: dict, source: str, synthetic: bool) -> dict:
    result = {**result, "source": source, "synthetic_data": synthetic}
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    EXTRACTION_METRICS_PATH.write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold")
    ap.add_argument("--texts", help="folder of <resume_id>.txt files")
    ap.add_argument("--from-db", action="store_true")
    args = ap.parse_args()
    if args.from_db:
        from placeiq.db import Annotation, session_factory
        with session_factory()() as s:
            rows = s.query(Annotation).all()
        texts = {a.resume_id: a.text for a in rows}
        gold = {a.resume_id: a.gold() for a in rows}
        synthetic = any(a.annotator == "synthetic" for a in rows)
        source = "database annotations"
    else:
        if not (args.gold and args.texts):
            ap.error("--gold and --texts are required unless --from-db is given")
        gold = load_gold(args.gold)
        df = pd.read_csv(args.gold)
        synthetic = "annotator" in df and (df.annotator == "synthetic").any()
        texts = {rid: (Path(args.texts) / f"{rid}.txt").read_text(encoding="utf-8") for rid in gold}
        source = str(args.gold)
    if not gold:
        raise SystemExit("No annotations found.")
    res = save(evaluate_texts(texts, gold), source, bool(synthetic))
    print(json.dumps({k: res[k] for k in ("n_documents", "micro", "precision_by_method", "ablation_without_fuzzy", "meets_target")}, indent=2))
