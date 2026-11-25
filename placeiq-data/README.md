# Data handling

Follows synopsis §4.2. Lives inside the career-ops checkout. **Nothing under `raw/`, `processed/`, `synthetic/` or `artifacts/`, and not the database, is committed** (see `.gitignore`).

| Folder | Contents |
|---|---|
| `templates/` | Column layouts to hand to the placement cell / annotators. Example rows are fake. |
| `raw/` | Files as received. Delete resumes once features are extracted. |
| `processed/` | Anonymised, feature-ready CSVs (`student_hash` only, no names/emails/phones). |
| `synthetic/` | Generated fake data for development only. Never report results from it. |

## Historical records (`historical_records_template.csv`)

| Column | Type | Notes |
|---|---|---|
| `student_hash` | str | `placeiq.data.anonymize.hash_identifier(roll_no)`; needs `PLACEIQ_SALT` set |
| `batch_year` | int | Graduating year |
| `branch` | str | CSE, IT, ECE, ... |
| `cgpa` | float | 0–10 |
| `active_backlogs` | int | At the time of placement season |
| `internships`, `projects`, `certifications` | int | Counts |
| `skills` | str | `;`-separated canonical names from `placeiq/extraction/taxonomy.json` |
| `rounds_cleared` | int | **Outcome-side. Never used as a model feature** (it leaks the label). Kept for descriptive analysis only. |
| `placed` | 0/1 | Target |
| `gender` | optional | M / F / O. **Fairness audit only**, never a model feature |

Target: ≥ 200 records over the two most recent batches. Under 150 → report the classifier as indicative with confidence intervals (the training script prints bootstrap CIs).

## Annotation set (`annotation_template.csv`)

50 resumes, skills hand-labelled with canonical taxonomy names. Used by
`python -m placeiq.extraction.evaluate` to report precision / recall / F1 (target F1 > 0.80).
Two annotators per resume where possible; resolve disagreements before scoring.

## Consent

Collect explicit consent before any record is used. Keep the signed forms with the
placement cell, not in this repository.

## Raw intake file (what the placement cell provides)

`python -m placeiq ingest` takes the raw file and produces the anonymised training table. The raw
file is the template above with these differences:

| Column | Notes |
|---|---|
| `student_id` | Roll / enrolment number **instead of** `student_hash`; hashed during ingest and never written out |
| `skills` | Optional. If blank, skills are extracted from the resume |
| `resume_file` | Optional. File name (.pdf or .txt) inside the `--resumes` folder |
| `jd_id` | Optional. Job description the student applied to, `placeiq-data/jds/<jd_id>.txt`; needed for the similarity baseline |

`placeiq-data/synthetic/records.csv` (created by `python -m placeiq demo`) is a complete example of this layout.
After ingest, delete the raw resumes (§4.2): only features and similarity scores are kept.

## From career-ops users (data-collection bridge)

Students who used career-ops can export their own outcome row, with consent:

```powershell
node placeiq-outcome.mjs --roll <roll-number> --out outcome.csv
```

It writes one row in the raw intake layout above, plus `careerops_score` (their mean career-ops LLM job-fit score over
roles applied to). Concatenate the students' files and run `python -m placeiq ingest`. `careerops_score` becomes the
`sim_llm_fit` **baseline** in the §4.6 comparison, never a model feature.
