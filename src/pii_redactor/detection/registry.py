"""Build the set of enabled detectors from config + document knowledge base."""
from __future__ import annotations

from ..config import Settings
from .ner_detector import (AddressDetector, CompanyDetector, KnowledgeBase,
                           NameDetector)
from .regex_detectors import (CreditCardDetector, DOBDetector, EmailDetector,
                              IPDetector, PhoneDetector, SSNDetector)

_REGEX = {
    "EMAIL": EmailDetector,
    "PHONE": PhoneDetector,
    "SSN": SSNDetector,
    "CREDIT_CARD": CreditCardDetector,
    "IP": IPDetector,
    "DOB": DOBDetector,
}


def build_detectors(settings: Settings, doc, full_text: str) -> list:
    detectors = []
    for cat, cls in _REGEX.items():
        if settings.categories.get(cat):
            detectors.append(cls())

    kb = KnowledgeBase.build(doc, full_text)
    if settings.categories.get("NAME"):
        detectors.append(NameDetector(kb))
    if settings.categories.get("COMPANY"):
        detectors.append(CompanyDetector(settings.company_allowlist))
    if settings.categories.get("ADDRESS"):
        detectors.append(AddressDetector())

    # Optional secondary spaCy NER (off by default; no-op if the model isn't installed).
    if getattr(settings, "use_spacy_ner", False):
        from .spacy_detector import build_spacy_detector
        ner_cats = [c for c in ("NAME", "COMPANY", "ADDRESS") if settings.categories.get(c)]
        spacy_det = build_spacy_detector(ner_cats, settings.spacy_model)
        if spacy_det is not None:
            detectors.append(spacy_det)
    return detectors, kb
