"""Detector interface. Every PII category is an independently testable Detector."""
from __future__ import annotations

import re

from ..models import Span


class Detector:
    category = "BASE"
    name = "base"

    def detect(self, text: str) -> list[Span]:
        raise NotImplementedError


class RegexDetector(Detector):
    """Base for pattern detectors. Subclasses set `pattern` and may override
    `validate()` to reject false positives (e.g. Luhn for cards, range for IPs)."""

    pattern: re.Pattern

    def detect(self, text: str) -> list[Span]:
        spans = []
        for m in self.pattern.finditer(text):
            value = m.group(0)
            if self.validate(value, m, text):
                s, e = self.trim(m.start(), m.end(), value)
                spans.append(Span(s, e, text[s:e], self.category, self.name, 1.0))
        return spans

    def validate(self, value: str, match: re.Match, text: str) -> bool:
        return True

    def trim(self, start: int, end: int, value: str) -> tuple[int, int]:
        return start, end
