"""Upload PlaceIQ to a Hugging Face Space (Docker SDK).

Run it yourself after signing in with your own token:

    .venv\\Scripts\\pip install -U huggingface_hub
    .venv\\Scripts\\hf auth login                  # paste a token with "write" access
    .venv\\Scripts\\python deploy\\hf_upload.py YOUR-USERNAME/placeiq [--private]

It creates the Space if needed (Docker SDK, free CPU) and uploads the project, skipping
local-only files (virtualenv, node_modules, builds, databases, personal data). Binary files
such as fonts are stored the way the Hub requires automatically. Then add the two secrets
(see DEPLOY.md); the Space builds and starts by itself.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parent.parent
IGNORE = [
    ".venv/**", "**/__pycache__/**", "**/*.pyc", ".pytest_cache/**", ".env", ".env.*",
    "web/node_modules/**", "web/.next/**",
    "placeiq-data/placeiq.db*", "placeiq-data/artifacts/**", "placeiq-data/synthetic/**",
    "placeiq-data/raw/**", "placeiq-data/processed/**", "placeiq-data/student/**",
    "notebooks/**", "start.bat", ".git/**",
]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_id", help="your-username/space-name")
    ap.add_argument("--private", action="store_true", help="make the Space private")
    args = ap.parse_args()
    api = HfApi()
    api.create_repo(args.repo_id, repo_type="space", space_sdk="docker", private=args.private, exist_ok=True)
    api.upload_folder(repo_id=args.repo_id, repo_type="space", folder_path=str(ROOT), ignore_patterns=IGNORE,
                      commit_message="Deploy PlaceIQ")
    print(f"Uploaded. Open https://huggingface.co/spaces/{args.repo_id} and add the secrets from DEPLOY.md.")
