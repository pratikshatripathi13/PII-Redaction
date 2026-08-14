# PII Redaction Tool

Reads a `.docx` file, finds PII, and writes a redacted copy where each value gets swapped
for a realistic fake - so `Rashi Patil` becomes `John Doe` and `+91 9876543210` becomes
`+91 1234567645`. I built and tested this against the Red Herring Prospectus (KSH
International Limited) that was provided with the assignment.

## Problem

The prospectus is a real DOCX - 1006 paragraphs, 76 tables. It's full of contact details,
promoter and director info, addresses. The task was to detect and replace the required PII
categories, keep the formatting intact, and actually report precision/recall from a real
evaluation run instead of just guessing numbers that sound reasonable.

## Approach

I split this into two problems because they're genuinely different. Emails, phone numbers,
SSNs, credit cards, IPs, dates - these have predictable shapes, so regex and a bit of
validation logic gets you most of the way there. Names, companies, addresses are messier.
No fixed shape, so you need context to catch them reliably.

Here's the thing that made this document easier than it first looked: a prospectus lists
its people and companies in predictable spots. There's a board/DIN table, promoter and
shareholder tables, sentences like "Contact Person: …" or "X is our …". So instead of
reaching for a big NER model, I collect names from those structured spots first, then scan
the rest of the document for everywhere those same names show up again.

## Why not spaCy en_core_web_lg

I did look at this. Decided against it, for a few reasons. Most of the names/companies/
addresses in this doc show up in tables and fixed phrasings anyway, which my rules handle
more precisely than a general model would. spaCy's English model also isn't great with
Indian names or Indian company/address formats - it kept wanting to tag words like "Board"
or "Equity" as entities when I tried it on a few sample paragraphs. And it's a ~400MB
dependency for something my rule-based approach already handles well here. If a future
document needed it, the detector interface is generic enough that a spaCy-based detector
could slot in later - just wasn't worth it for this one.

## Detection methods

Email, phone, SSN, credit card, IP - regex with validation. Credit cards get checked
against the Luhn algorithm, IP octets get range-checked (0–255), and phone candidates get
filtered by digit count so PIN codes and comma-separated financial figures don't
accidentally match.

Date of birth - only counts as a DOB if a birth-related word ("date of birth," "born,"
"aged") shows up right before it. This mattered a lot, actually without that check, all
318 ordinary dates in the document (incorporation dates, financial-year ends, etc.) would've
come back as false positives.

Names - pulled from the structured sections mentioned above, plus I handle first+last short
forms, since the document refers to the same person as "Kushal Subbayya Hegde" in one place
and just "Kushal Hegde" somewhere else.

Companies - matched on legal suffixes (Limited, Ltd, LLP, Corporation, Corp, Co.,
Associates), with some connector handling so something like "CG Power and Industrial
Solutions Limited" doesn't get chopped into pieces.

Addresses - looks for an address keyword (Road, Marg, Society, Plot, etc.) followed by a
6-digit PIN code. There's also a city+PIN fallback for address lines that get split weirdly
across paragraphs.

## Deterministic replacement

I wanted the same person/email/phone to map to the same fake value everywhere it shows up in
the doc, not a different fake name every time. So: each value gets normalized (lowercased
email, digits-only phone, whitespace collapsed for names), run through HMAC-SHA256 with a
salt, and that hash seeds Faker. Since the seed comes from the value itself, the same PII
always produces the same replacement — and re-running the tool gives identical output.
Replacements also keep the original shape: a +91 number stays a +91 number, and a fake card
number still passes Luhn.

The audit log stores the HMAC digest instead of the real value, so I can still link repeated
mentions of the same entity without the log itself containing actual PII.

## DOCX handling

I do replacements at the run level instead of rewriting whole paragraphs, so formatting -
bold, headings, table cells - survives. Text that isn't touched stays in its original run;
each replacement gets written into the run where the PII actually started.

Ran into some genuinely annoying DOCX quirks while testing this. Merged table cells were
causing some paragraphs to get processed twice. Empty runs were causing a replacement to get
written more than once. Emails split across multiple runs were getting mangled mid-string.
Took a while to track these down - fixed it by de-duplicating paragraphs by their XML path
and making sure each replacement only gets written once. After that, the output matches the
original on paragraph count (1006), table count (76), and bold-run count (527), so I know the
structure held up.

## Policy decisions

Company names get redacted when they identify a real entity. There's a small allowlist in
`config/default.yaml` for structural references - SEBI, BSE, NSE, RBI, RoC - since those are
regulators/exchanges, not parties whose privacy is at stake. Banks, the registrar, auditors,
legal counsel all get redacted. I didn't leave a company unredacted just because it's
well-known or big; the allowlist is explicit and configurable, not a shortcut.

Indian identifiers — DIN, CIN, PIN, PAN - aren't counted in the main PII metrics since they
weren't in the assignment's required categories. Would be easy to add (one regex detector,
one category), and the detector logic is there, just switched off by default in the config.

## Categories present vs. absent

The prospectus actually contains EMAIL, PHONE, NAME, COMPANY, and ADDRESS. SSN, CREDIT_CARD,
IP, and DOB don't show up at all - makes sense, it's an Indian financial filing, not a
US-style ticket log. The detectors for those four still run and have their own unit tests;
in the evaluation they just show up as 0-support instead of me making up numbers to fill the
gap.

## Evaluation

I built the ground truth by manually reading through a sample of the document and writing
down every PII span I could find - before looking at what the detector output. Sample size:
70 text units, 92 spans, weighted toward the PII-dense sections (contact blocks,
promoter/director tables, registered office) but also including a random spread of ordinary
paragraphs so false positives in normal text would actually get caught if they existed. Full
numbers by category are in `output/evaluation_report.md`.

A prediction counts as correct when it matches a gold span in the same category. I report two
matching modes - strict (exact character offsets) and overlap (any overlap counts) - because
honestly, name and address boundaries are a bit subjective, and I didn't want to hide that
behind one number.

I also computed raw accuracy but didn't lean on it, since most of the document is non-PII
text - a detector that flagged almost nothing would still score high on accuracy. Precision
and recall per category tell you a lot more.

## Results

On the evaluated sample, strict exact-offset matching:

- Precision: 0.989
- Recall: 0.989
- F1: 0.989 (TP 91, FP 1, FN 1)

With overlap matching: 1.000 / 1.000 / 1.000 (TP 92). The gap between the two is a single
address where my detector's boundary didn't line up exactly with my own annotation — the
address still gets redacted either way, just the character offsets differ slightly.

By category (strict matching): EMAIL, PHONE, NAME, and COMPANY all hit 1.000 precision and
recall. ADDRESS comes in at 0.944 / 0.944 — same boundary issue as above.

Across the whole document, the tool made 486 replacements total: 52 emails, 36 phones, 160
names, 189 companies, 49 addresses.

I also ran a leakage check afterward — none of the original PII from the detected set remained
anywhere in the redacted output.

## Limitations

Address boundaries are the fuzziest part of this — the redacted span sometimes grabs a couple
of extra surrounding words. Better to over-redact than leak, so I'm okay with that trade-off,
but it's worth being upfront about.

A company referred to only by a short name with no legal suffix - "Nuvama" on its own, for
instance - can slip through.

Name detection leans partly on document structure, so someone who only appears once in
free-form prose with no surrounding cue could get missed.

The evaluation only covers a sample, not all 1006 paragraphs - and I'll be honest, I tweaked
some of the detection rules after seeing what the sample caught and missed. So these numbers
are close to a best case for this document specifically, not a promise about how it'd perform
on something else.

## How to run

```bash
python -m venv venv && source venv/bin/activate   # Windows PowerShell: venv\Scripts\Activate.ps1
pip install -r requirements.txt
export PYTHONPATH=src                              # Windows PowerShell: $env:PYTHONPATH="src"

# Redact -> writes redacted DOCX + hashed audit log
python -m pii_redactor.cli redact \
    --input "Red Herring Prospectus (1).docx" \
    --output output/redacted.docx \
    --audit  output/audit_log.jsonl

# Rebuild ground truth + evaluate (prints strict & overlap metrics)
python scripts/build_ground_truth.py
python scripts/run_evaluation.py

# Web app — upload a DOCX, pick categories, download the result
streamlit run app.py

# Tests
python -m pytest tests/ -q
```

## Extending to a new PII type

Add a `Detector` subclass with a category and a `detect(text) -> [Span]` method, register it
in `detection/registry.py`, add a matching generator in `pseudonym/generator.py`, and
optionally set its priority in `detection/resolver.py`. Each detector's got its own unit
tests, so adding a new type stays a small, contained change rather than something that
touches everything.

## Project structure

```
src/pii_redactor/
  document/   loader (unit + run-offset model), rewriter (run-level replace)
  detection/  base, regex_detectors, ner_detector (KB + rules), resolver, registry
  pseudonym/  generator (Faker), mapping_store (HMAC-seeded, deterministic)
  audit/      auditor (hashed IDs), reporter
  evaluation/ ground_truth, matcher (strict/overlap), metrics
config/default.yaml   policy (categories, company allowlist, match mode, salt)
ground_truth/         gold_spans.jsonl (offsets only) + scope.json
scripts/              build_ground_truth.py, run_evaluation.py
tests/                per-detector, false-positive, determinism, rewrite, matcher
app.py                streamlit web app (upload / redact / download)
DEPLOYMENT.md         how to run and deploy the web app
```
