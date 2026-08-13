"""Per-category detector unit tests. Each detector is tested on plain strings,
independently of python-docx or any other detector."""
from pii_redactor.detection.regex_detectors import (CreditCardDetector, DOBDetector,
                                                    EmailDetector, IPDetector,
                                                    PhoneDetector, SSNDetector)
from pii_redactor.detection.ner_detector import (AddressDetector, CompanyDetector,
                                                 KnowledgeBase, NameDetector)


def _texts(spans):
    return [s.text for s in spans]


# ---- EMAIL ----
def test_email_basic():
    d = EmailDetector()
    assert _texts(d.detect("write to cs.connect@kshinternational.com please")) == \
        ["cs.connect@kshinternational.com"]


def test_email_multiple_and_subdomain():
    d = EmailDetector()
    got = _texts(d.detect("a@x.com and b.c@in.mpms.mufg.com"))
    assert got == ["a@x.com", "b.c@in.mpms.mufg.com"]


# ---- PHONE ----
def test_phone_indian_formats():
    d = PhoneDetector()
    assert _texts(d.detect("Tel: +91 22 40094400")) == ["+91 22 40094400"]
    assert _texts(d.detect("Mobile +91 81081 14949")) == ["+91 81081 14949"]
    assert _texts(d.detect("call 022-68052182 today")) == ["022-68052182"]


def test_phone_in_comma_list():
    # regression: numbers followed by a comma must still be caught
    d = PhoneDetector()
    got = _texts(d.detect("+91 22 30752929, +91 22 30752928 and +91 22 30752914"))
    assert len(got) == 3


# ---- SSN / CREDIT CARD / IP ----
def test_ssn():
    assert _texts(SSNDetector().detect("SSN 123-45-6789.")) == ["123-45-6789"]


def test_credit_card_luhn():
    d = CreditCardDetector()
    assert _texts(d.detect("card 4539578763621486")) == ["4539578763621486"]  # valid Luhn
    assert d.detect("num 4539578763621487") == []                            # invalid Luhn


def test_ip_range():
    d = IPDetector()
    assert _texts(d.detect("host 192.168.1.1")) == ["192.168.1.1"]
    assert d.detect("version 999.1.1.1") == []


# ---- DOB (context-gated) ----
def test_dob_requires_context():
    d = DOBDetector()
    assert _texts(d.detect("Date of birth: January 05, 1980")) == ["January 05, 1980"]
    # a plain corporate date is NOT a DOB
    assert d.detect("incorporated on July 30, 1979") == []


# ---- NAME / COMPANY / ADDRESS ----
def test_company_suffixes_and_connectors():
    d = CompanyDetector(allowlist=[])
    assert "Nuvama Wealth Management Limited" in _texts(
        d.detect("appointed Nuvama Wealth Management Limited as lead"))
    # connector kept whole; two suffixed firms not merged
    got = _texts(d.detect("HDFC Bank Limited and ICICI Bank Limited"))
    assert "HDFC Bank Limited" in got and "ICICI Bank Limited" in got


def test_company_allowlist():
    d = CompanyDetector(allowlist=["BSE Limited"])
    assert d.detect("listed on BSE Limited") == []


def test_name_gazetteer_and_alias():
    kb = KnowledgeBase()
    kb.persons = {"Kushal Subbayya Hegde", "Kushal Hegde"}
    d = NameDetector(kb)
    assert _texts(d.detect("shares of Kushal Subbayya Hegde")) == ["Kushal Subbayya Hegde"]
    assert _texts(d.detect("transfer to Kushal Hegde")) == ["Kushal Hegde"]


def test_address_pin_anchor():
    d = AddressDetector()
    got = _texts(d.detect("A29, Abhimanshree Society, Pashan Road, Pune – 411 008, India"))
    assert got and "Pashan Road" in got[0] and "411 008" in got[0]
