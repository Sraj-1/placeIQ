"""Project-wide paths, constants and local settings for the PlaceIQ engine.

Layout of the placeiq-app folder:
    placeiq/         this Python package (engine + API service)
    web/             the Next.js interface (talks to this engine through its /api/engine proxy)
    placeiq-data/    institution data: companies.json, jds/, templates/, the SQLite database,
                     raw/processed/synthetic datasets and model artifacts (personal data git-ignored)

Settings come from environment variables, falling back to `.env` in the app folder.
`python -m placeiq init` adds PlaceIQ's entries to that file (appending, never overwriting),
so nothing external is needed.
"""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent          # the placeiq-app folder
ENV_PATH = ROOT / ".env"
load_dotenv(ENV_PATH, override=False)

PQ_DIR = Path(os.environ.get("PLACEIQ_DATA_DIR") or ROOT / "placeiq-data")
DATA_DIR = PQ_DIR
ARTIFACTS_DIR = PQ_DIR / "artifacts"
FIGURES_DIR = ARTIFACTS_DIR / "figures"
CONFIG_DIR = PQ_DIR
JD_DIR = PQ_DIR / "jds"
TAXONOMY_PATH = Path(__file__).resolve().parent / "extraction" / "taxonomy.json"
COMPANIES_PATH = PQ_DIR / "companies.json"

MODEL_PATH = ARTIFACTS_DIR / "model.joblib"
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"

# The local API service the web app talks to (through its /api/engine proxy).
API_HOST = os.environ.get("PLACEIQ_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("PLACEIQ_API_PORT", "8765"))

# Small hosting plans (e.g. Render free: ~0.1 CPU, 512 MB) can't retrain in time or memory.
# With this set, the deployed app serves the model built into the image; retrain locally and redeploy.
TRAINING_DISABLED = os.environ.get("PLACEIQ_DISABLE_TRAINING", "").strip().lower() in ("1", "true", "yes")

TARGET = "placed"
RANDOM_STATE = 42
CV_FOLDS = 5


def database_url() -> str:
    """SQLite file by default (zero install). Set DATABASE_URL for PostgreSQL, e.g.
    postgresql+psycopg://user:pass@localhost:5432/placeiq (needs `pip install psycopg[binary]`)."""
    return os.environ.get("DATABASE_URL") or f"sqlite:///{(PQ_DIR / 'placeiq.db').as_posix()}"


def ensure_env() -> bool:
    """Add PLACEIQ_SALT to .env if missing (appending, never rewriting other entries).
    Returns True if anything was added."""
    load_dotenv(ENV_PATH, override=False)
    if os.environ.get("PLACEIQ_SALT"):
        return False
    block = ("\n# --- PlaceIQ (local secrets; never commit this file) ---\n"
             f"PLACEIQ_SALT={secrets.token_hex(32)}\n"
             "# DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/placeiq\n")
    with ENV_PATH.open("a", encoding="utf-8") as f:
        f.write(block)
    load_dotenv(ENV_PATH, override=True)
    return True
