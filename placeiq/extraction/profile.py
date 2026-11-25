"""Heuristic first draft of the non-skill profile fields.

These are *suggestions* for the correction interface, never committed as-is. Anything not
found is left as None and listed in `needs_review` so the UI forces the student to fill it.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from placeiq.extraction.skills import extract_skill_matches

_SECTION_HEADINGS = {
    "internships": r"(work\s+)?experience|internships?|professional experience|employment",
    "projects": r"(academic\s+|personal\s+|key\s+)?projects?",
    "certifications": r"certifications?|certificates?|licen[cs]es?( & certifications)?|courses",
    "education": r"education|academic(s| details| qualifications)?",
    "skills": r"(technical\s+)?skills(\s+summary)?|technologies|tech stack",
    "other": r"achievements?|awards?|extra[- ]?curricular|positions? of responsibility|hobbies|interests|languages|summary|objective|profile",
}
_HEADING_RE = {k: re.compile(rf"^\s*({v})\s*:?\s*$", re.IGNORECASE) for k, v in _SECTION_HEADINGS.items()}
_BULLET = re.compile(r"^\s*(?:[•\-*–●▪◦➢►✓]|o(?=\s))\s*")
_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
_DATE_RANGE = re.compile(rf"(?:{_MONTH}\s*)?\b(?:19|20)\d{{2}}\s*[-–—to]+\s*(?:(?:{_MONTH}\s*)?(?:19|20)\d{{2}}|present|current|now)",
                         re.IGNORECASE)
_CGPA = re.compile(r"\b(?:c\.?g\.?p\.?a|cpi|gpa|sgpa)\b[^0-9\n]{0,15}(\d{1,2}(?:\.\d{1,2})?)", re.IGNORECASE)
_BACKLOGS = re.compile(r"(\d+)\s*(?:active\s+)?backlogs?", re.IGNORECASE)
_BRANCHES = [
    ("CSE", r"computer science|\bcse\b"),
    ("IT", r"information technology|\bb\.?\s?tech\.?\s*\(?it\)?"),
    ("ECE", r"electronics (and|&) communication|\bece\b"),
    ("EEE", r"electrical (and|&) electronics|\beee\b"),
    ("ME", r"mechanical engineering|\bmech\b"),
]


@dataclass
class ProfileDraft:
    branch: str | None = None
    cgpa: float | None = None
    active_backlogs: int | None = None
    internships: int | None = None
    projects: int | None = None
    certifications: int | None = None
    skills: list[str] = field(default_factory=list)
    skill_evidence: dict[str, str] = field(default_factory=dict)
    needs_review: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def split_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Markdown CVs mark headings with '#' and bold with '**'.
        bare = stripped.lstrip("#").strip().strip("*_").strip()
        heading = next((k for k, rx in _HEADING_RE.items() if rx.match(bare)), None)
        if heading:
            current = heading
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(stripped)
    return sections


def _is_title(line: str) -> bool:
    if _BULLET.match(line) or len(line) < 4:
        return False
    letters = [c for c in line if c.isalpha()]
    mostly_upper = len(letters) >= 4 and sum(c.isupper() for c in letters) / len(letters) > 0.6
    bold_title = line.startswith("**") or line.startswith("###")
    return mostly_upper or bold_title or "|" in line or bool(_DATE_RANGE.search(line))


def _count_entries(lines: list[str], ignore: set[str]) -> int:
    """Count entry *titles* (upper-case, '|'-separated or dated lines). Description lines and
    bullets under a title are not entries. A bullet-only list counts its bullets; a plain
    list of short lines counts the lines."""
    lines = [l for l in lines if l not in ignore]
    titles = [l for l in lines if _is_title(l)]
    if titles:
        return len(titles)
    bullets = [l for l in lines if _BULLET.match(l)]
    return len(bullets) if bullets else len(lines)


def draft_profile(text: str) -> ProfileDraft:
    d = ProfileDraft()
    sections = split_sections(text)

    m = _CGPA.search(text)
    if m and 0 < float(m.group(1)) <= 10:
        d.cgpa = float(m.group(1))
    m = _BACKLOGS.search(text)
    if m:
        d.active_backlogs = int(m.group(1))
    lowered = text.lower()
    for code, rx in _BRANCHES:
        if re.search(rx, lowered):
            d.branch = code
            break

    # Page headers (usually the student's name) repeat on later pages; never count them.
    header = set(sections.get("header", [])[:2])
    for key in ("internships", "projects", "certifications"):
        if key in sections:
            setattr(d, key, _count_entries(sections[key], header))

    matches = extract_skill_matches(text)
    d.skills = [m.skill for m in matches]
    d.skill_evidence = {m.skill: f"{m.method}:{m.alias}" for m in matches}

    # Counts are always estimates; everything goes to review, missing fields flagged first.
    d.needs_review = [k for k in ("branch", "cgpa", "active_backlogs", "internships", "projects", "certifications")
                      if getattr(d, k) is None]
    return d
