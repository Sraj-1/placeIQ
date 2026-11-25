from placeiq.data.anonymize import hash_identifier, strip_contact_info
from placeiq.extraction.evaluate import score
from placeiq.extraction.profile import draft_profile
from placeiq.extraction.skills import extract_skill_matches, extract_skills


def test_no_substring_false_positives():
    s = extract_skills("Built apps in JavaScript and MySQL; code on GitHub")
    assert {"javascript", "mysql", "github"} <= s
    assert not {"java", "sql", "git"} & s


def test_symbols_preserved():
    s = extract_skills("Languages: C++, C#, Node.js, C")
    assert {"c++", "c#", "node.js", "c"} <= s


def test_strict_aliases_ignore_ordinary_words():
    assert not {"excel", "express", "rest api"} & extract_skills("I excel at teamwork and express ideas; the rest is history")
    assert "excel" in extract_skills("Advanced MS Excel and Power BI")


def test_fuzzy_catches_typos_only_for_long_aliases():
    matches = {m.skill: m for m in extract_skill_matches("Worked with tensorflwo and kubernets")}
    assert matches["tensorflow"].method == "fuzzy"
    assert matches["kubernetes"].method == "fuzzy"


def test_extraction_metrics():
    res = score({"a": {"python", "sql"}}, {"a": {"python", "java"}})
    assert res["micro"] == {"precision": 0.5, "recall": 0.5, "f1": 0.5}


def test_draft_profile():
    text = """B.Tech Computer Science, CGPA: 8.4/10
PROJECTS
Resume Matcher
• Built with Python and Flask
Placement Predictor
• scikit-learn
CERTIFICATIONS
• AWS Cloud Practitioner
• Google Data Analytics
"""
    d = draft_profile(text)
    assert d.branch == "CSE" and d.cgpa == 8.4
    assert d.projects == 2 and d.certifications == 2
    assert {"python", "flask", "scikit-learn", "aws"} <= set(d.skills)
    assert "internships" in d.needs_review


def test_anonymize(monkeypatch):
    monkeypatch.setenv("PLACEIQ_SALT", "test-salt")
    assert hash_identifier("01234567890") == hash_identifier(" 01234567890 ")
    cleaned = strip_contact_info("me@x.com +91 98765 43210 github.com/me linkedin.com/in/me")
    assert "@" not in cleaned and "98765" not in cleaned and "github" not in cleaned


def test_draft_profile_from_markdown_cv():
    md = """# Student

## Education
**B.Tech, Computer Science and Engineering** (2022 - 2026)
CGPA: 7.4/10

## Projects
CAMPUS PORTAL | 2025
- Built with React and Flask
EXPENSE APP | 2024
- Kotlin and SQLite

## Internships
WEB INTERN - STARTUP | Jun 2025 - Jul 2025
- React components

## Certifications
- Python for Data Science
"""
    d = draft_profile(md)
    assert (d.branch, d.cgpa, d.projects, d.internships, d.certifications) == ("CSE", 7.4, 2, 1, 1)
    assert {"react", "flask", "kotlin", "sqlite", "python"} <= set(d.skills)
