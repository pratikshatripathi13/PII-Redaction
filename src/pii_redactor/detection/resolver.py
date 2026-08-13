"""Resolve overlapping spans from multiple detectors into a non-overlapping set.

Priority (higher wins on overlap). ADDRESS is highest so that when an address
block overlaps a phone/email, the whole block is redacted (covering the contact
detail) rather than leaving a fragment. Among equal priority, the longer span
wins; ties break by earliest start.
"""
from __future__ import annotations

from ..models import Span

PRIORITY = {
    "ADDRESS": 5,
    "NAME": 4,
    "COMPANY": 4,
    "EMAIL": 3,
    "PHONE": 3,
    "SSN": 3,
    "CREDIT_CARD": 3,
    "DOB": 3,
    "IP": 3,
}


def resolve(spans: list[Span]) -> list[Span]:
    ordered = sorted(
        spans,
        key=lambda s: (-PRIORITY.get(s.category, 0), -(s.end - s.start), s.start),
    )
    kept: list[Span] = []
    for s in ordered:
        if not any(s.overlaps(k) for k in kept):
            kept.append(s)
    kept.sort(key=lambda s: s.start)
    return kept
