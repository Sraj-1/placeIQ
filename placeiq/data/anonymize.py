"""Anonymisation at the point of ingestion (synopsis §4.2).

Identifiers are replaced with a keyed hash (HMAC-SHA256) so the same student maps to the
same hash across files, but the hash cannot be reversed or brute-forced from roll numbers
without the secret salt. Set the salt once per project in the environment:

    $env:PLACEIQ_SALT = "<long random string>"   # PowerShell

Keep the salt out of the repository.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\d[\s-]?){10}\b")
_URL = re.compile(r"(?:https?://|www\.)\S+|(?:linkedin|github)\.com/\S+", re.IGNORECASE)


def _salt() -> bytes:
    salt = os.environ.get("PLACEIQ_SALT")
    if not salt:
        raise RuntimeError("PLACEIQ_SALT is not set; refusing to hash identifiers without a secret salt.")
    return salt.encode()


def hash_identifier(identifier: str, length: int = 16) -> str:
    """Stable, non-reversible id for a student (roll number, enrolment no., email)."""
    normalised = identifier.strip().lower().encode()
    return hmac.new(_salt(), normalised, hashlib.sha256).hexdigest()[:length]


def strip_contact_info(text: str) -> str:
    """Remove emails, phone numbers and profile URLs from resume text."""
    text = _EMAIL.sub(" ", text)
    text = _URL.sub(" ", text)
    text = _PHONE.sub(" ", text)
    return re.sub(r"[ \t]+", " ", text)
