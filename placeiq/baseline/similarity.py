"""Resume–JD similarity baseline (synopsis §4.6). Not a deliverable; it is the thing PlaceIQ
is compared against. Ported from the earlier AI-Resume-Matcher with these fixes:

  - Sentence-BERT is actually computed (the old hybrid hard-coded bert_score = 0.0);
  - TF-IDF is fit on the real JD corpus instead of an 11-line toy corpus;
  - preprocessing keeps "c++", "c#", "node.js" etc. (the old cleaner stripped all non-letters);
  - the skill-overlap term uses the evaluated PlaceIQ extractor.

Data-retention note: resumes must be discarded after feature extraction (§4.2), so compute
these scores at ingestion time with `score_resume` and store only the numbers.
TF-IDF is fit on the JD corpus alone so a single resume can be scored without the cohort.
"""
from __future__ import annotations

import re
from functools import lru_cache

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from placeiq.data.anonymize import strip_contact_info
from placeiq.extraction.skills import extract_skills

SBERT_MODEL = "all-MiniLM-L6-v2"
HYBRID_ALPHA = 0.5  # weight on TF-IDF in the lexical/semantic fusion used in the literature


def clean(text: str) -> str:
    text = strip_contact_info(text).lower()
    text = re.sub(r"[^a-z0-9+#.\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class SimilarityBaseline:
    def __init__(self, jd_texts: dict[str, str], use_sbert: bool = True):
        self.jd_ids = list(jd_texts)
        self.jd_clean = [clean(jd_texts[j]) for j in self.jd_ids]
        self.tfidf = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, token_pattern=r"(?u)\b[\w+#.]+\b")
        self.jd_tfidf = self.tfidf.fit_transform(self.jd_clean)
        self.jd_skills = [extract_skills(t) for t in self.jd_clean]
        self.use_sbert = use_sbert
        self.jd_emb = _sbert().encode(self.jd_clean, normalize_embeddings=True, show_progress_bar=False) if use_sbert else None

    def score_resume(self, resume_text: str, jd_id: str) -> dict[str, float]:
        j = self.jd_ids.index(jd_id)
        r = clean(resume_text)
        tfidf = float(cosine_similarity(self.tfidf.transform([r]), self.jd_tfidf[j])[0, 0])
        rs, js = extract_skills(r), self.jd_skills[j]
        skill = len(rs & js) / len(js) if js else 0.0
        out = {"sim_tfidf": round(tfidf, 4), "sim_skill_overlap": round(skill, 4)}
        if self.use_sbert:
            emb = _sbert().encode([r], normalize_embeddings=True, show_progress_bar=False)
            sbert = float(np.dot(emb[0], self.jd_emb[j]))
            out["sim_sbert"] = round(sbert, 4)
            out["sim_hybrid"] = round(HYBRID_ALPHA * tfidf + (1 - HYBRID_ALPHA) * sbert, 4)
        return out


@lru_cache(maxsize=1)
def _sbert():
    from sentence_transformers import SentenceTransformer  # heavy import, load lazily
    return SentenceTransformer(SBERT_MODEL)
