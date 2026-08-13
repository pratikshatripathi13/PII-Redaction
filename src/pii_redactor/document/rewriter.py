"""Apply replacements at the run level, preserving per-run formatting.

Strategy (see README "DOCX preservation"):
  * Unreplaced original characters stay in the exact run they came from, so their
    formatting (bold, size, style) is untouched.
  * Each replacement's synthetic text is written wholly into the run where the PII
    *started*, inheriting that run's formatting.
  * Characters covered by a replacement are dropped from every run that held them.

This correctly handles multiple replacements per run and replacements that span
several runs, without ever rebuilding the paragraph or losing run boundaries.
"""
from __future__ import annotations

from ..models import Span
from .loader import TextUnit


def apply_replacements(unit: TextUnit, replacements: list[tuple[Span, str]]) -> None:
    if not replacements:
        return
    full = unit.text
    runs = unit.runs
    offsets = unit.run_offsets

    # Build ordered segments over the whole unit: (orig_start, orig_end, text, replaced)
    spans = sorted(replacements, key=lambda x: x[0].start)
    segments: list[tuple[int, int, str, bool]] = []
    pos = 0
    for span, new_text in spans:
        if span.start < pos:
            continue  # defensive: skip overlaps (resolver should prevent these)
        if span.start > pos:
            segments.append((pos, span.start, full[pos:span.start], False))
        segments.append((span.start, span.end, new_text, True))
        pos = span.end
    if pos < len(full):
        segments.append((pos, len(full), full[pos:], False))

    # Redistribute segments back into runs by original start offset.
    for run, (rs, re) in zip(runs, offsets):
        buf = []
        for os_, oe_, text, replaced in segments:
            if replaced:
                # Emit the whole replacement in the single positive-width run that
                # contains its start offset. Zero-width runs (rs == re, common in
                # DOCX) must never receive it, or the text would be duplicated.
                if rs <= os_ < re:
                    buf.append(text)
            else:
                lo, hi = max(os_, rs), min(oe_, re)
                if lo < hi:
                    buf.append(full[lo:hi])
        run.text = "".join(buf)
