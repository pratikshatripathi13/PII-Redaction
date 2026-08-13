"""End-to-end redaction pipeline."""
from __future__ import annotations

from dataclasses import dataclass

from .audit.auditor import Auditor
from .config import Settings
from .detection.registry import build_detectors
from .detection.resolver import resolve
from .document.loader import DocxDocument
from .document.rewriter import apply_replacements
from .models import Span
from .pseudonym.mapping_store import MappingStore


@dataclass
class RedactionOutput:
    auditor: Auditor
    predictions: dict          # unit_id -> list[Span] (for evaluation)
    unit_texts: dict           # unit_id -> original text (in-memory only)
    unit_lengths: dict         # unit_id -> char length (for token accuracy)
    kb: object


def redact(input_path: str, output_path: str | None, settings: Settings) -> RedactionOutput:
    doc = DocxDocument(input_path)
    units = list(doc.units())
    full_text = "\n".join(u.text for u in units)

    detectors, kb = build_detectors(settings, doc, full_text)
    store = MappingStore(settings.salt)
    auditor = Auditor()
    predictions: dict = {}
    unit_texts: dict = {}
    unit_lengths: dict = {}

    for unit in units:
        text = unit.text
        if not text.strip():
            continue
        unit_lengths[unit.unit_id] = len(text)
        raw_spans: list[Span] = []
        for det in detectors:
            raw_spans.extend(det.detect(text))
        spans = resolve(raw_spans)
        if not spans:
            continue
        predictions[unit.unit_id] = spans
        unit_texts[unit.unit_id] = text

        replacements = []
        for span in spans:
            repl = store.replacement_for(span.category, span.text)
            hid = store.hashed_id(span.category, span.text)
            auditor.record(unit.unit_id, span.category, hid, repl)
            replacements.append((span, repl))
        apply_replacements(unit, replacements)

    if output_path:
        doc.save(output_path)
    return RedactionOutput(auditor, predictions, unit_texts, unit_lengths, kb)
