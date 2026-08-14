"""Thin service used by the web app. It reuses the existing `redact()` pipeline —
there is no second redaction implementation.

Given uploaded .docx bytes and a list of categories to redact, it returns the redacted
.docx bytes, the audit-log bytes, and the redaction summary.
"""
from __future__ import annotations

import os
import tempfile

from .config import load_settings
from .models import CATEGORIES
from .redactor import redact

_DEFAULT_CONFIG = os.path.join(os.path.dirname(__file__), "..", "..", "config", "default.yaml")


def redact_bytes(file_bytes: bytes, selected_categories, use_spacy: bool = False,
                 config_path: str = _DEFAULT_CONFIG) -> dict:
    settings = load_settings(config_path)
    # Turn on only the categories the user selected.
    settings.categories = {c: (c in set(selected_categories)) for c in CATEGORIES}
    settings.use_spacy_ner = bool(use_spacy)

    with tempfile.TemporaryDirectory() as tmp:
        in_path = os.path.join(tmp, "input.docx")
        out_path = os.path.join(tmp, "redacted.docx")
        audit_path = os.path.join(tmp, "audit_log.jsonl")
        with open(in_path, "wb") as f:
            f.write(file_bytes)

        result = redact(in_path, out_path, settings)
        result.auditor.write_jsonl(audit_path)

        with open(out_path, "rb") as f:
            redacted_bytes = f.read()
        with open(audit_path, "rb") as f:
            audit_bytes = f.read()

    return {
        "redacted_bytes": redacted_bytes,
        "audit_bytes": audit_bytes,
        "summary": result.auditor.summary(),
    }
