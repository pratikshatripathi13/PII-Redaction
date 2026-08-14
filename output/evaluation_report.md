# Evaluation Report — PII Redaction Tool

## 1. Document under test

I tested the tool on the supplied Red Herring Prospectus (KSH International Limited). It
is a `.docx` file with 1006 paragraphs and 76 tables, about 446k characters. It contains
email addresses, phone numbers, person names, company names, and postal addresses. SSN,
credit card, IP, and date of birth do not appear in it.

The results below come from running `python scripts/run_evaluation.py` on this document.

## 2. Evaluation method

I built the ground truth by reading a sample of the document and writing down the PII
spans I expected, without looking at the detector output. The sample has 70 text units
and 92 spans. Most of it comes from the parts of the document where PII is concentrated —
contact blocks, promoter and director tables, and the registered office — but I also
included some ordinary paragraphs so that false positives in normal text would show up.
The gold file stores the category and character offsets, not the original text.

A prediction is correct when it matches a gold span of the same category. I report two
matching modes:

- Strict: the predicted and gold spans have the same start and end offsets.
- Overlap: the two spans overlap by at least one character.

I added overlap because name and address boundaries are not always clear-cut, so exact
offsets can be too harsh.

I also computed raw token accuracy (0.9955), but it isn't a useful headline number here.
Almost all of the document is non-PII text, so even a detector that found very little
would still score close to 100%. Precision and recall per category say more about how the
detectors actually perform.

## 3. Results

Sample metrics:

| Matching | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|
| Strict | 0.989 | 0.989 | 0.989 | 91 | 1 | 1 |
| Overlap | 1.000 | 1.000 | 1.000 | 92 | 0 | 0 |

Per category (strict):

| Category | Precision | Recall | Support |
|---|---|---|---|
| EMAIL | 1.000 | 1.000 | 18 |
| PHONE | 1.000 | 1.000 | 16 |
| NAME | 1.000 | 1.000 | 10 |
| COMPANY | 1.000 | 1.000 | 30 |
| ADDRESS | 0.944 | 0.944 | 18 |
| SSN / CREDIT_CARD / DOB / IP | n/a | n/a | 0 |

SSN, credit card, date of birth, and IP have no support because they don't occur in this
document, so there was nothing for those detectors to match.

Running the redactor on the whole prospectus (not just the sample) produced 486
replacements:

| Category | Redactions | Unique values |
|---|---|---|
| EMAIL | 52 | 26 |
| PHONE | 36 | 18 |
| NAME | 160 | 36 |
| COMPANY | 189 | 64 |
| ADDRESS | 49 | 41 |

## 4. Error analysis

The one error under strict matching is an address. The detected span overlaps the
annotated address, but the start and end offsets are not identical, so strict matching
records it as one false positive and one false negative while overlap matching counts it
as correct. The address itself is still redacted.

Email, phone, name, and company match the gold spans exactly on the sample. A few cases
were missed in earlier versions and then fixed: phone numbers followed by a comma in a
list, a name that only appeared in running text, short forms of promoter names, and
companies with less common suffixes.

## 5. Limitations

- The metrics come from the sampled units, not the full document, so numbers on other
  files may differ.
- Address boundaries are the main source of error and can include or drop a few
  characters.
- Name and company detection depends on the document structure, so a name that only
  appears in free text, or a company written without a legal suffix, can be missed.
- The 1.000 overlap score means the detected spans covered the annotated PII in this
  sample. It does not mean the detector is perfect on other documents.
