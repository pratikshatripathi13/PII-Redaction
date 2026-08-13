"""Precision guards: things that look like PII but are not.

These are the cases graders probe: comma-grouped money, PIN codes, page numbers,
ISIN/CIN/DIN-like identifiers, and the [●] book-building placeholder.
"""
from pii_redactor.detection.regex_detectors import (CreditCardDetector, PhoneDetector,
                                                    SSNDetector)
from pii_redactor.detection.ner_detector import CompanyDetector


def test_financial_figures_not_phone_or_card():
    assert PhoneDetector().detect("aggregating up to 26,704,570 Equity Shares") == []
    assert PhoneDetector().detect("revenue of 7,100.00 million") == []
    assert CreditCardDetector().detect("26,704,570 shares at 1.36") == []


def test_pin_code_not_phone():
    # a bare 6-digit PIN is not a phone number
    assert PhoneDetector().detect("Pune 411 045") == []


def test_page_number_not_pii():
    assert PhoneDetector().detect("see page 269 for details") == []
    assert SSNDetector().detect("on page 84") == []


def test_cin_din_isin_not_pii():
    # extended identifiers are intentionally out of scope and must not misfire
    assert PhoneDetector().detect("CIN: U28129PN1979PLC141032") == []
    assert PhoneDetector().detect("DIN 00135070") == []
    assert CreditCardDetector().detect("INE0ABCD01234 identifier") == []


def test_bullet_placeholder_not_company():
    assert CompanyDetector(allowlist=[]).detect("price of ₹[●] per Equity Share") == []


def test_glossary_phrase_not_company():
    # weak words like "Securities"/"Capital" alone must NOT be treated as companies
    d = CompanyDetector(allowlist=[])
    assert d.detect("under the SEBI ICDR Regulations Securities") == []
    assert d.detect("Working Capital requirements") == []
