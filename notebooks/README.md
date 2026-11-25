# Notebooks

Reproducible evaluation for the project report (deliverable 5.1). Each notebook calls into the
`placeiq` package rather than re-implementing anything. It uses `data/processed/historical.csv`
when that exists, otherwise the synthetic demo data (and says so in its first output).

| Notebook | Contents |
|---|---|
| `01_extraction_eval.ipynb` | Extraction P/R/F1 on the annotations saved in the web tool, per-method precision, no-fuzzy ablation, error analysis |
| `02_classifier_and_baseline.ipynb` | LR vs RF cross-validation, per-class metrics, coefficients, the similarity-vs-classifier comparison, fairness audit, report figures |
| `03_cohort_descriptives.ipynb` | Placement rate by branch, CGPA band, backlogs and internships |

Run (from the project root):

```powershell
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\jupyter notebook notebooks
```

Notebook 02 retrains the model and overwrites `artifacts/` (model, metrics, figures).
