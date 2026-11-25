"""PDF → text (synopsis §4.3). PDF only; output always goes through the correction UI."""
from __future__ import annotations

import logging
from typing import BinaryIO

import pdfplumber

log = logging.getLogger(__name__)

_BULLET_GLYPHS = {"": "•", "": "•", "▪": "•", "●": "•", "": "•"}


def extract_text(source: str | BinaryIO) -> str:
    """Extract text from a PDF path or file-like object. Returns "" if nothing is readable
    (e.g. a scanned image PDF) so the caller can route the student to manual entry."""
    if hasattr(source, "seek"):
        source.seek(0)
    pages: list[str] = []
    try:
        with pdfplumber.open(source) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text(x_tolerance=1.5, y_tolerance=3) or ""
                if not text.strip():
                    log.warning("No extractable text on page %d", i + 1)
                pages.append(text)
    except Exception:  # pdfplumber raises a variety of parser errors
        log.exception("PDF parsing failed")
        return ""
    text = "\n".join(pages)
    for glyph, repl in _BULLET_GLYPHS.items():
        text = text.replace(glyph, repl)
    return text.strip()
