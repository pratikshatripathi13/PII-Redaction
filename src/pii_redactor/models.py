"""Core data types shared across the pipeline.

Kept deliberately small and dependency-free so detectors can be unit-tested
against plain strings without touching python-docx.
"""
from __future__ import annotations

from dataclasses import dataclass

# The nine PII categories required by the assignment.
CATEGORIES = [
    "EMAIL", "PHONE", "NAME", "COMPANY", "ADDRESS",
    "SSN", "CREDIT_CARD", "DOB", "IP",
]


@dataclass(frozen=True)
class Span:
    """A detected PII occurrence within a single text unit.

    start/end are character offsets into the unit's concatenated text
    (Python slice semantics: text[start:end] == text).
    """
    start: int
    end: int
    text: str
    category: str
    detector: str
    confidence: float = 1.0

    def overlaps(self, other: "Span") -> bool:
        return self.start < other.end and other.start < self.end

    def __len__(self) -> int:
        return self.end - self.start


@dataclass(frozen=True)
class GoldSpan:
    """A ground-truth PII span (category + offsets only; no raw value stored)."""
    unit_id: str
    start: int
    end: int
    category: str
