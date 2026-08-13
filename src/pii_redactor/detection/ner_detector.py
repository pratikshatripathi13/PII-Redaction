"""Entity detection for NAME, COMPANY and ADDRESS.

Instead of a heavy statistical NER model (imprecise on Indian names, company and
address formats), we exploit the fact that a prospectus states its entities in
*structured* places: the board/DIN table, promoter and shareholder tables, and
"Contact Person:" / "X is our <title>" sentences. We bootstrap a KnowledgeBase of
person names from those anchors, then find every occurrence document-wide.
Companies are matched by a strong legal suffix (Limited/Ltd/LLP) plus the
promoter "Family Trust" pattern. Addresses are matched by an anchor + PIN code.

This generalises to any similarly-structured prospectus (the anchors are generic,
not hard-coded values), stays fully explainable, and needs no model download.
An optional spaCy detector can be added later behind the same Detector interface.
"""
from __future__ import annotations

import re

from ..models import Span
from .base import Detector

# Words that are never part of a person name (roles, labels, headings, table junk).
_STOP = {
    "the", "our", "and", "of", "to", "from", "also", "formerly",
    "board", "directors", "director", "promoter", "promoters", "group",
    "company", "committee", "shareholder", "shareholders", "equity", "share",
    "offer", "trust", "family", "limited", "private", "registered", "office",
    "india", "corporate", "identity", "chairman", "managing", "whole", "wholetime",
    "independent", "executive", "additional", "statutory", "auditors", "auditor",
    "compliance", "officer", "secretary", "chief", "financial", "manager", "head",
    "president", "website", "tel", "telephone", "email", "e-mail", "sebi",
    "registration", "address", "escrow", "refund", "syndicate", "sponsor",
    "collection", "account", "designated", "intermediaries", "members", "member",
    "lead", "managers", "book", "running", "registrar", "bank", "banks", "fund",
    "capital", "securities", "regulations", "act", "total", "subtotal",
    "sub-total", "anchor", "investor", "pay", "category", "particulars", "no",
    "name", "designation", "din",
}


def _clean_person(cand: str) -> str | None:
    """Trim label/role words from both ends and validate a person name."""
    toks = re.sub(r"\s+", " ", cand).strip().split()
    while toks and toks[0].lower().strip(".,") in _STOP:
        toks.pop(0)
    while toks and toks[-1].lower().strip(".,") in _STOP:
        toks.pop()
    if not (2 <= len(toks) <= 4):
        return None
    for t in toks:
        core = t.strip(".")
        if not core or not core[0].isupper() or any(c.isdigit() for c in core):
            return None
        if core.lower() in _STOP:
            return None
        if len(core) == 1 and not t.endswith("."):  # bare single letter (e.g. "A")
            return None
    return " ".join(toks)


# ------------------------------------------------------------------ KnowledgeBase
class KnowledgeBase:
    def __init__(self):
        self.persons: set[str] = set()

    @classmethod
    def build(cls, doc, full_text: str) -> "KnowledgeBase":
        kb = cls()
        kb._mine_tables(doc)
        kb._mine_text(full_text)
        return kb

    def _mine_tables(self, doc):
        for tbl in doc.doc.tables:
            if not tbl.rows:
                continue
            header = [c.text.strip().lower() for c in tbl.rows[0].cells]
            hset = " ".join(header)
            name_col = next((i for i, h in enumerate(header) if h.startswith("name")), None)
            if name_col is None:
                continue
            if not ("din" in hset or "designation" in hset or "promoter" in hset
                    or "shareholder" in hset):
                continue
            for row in tbl.rows[1:]:
                if name_col >= len(row.cells):
                    continue
                cleaned = _clean_person(re.sub(r"[\*\^&#()0-9]", " ", row.cells[name_col].text))
                if cleaned:
                    self.persons.add(cleaned)

    def _mine_text(self, text: str):
        anchors = [
            r"(?:Mr|Ms|Mrs|Dr|Shri|Smt)\.?\s+([A-Z][a-zA-Z.]+(?:\s+[A-Z][a-zA-Z.]+){1,3})",
            r"([A-Z][a-zA-Z.]+(?:\s+[A-Z][a-zA-Z.]+){1,3})\s+is\s+our\b",
            r"Contact\s+Person[s]?\s*:?\s*([A-Z][a-zA-Z.]+(?:\s+[A-Z][a-zA-Z.]+){1,3})",
        ]
        anchors.append(r"being\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})")  # "...being <Name>"
        for pat in anchors:
            for m in re.finditer(pat, text):
                cleaned = _clean_person(m.group(1))
                if cleaned:
                    self.persons.add(cleaned)
        # Add first+last aliases for 3-4 token names (documents often use the short
        # form, e.g. "Kushal Subbayya Hegde" also appears as "Kushal Hegde").
        for full in list(self.persons):
            toks = full.split()
            if len(toks) >= 3:
                alias = f"{toks[0]} {toks[-1]}"
                if _clean_person(alias):
                    self.persons.add(alias)


def _alternation(items) -> re.Pattern | None:
    items = sorted({i for i in items if i}, key=len, reverse=True)  # longest first
    if not items:
        return None
    return re.compile(r"(?<!\w)(" + "|".join(re.escape(i) for i in items) + r")(?!\w)")


# --------------------------------------------------------------------- detectors
class NameDetector(Detector):
    category = "NAME"
    name = "kb.name"

    def __init__(self, kb: KnowledgeBase):
        self._re = _alternation(kb.persons)

    def detect(self, text: str) -> list[Span]:
        if not self._re:
            return []
        return [Span(m.start(), m.end(), m.group(0), self.category, self.name, 0.95)
                for m in self._re.finditer(text)]


class CompanyDetector(Detector):
    category = "COMPANY"
    name = "rule.company"

    _SUFFIX = (r"(?:Private\s+Limited|Pvt\.?\s*Ltd\.?|Limited|Ltd\.?|LLP|"
               r"Corporation|Corp\.?|Co\.|Associates)")
    # A capitalised head word, then up to 6 more words which may be capitalised
    # tokens, a parenthesised token like "(India)", OR lowercase connectors
    # (and / of / the / &), ending in a legal/entity suffix. Allowing connectors
    # keeps "CG Power and Industrial Solutions Limited" whole; the parenthesis rule
    # keeps "Transformers & Rectifiers (India) Limited" whole.
    _WORD = r"(?:and|of|the|&|\([A-Za-z]+\)|[A-Z0-9][A-Za-z0-9&.()\-]*)"
    _CAND = re.compile(
        r"([A-Z][A-Za-z0-9&.()\-]*(?:[ \t\n]+" + _WORD + r"){0,6}?[ \t\n]+" + _SUFFIX + r")(?!\w)"
    )
    _SUFFIX_ONLY = re.compile(
        r"^(?:Private\s+Limited|Pvt\.?\s*Ltd\.?|Limited|Ltd\.?|LLP|Corporation|Corp\.?|Co\.|Associates)$",
        re.I)
    _TRUST = re.compile(r"([A-Z][a-z]+\s+Family\s+Trust)")
    # leading label words / codes to strip off the front of a company match
    _LEAD_STOP = {
        "company", "bank", "banks", "issue", "fresh", "offer", "public", "registrar",
        "promoter", "corporate", "the", "and", "of", "designated", "sponsor",
        "escrow", "refund", "syndicate", "members", "lead", "managers", "book",
        "running", "account", "collection", "our", "formerly", "also", "to", "from",
        "shareholders", "shareholder", "investor", "anchor", "capital", "short",
        "long", "term", "positive", "stable", "net", "working", "proposed",
        "family", "trust",
    }
    _CODE = re.compile(r"^(?:[A-Z]{1,4}\d{3,}[A-Z0-9]*|[UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})$")

    def __init__(self, allowlist: list[str]):
        self._allow = {a.lower() for a in allowlist}

    def _allowed(self, value: str) -> bool:
        v = re.sub(r"\s+", " ", value).lower()
        return any(a == v or a in v for a in self._allow)

    def _trim_start(self, text: str, s: int, e: int) -> int:
        """Advance start offset past leading label words / identifier codes."""
        while s < e:
            m = re.match(r"([A-Za-z0-9.\-]+)[ \t\n]+", text[s:e])
            if not m:
                break
            tok = m.group(1)
            if tok.lower().strip(".") in self._LEAD_STOP or self._CODE.match(tok):
                s += m.end()
            else:
                break
        return s

    def detect(self, text: str) -> list[Span]:
        spans, seen = [], set()
        for m in self._CAND.finditer(text):
            s = self._trim_start(text, m.start(1), m.end(1))
            val = text[s:m.end(1)]
            # need a real (non-suffix) word before the legal suffix; drop bare "Private Limited"
            without_suffix = re.sub(self._SUFFIX + r"\s*$", "", val).strip()
            if (not without_suffix or self._SUFFIX_ONLY.match(val.strip())
                    or self._allowed(val) or (s, m.end(1)) in seen):
                continue
            seen.add((s, m.end(1)))
            spans.append(Span(s, m.end(1), val, self.category, self.name, 0.9))
        for m in self._TRUST.finditer(text):
            if (m.start(1), m.end(1)) not in seen:
                seen.add((m.start(1), m.end(1)))
                spans.append(Span(m.start(1), m.end(1), m.group(1), self.category, self.name, 0.9))
        return spans


class AddressDetector(Detector):
    """Anchor-based: an address-like run of text terminated by a 6-digit PIN code."""
    category = "ADDRESS"
    name = "rule.address"
    _re = re.compile(
        r"([A-Z0-9][^\n]{5,160}?(?:Road|Marg|Society|Apartment|Bunglow|Bungalow|Nagar|"
        r"Colony|Gymkhana|Residency|Park|Gat\s*No\.?|S\.?\s*no\.?|Plot\s*No\.?|Plot|"
        r"Village|Taluka|Floor|Tower|MIDC|Industrial|Complex|Chambers|Estate)"
        r"[^\n]{0,160}?\b\d{3}\s?\d{3}\b)"
    )

    # Prose lead-ins that precede an address; trimmed so we redact the address itself.
    _LEAD = re.compile(
        r"^.*?(?:located at|situated at|plant at|facility at|"
        r"Registered Office:|Corporate Office:|Office:)\s*", re.I)
    # A clean leading company name (…Limited/Ltd/LLP) that precedes an address on the
    # same line — trimmed so the COMPANY detector scores it and the address is clean.
    _LEAD_COMPANY = re.compile(
        r"^(?:[A-Z][A-Za-z0-9&.()\-]*\s+)*?(?:[A-Z][A-Za-z0-9&.()\-]*|and|of|&)\s+"
        r"(?:Limited|Ltd\.?|LLP|Corporation|Corp\.?|Co\.|Associates)\s+(?=[A-Z0-9])")
    # Fallback: a city name directly followed by a 6-digit PIN ("Pune – 411 045"),
    # catching address fragments that are split away from their street line.
    _CITY_PIN = re.compile(r"\b([A-Z][a-z]+(?:\s*[–-]\s*|\s+)\d{3}\s?\d{3})\b")

    def detect(self, text: str) -> list[Span]:
        spans = []
        for m in self._re.finditer(text):
            s, e = m.start(1), m.end(1)
            for lead in (self._LEAD, self._LEAD_COMPANY):
                lm = lead.match(text[s:e])
                if lm and lm.end() < (e - s):
                    s += lm.end()
            spans.append(Span(s, e, text[s:e], self.category, self.name, 0.85))
        taken = [(sp.start, sp.end) for sp in spans]
        for m in self._CITY_PIN.finditer(text):
            if not any(m.start(1) < e and s < m.end(1) for s, e in taken):
                spans.append(Span(m.start(1), m.end(1), m.group(1), self.category, self.name, 0.7))
        return spans
