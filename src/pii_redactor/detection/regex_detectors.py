"""Deterministic, high-precision detectors for structured PII types."""
from __future__ import annotations

import re

from ..models import Span
from .base import Detector, RegexDetector

# ----------------------------------------------------------------------------- EMAIL
class EmailDetector(RegexDetector):
    category = "EMAIL"
    name = "regex.email"
    pattern = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


# ----------------------------------------------------------------------------- PHONE
class PhoneDetector(Detector):
    """Indian + international phone numbers.

    Candidate = a run of digits/separators (NO commas, so comma-grouped financial
    figures like 26,704,570 can never match). Validated by digit count and prefix,
    so 6-digit PIN codes and 8-digit DIN-like values are rejected.
    """
    category = "PHONE"
    name = "regex.phone"
    # optional +91 / 0 prefix, then 10-13 digits split by space/hyphen/() only
    # Trailing lookahead is (?!\d) only — NOT (?![\d,]) — so phone numbers in a
    # comma-separated list ("...30752929, +91 22 30752928") are still matched.
    # Comma-grouped financial figures are excluded by the leading (?<![\d,.]) and
    # by _plausible() (digit count + currency context), not by a trailing comma.
    _cand = re.compile(r"(?<![\d,.])(?:\+\s?)?(?:91[\s-]?|0)?(?:\(?\d{2,5}\)?[\s-]?)?\d{3,5}[\s-]?\d{3,6}(?!\d)")

    def detect(self, text: str) -> list[Span]:
        spans = []
        for m in self._cand.finditer(text):
            raw = m.group(0)
            digits = re.sub(r"\D", "", raw)
            if not self._plausible(digits, raw, m, text):
                continue
            s, e = m.start(), m.end()
            # trim leading/trailing spaces captured by the pattern
            while s < e and text[s] in " -":
                s += 1
            while e > s and text[e - 1] in " -":
                e -= 1
            spans.append(Span(s, e, text[s:e], self.category, self.name, 1.0))
        return spans

    @staticmethod
    def _plausible(digits: str, raw: str, m: re.Match, text: str) -> bool:
        n = len(digits)
        if n < 10 or n > 13:
            return False
        # Reject amounts: preceded by currency or followed by units.
        after = text[m.end():m.end() + 12].lower()
        before = text[max(0, m.start() - 2):m.start()]
        if "₹" in before or "rs" in before.lower():
            return False
        if re.match(r"\s*(million|billion|crore|lakh|%|per cent)", after):
            return False
        # Indian mobile (10 digits starting 6-9), or has +91/STD structure, or intl.
        if n == 10 and digits[0] in "6789":
            return True
        if digits.startswith("91") and n in (11, 12):
            return True
        if raw.strip().startswith("+"):
            return True
        # STD-code landline written with a separator (e.g. "022-68052182", "20 45053237")
        if ("-" in raw or " " in raw) and n in (10, 11):
            return True
        return False


# ----------------------------------------------------------------------------- SSN
class SSNDetector(RegexDetector):
    category = "SSN"
    name = "regex.ssn"
    pattern = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


# ----------------------------------------------------------------------------- CREDIT CARD
class CreditCardDetector(RegexDetector):
    category = "CREDIT_CARD"
    name = "regex.credit_card"
    # 13-16 digits, optionally grouped in 4s by space/hyphen. Luhn-validated.
    pattern = re.compile(r"\b(?:\d[ -]?){13,16}\b")

    def validate(self, value, match, text) -> bool:
        digits = re.sub(r"\D", "", value)
        if len(digits) not in (13, 14, 15, 16):
            return False
        return _luhn_ok(digits)

    def trim(self, start, end, value):
        # strip a trailing separator if the pattern grabbed one
        while value and value[-1] in " -":
            end -= 1; value = value[:-1]
        return start, end


def _luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for d in reversed(digits):
        x = ord(d) - 48
        if alt:
            x *= 2
            if x > 9:
                x -= 9
        total += x
        alt = not alt
    return total % 10 == 0


# ----------------------------------------------------------------------------- IP
class IPDetector(RegexDetector):
    category = "IP"
    name = "regex.ip"
    pattern = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

    def validate(self, value, match, text) -> bool:
        return all(0 <= int(o) <= 255 for o in value.split("."))


# ----------------------------------------------------------------------------- DOB
class DOBDetector(Detector):
    """Date of birth = a date that is *contextually* a birth date.

    A plain date detector would fire on all 318 corporate/financial dates in this
    document (incorporation, offer, FY-end). We only accept a date when a birth
    trigger word appears shortly before it. Result on this document: 0 (correct).
    """
    category = "DOB"
    name = "rule.dob"
    _date = re.compile(
        r"\b(?:\d{1,2}\s+)?(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{1,2},?\s+\d{4}\b"
        r"|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
    )
    _trigger = re.compile(r"(?i)(date of birth|born on|born|d\.?o\.?b\.?|aged)")

    def detect(self, text: str) -> list[Span]:
        spans = []
        for m in self._date.finditer(text):
            window = text[max(0, m.start() - 40):m.start()]
            if self._trigger.search(window):
                spans.append(Span(m.start(), m.end(), m.group(0), self.category, self.name, 1.0))
        return spans
