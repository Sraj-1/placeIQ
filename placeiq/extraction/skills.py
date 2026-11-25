"""Taxonomy-constrained skill extraction (synopsis §4.3).

Three matchers, in order of trust:
  1. exact  - case-insensitive alias with token boundaries, so "java" never fires inside
              "javascript" and "git" never fires inside "github";
  2. strict - case-sensitive aliases that are ordinary words or single letters ("C", "R",
              "Go", "Excel", "Express", "Notion"). These only count when they appear as an
              item in a list (after ":", ",", "/", "•", "|" or "and", and before ",", "/", ")"
              or end of line), so "PROJECT C" and "Go-getter" don't match;
  3. fuzzy  - RapidFuzz ratio over 1-3-word n-grams to absorb typos ("tensorflwo"). Only for
              aliases of 7+ characters, the first letter must agree, and an n-gram that is
              itself a known alias is never re-read as a typo of another skill.
Exact and strict matches are resolved longest-first, so an alias inside a longer matched
alias is not counted twice ("sql" inside "pl/sql", "js" inside "node.js").
Every match records the alias and method, so the correction UI can show evidence and the
evaluation can report precision per method.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache

from rapidfuzz import fuzz, process

from placeiq.config import TAXONOMY_PATH

FUZZY_MIN_ALIAS_LEN = 7
FUZZY_THRESHOLD = 90

_B = r"[a-z0-9+#]"              # characters that continue a token (lower-case text)
_LIST_BEFORE = r"(?:^|[,;:/(•|·]|\band\b|\b&)[ \t]*"
_LIST_AFTER = r"(?=[ \t]*(?:$|[,;/)|·]|\band\b|&))"


@dataclass(frozen=True)
class SkillMatch:
    skill: str
    alias: str
    method: str  # "exact" | "strict" | "fuzzy"
    score: float


@lru_cache(maxsize=1)
def load_taxonomy() -> dict[str, dict]:
    return json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))


def skill_categories() -> dict[str, str]:
    return {skill: entry["category"] for skill, entry in load_taxonomy().items()}


def _alias_regex(alias: str) -> str:
    return r"\s+".join(re.escape(part) for part in alias.split())


@lru_cache(maxsize=1)
def _compiled():
    exact, strict, fuzzy, known = [], [], [], set()
    for skill, entry in load_taxonomy().items():
        for alias in entry.get("aliases", []):
            a = alias.lower()
            known.add(a)
            exact.append((skill, alias, re.compile(rf"(?<!{_B}){_alias_regex(a)}(?!{_B})")))
            if len(a) >= FUZZY_MIN_ALIAS_LEN:
                fuzzy.append((skill, a))
        for alias in entry.get("strict", []):
            known.add(alias.lower())
            strict.append((skill, alias, re.compile(rf"{_LIST_BEFORE}({re.escape(alias)}){_LIST_AFTER}", re.MULTILINE)))
    return exact, strict, fuzzy, frozenset(known)


def normalize(text: str) -> str:
    """Lower-case and blank out unsupported characters, preserving length so that match
    offsets line up with the original text."""
    out = []
    for ch in text:
        low = ch.lower()
        if len(low) != 1:
            low = " "
        out.append(low if (low.isascii() and (low.isalnum() or low in "+#./-\n")) else " ")
    return "".join(out)


def _ngrams(text: str, max_n: int = 3) -> list[str]:
    tokens = [t.strip(".") for t in re.findall(r"[a-z0-9+#.]+", text)]
    tokens = [t for t in tokens if t]
    grams = set()
    for n in range(1, max_n + 1):
        for i in range(len(tokens) - n + 1):
            grams.add(" ".join(tokens[i:i + n]))
    return list(grams)


def extract_skill_matches(text: str, use_fuzzy: bool = True) -> list[SkillMatch]:
    if not text or not text.strip():
        return []
    exact, strict, fuzzy, known = _compiled()
    norm = normalize(text)

    # Collect every candidate span, then accept longest-first without overlaps.
    candidates = []
    for skill, alias, pattern in exact:
        for m in pattern.finditer(norm):
            candidates.append((m.start(), m.end(), skill, alias, "exact"))
    for skill, alias, pattern in strict:
        for m in pattern.finditer(text):
            candidates.append((m.start(1), m.end(1), skill, alias, "strict"))
    candidates.sort(key=lambda c: (-(c[1] - c[0]), c[0]))
    taken: list[tuple[int, int]] = []
    found: dict[str, SkillMatch] = {}
    for start, end, skill, alias, method in candidates:
        if any(start < e and s < end for s, e in taken):
            continue
        taken.append((start, end))
        found.setdefault(skill, SkillMatch(skill, alias, method, 100.0))

    if use_fuzzy:
        grams = [g for g in _ngrams(norm) if g not in known]
        for skill, alias in fuzzy:
            if skill in found:
                continue
            candidates_f = [g for g in grams if g[0] == alias[0] and abs(len(g) - len(alias)) <= 2]
            hit = process.extractOne(alias, candidates_f, scorer=fuzz.ratio, score_cutoff=FUZZY_THRESHOLD)
            if hit:
                found[skill] = SkillMatch(skill, hit[0], "fuzzy", float(hit[1]))

    return sorted(found.values(), key=lambda m: m.skill)


def extract_skills(text: str, use_fuzzy: bool = True) -> set[str]:
    return {m.skill for m in extract_skill_matches(text, use_fuzzy)}
