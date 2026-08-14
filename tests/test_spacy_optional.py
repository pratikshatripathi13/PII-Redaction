"""The optional spaCy detector must (a) never break when spaCy is absent, and
(b) map entity labels correctly when it is available."""
import pytest

from pii_redactor.detection.spacy_detector import build_spacy_detector


def test_build_returns_none_when_unavailable_is_safe():
    # Whether or not spaCy is installed, this must not raise. It returns either a
    # detector or None; the pipeline treats None as "skip".
    det = build_spacy_detector(["NAME", "COMPANY", "ADDRESS"])
    assert det is None or hasattr(det, "detect")


def test_spacy_detection_when_available():
    det = build_spacy_detector(["NAME"])
    if det is None:
        pytest.skip("spaCy / en_core_web_sm not installed")
    spans = det.detect("Barack Obama visited Paris.")
    assert any(s.category == "NAME" for s in spans)
