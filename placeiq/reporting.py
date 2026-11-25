"""Figures for the project report (PNG, 160 dpi), written by training into placeiq-data/artifacts/figures.

- roc_curves.png         ROC of LR, RF and every similarity signal on the same students
- confusion_matrix.png   primary model, out-of-fold, threshold 0.5
- coefficients.png       standardised logistic-regression coefficients
- calibration.png        reliability of the predicted probabilities (out-of-fold)
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.calibration import calibration_curve  # noqa: E402
from sklearn.metrics import roc_auc_score, roc_curve  # noqa: E402

INK, INK2, GRID = "#0b0b0b", "#52514e", "#e1e0d9"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"]  # validated categorical order
LABELS = {"oof_logistic_regression": "Logistic regression (PlaceIQ)", "oof_random_forest": "Random forest",
          "sim_tfidf": "Similarity: TF-IDF", "sim_sbert": "Similarity: Sentence-BERT",
          "sim_hybrid": "Similarity: hybrid", "sim_skill_overlap": "Similarity: skill overlap",
          "sim_llm_fit": "career-ops LLM job-fit score"}


def _style(ax, title: str, synthetic: bool):
    ax.set_title(title + ("  [SYNTHETIC DATA]" if synthetic else ""), loc="left", fontsize=11, color=INK)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#c3c2b7")
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def make_figures(oof: pd.DataFrame, results: dict, out_dir: Path) -> list[str]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    synthetic = results.get("synthetic_data", False)
    y = oof["placed"].to_numpy()
    written = []

    # ROC curves
    fig, ax = plt.subplots(figsize=(6.4, 5.2))
    cols = [c for c in LABELS if c in oof.columns]
    for color, c in zip(SERIES, cols):
        sub = oof.dropna(subset=[c])
        if sub["placed"].nunique() < 2:
            continue
        fpr, tpr, _ = roc_curve(sub["placed"], sub[c])
        auc = roc_auc_score(sub["placed"], sub[c])
        ax.plot(fpr, tpr, color=color, linewidth=2, label=f"{LABELS[c]}  (AUC {auc:.2f})")
    ax.plot([0, 1], [0, 1], color="#898781", linewidth=1, linestyle="--", label="Chance (AUC 0.50)")
    ax.set_xlabel("False positive rate", color=INK2)
    ax.set_ylabel("True positive rate", color=INK2)
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    _style(ax, "ROC: outcome-trained classifier vs similarity", synthetic)
    fig.tight_layout()
    fig.savefig(out_dir / "roc_curves.png", dpi=160)
    plt.close(fig)
    written.append("roc_curves.png")

    # Confusion matrix (primary model)
    primary = results.get("primary_model", "logistic_regression")
    cm = np.array(results["models"][primary]["confusion_matrix"])
    fig, ax = plt.subplots(figsize=(4.4, 3.8))
    ax.imshow(cm, cmap="Blues")
    for (i, j), v in np.ndenumerate(cm):
        ax.text(j, i, str(v), ha="center", va="center", fontsize=13,
                color="white" if v > cm.max() * 0.6 else INK)
    ax.set_xticks([0, 1], ["Not placed", "Placed"])
    ax.set_yticks([0, 1], ["Not placed", "Placed"])
    ax.set_xlabel("Predicted", color=INK2)
    ax.set_ylabel("Actual", color=INK2)
    ax.set_title("Confusion matrix (out-of-fold)" + ("\n[SYNTHETIC DATA]" if synthetic else ""), loc="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(out_dir / "confusion_matrix.png", dpi=160)
    plt.close(fig)
    written.append("confusion_matrix.png")

    # Coefficients
    coefs = results.get("coefficients", [])[:14][::-1]
    if coefs:
        fig, ax = plt.subplots(figsize=(6.4, 0.32 * len(coefs) + 1.2))
        vals = [c["coefficient"] for c in coefs]
        ax.barh([c["feature"] for c in coefs], vals, color=["#2a78d6" if v >= 0 else "#e34948" for v in vals], height=0.6)
        ax.axvline(0, color="#c3c2b7", linewidth=1)
        ax.set_xlabel("Log-odds per 1 SD (blue raises, red lowers placement odds)", color=INK2)
        _style(ax, "Logistic regression coefficients", synthetic)
        fig.tight_layout()
        fig.savefig(out_dir / "coefficients.png", dpi=160)
        plt.close(fig)
        written.append("coefficients.png")

    # Calibration
    col = f"oof_{primary}"
    frac, mean_pred = calibration_curve(y, oof[col], n_bins=8, strategy="quantile")
    fig, ax = plt.subplots(figsize=(4.8, 4.4))
    ax.plot([0, 1], [0, 1], color="#898781", linestyle="--", linewidth=1, label="Perfect calibration")
    ax.plot(mean_pred, frac, marker="o", markersize=6, color="#2a78d6", linewidth=2, label="Model")
    ax.set_xlabel("Predicted probability", color=INK2)
    ax.set_ylabel("Observed placement rate", color=INK2)
    ax.legend(fontsize=8, frameon=False)
    _style(ax, "Calibration (out-of-fold)", synthetic)
    fig.tight_layout()
    fig.savefig(out_dir / "calibration.png", dpi=160)
    plt.close(fig)
    written.append("calibration.png")
    return written
