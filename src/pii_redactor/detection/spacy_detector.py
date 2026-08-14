"""Optional secondary NER detector backed by spaCy.

This is OFF by default. The rule-based detectors remain the primary system and all
reported metrics use them. When enabled (config `ner.use_spacy: true`), spaCy runs
alongside the rules and its entities are merged in by the resolver, mainly to catch
names that appear only in free prose with no structural cue.

Enable locally with:
    pip install spacy
    python -m spacy download en_core_web_sm

If spaCy or the model is not installed, `build_spacy_detector` returns None and the
pipeline simply runs without it (graceful no-op) — nothing else changes.
"""
from __future__ import annotations

from ..models import Span
from .base import Detector

try:
    import spacy
except ImportError:  # spaCy not installed
    spacy = None

# spaCy entity label -> our PII category
_LABEL_MAP = {"PERSON": "NAME", "ORG": "COMPANY", "GPE": "ADDRESS",
              "LOC": "ADDRESS", "FAC": "ADDRESS"}


class SpacyNerDetector(Detector):
    category = "NER"
    name = "spacy.ner"

    def __init__(self, nlp, categories):
        self._nlp = nlp
        self._categories = set(categories)

    def detect(self, text: str) -> list[Span]:
        spans = []
        for ent in self._nlp(text).ents:
            cat = _LABEL_MAP.get(ent.label_)
            if cat and cat in self._categories:
                spans.append(Span(ent.start_char, ent.end_char, ent.text, cat,
                                  self.name, 0.6))
        return spans


def build_spacy_detector(categories, model="en_core_web_sm"):
    """Return a SpacyNerDetector, or None if spaCy/the model is unavailable."""
    if spacy is None:
        return None
    try:
        nlp = spacy.load(model, disable=["lemmatizer", "tagger", "parser"])
    except Exception:
        return None
    return SpacyNerDetector(nlp, categories)
