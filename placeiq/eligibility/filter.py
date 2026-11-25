"""Static eligibility filter over the curated recruiter list (synopsis §4.9)."""
from __future__ import annotations

import json
from functools import lru_cache

from placeiq.config import COMPANIES_PATH
from placeiq.features.assemble import parse_skills


@lru_cache(maxsize=1)
def load_companies() -> list[dict]:
    return json.loads(COMPANIES_PATH.read_text(encoding="utf-8"))["companies"]


def check(profile: dict, company: dict) -> list[str]:
    """Return the reasons a profile fails a company's criteria (empty list = eligible)."""
    reasons = []
    if profile["cgpa"] < company.get("min_cgpa", 0):
        reasons.append(f"CGPA {profile['cgpa']} < {company['min_cgpa']}")
    if profile["active_backlogs"] > company.get("max_active_backlogs", 99):
        reasons.append(f"{profile['active_backlogs']} active backlogs > {company['max_active_backlogs']} allowed")
    if company.get("branches") and profile["branch"] not in company["branches"]:
        reasons.append(f"branch {profile['branch']} not eligible")
    need = set(company.get("required_skills_any", []))
    if need and not need & set(parse_skills(profile.get("skills", []))):
        reasons.append(f"needs one of: {', '.join(sorted(need))}")
    return reasons


def eligible_companies(profile: dict, companies: list[dict] | None = None) -> dict[str, list]:
    companies = companies if companies is not None else load_companies()
    result = {"eligible": [], "ineligible": []}
    for c in companies:
        reasons = check(profile, c)
        if reasons:
            result["ineligible"].append({"name": c["name"], "reasons": reasons})
        else:
            result["eligible"].append(c["name"])
    return result
