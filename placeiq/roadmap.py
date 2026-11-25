"""Role and recruiter gap roadmap.

- Roles: each job description in placeiq-data/jds is reduced to its taxonomy skills (with the same
  evaluated extractor used for resumes). The student sees which they have, which are missing,
  and how the model's estimate would change if they learned the missing ones.
- Recruiters: each eligibility rule in placeiq-data/companies.json is checked and every gap is
  classified as fixable before placement season (skills, backlogs, a CGPA shortfall of at most
  0.5) or not (branch, larger CGPA shortfall). "Near" recruiters have only fixable gaps.
"""
from __future__ import annotations

from functools import lru_cache

from placeiq.config import JD_DIR
from placeiq.eligibility.filter import load_companies
from placeiq.explain.whatif import score
from placeiq.extraction.skills import extract_skills
from placeiq.features.assemble import parse_skills

MAX_FIXABLE_CGPA_GAP = 0.5


@lru_cache(maxsize=1)
def role_profiles() -> dict[str, dict]:
    roles = {}
    for path in sorted(JD_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        title = next((line.strip() for line in text.splitlines() if line.strip()), path.stem)
        roles[path.stem] = {"title": title, "skills": sorted(extract_skills(text))}
    return roles


def company_gaps(profile: dict, company: dict) -> list[dict]:
    gaps = []
    skills = set(parse_skills(profile.get("skills", [])))
    if company.get("branches") and profile["branch"] not in company["branches"]:
        gaps.append({"type": "branch", "detail": f"Open to {', '.join(company['branches'])} only", "fixable": False})
    min_cgpa = company.get("min_cgpa", 0)
    if profile["cgpa"] < min_cgpa:
        gap = round(min_cgpa - profile["cgpa"], 2)
        gaps.append({"type": "cgpa", "detail": f"CGPA {profile['cgpa']:g} is {gap:g} below the {min_cgpa:g} cut-off",
                     "fixable": gap <= MAX_FIXABLE_CGPA_GAP})
    max_bl = company.get("max_active_backlogs", 99)
    if profile["active_backlogs"] > max_bl:
        gaps.append({"type": "backlogs", "detail": f"Clear {profile['active_backlogs'] - max_bl} backlog(s) "
                                                  f"(at most {max_bl} allowed)", "fixable": True})
    need = set(company.get("required_skills_any", []))
    if need and not need & skills:
        gaps.append({"type": "skills", "detail": f"Learn one of: {', '.join(sorted(need))}", "fixable": True,
                     "options": sorted(need)})
    return gaps


def roadmap(bundle: dict | None, profile: dict) -> dict:
    profile = {**profile, "skills": sorted(set(parse_skills(profile.get("skills", []))))}
    have = set(profile["skills"])

    roles = []
    for jd_id, role in role_profiles().items():
        needed = set(role["skills"])
        if not needed:
            continue
        missing = sorted(needed - have)
        roles.append({"id": jd_id, "title": role["title"], "have": sorted(needed & have), "missing": missing,
                      "coverage": round(len(needed & have) / len(needed), 4)})
    roles.sort(key=lambda r: -r["coverage"])
    if bundle is not None and roles:
        base = score(bundle, [profile])[0]
        learned = score(bundle, [{**profile, "skills": sorted(have | set(r["missing"]))} for r in roles])
        for r, p in zip(roles, learned):
            r["probability_if_learned"] = p
            r["delta_if_learned"] = round(p - base, 4)

    companies = {"eligible": [], "near": [], "out_of_reach": []}
    for c in load_companies():
        gaps = company_gaps(profile, c)
        entry = {"name": c["name"], "gaps": gaps}
        if not gaps:
            companies["eligible"].append(entry)
        elif all(g["fixable"] for g in gaps):
            companies["near"].append(entry)
        else:
            companies["out_of_reach"].append(entry)
    companies["near"].sort(key=lambda e: len(e["gaps"]))
    return {"roles": roles, "companies": companies}
