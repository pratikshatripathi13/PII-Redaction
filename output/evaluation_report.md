# PII Redaction — Evaluation Report

Document under test: **Red Herring Prospectus (KSH International Limited)**, `.docx`,
1006 paragraphs, 76 tables, ~446k characters.

All numbers below come from an actual run of the tool against the prospectus, scored
against a manually annotated ground truth. Categories that do not occur in the document
are reported as *0-support* rather than given made-up numbers.

## 1. What was redacted (full document)

| Category | Occurrences redacted | Unique entities |
|---|---|---|
| EMAIL | 52 | 26 |
| PHONE | 36 | 18 |
| NAME | 160 | 36 |
| COMPANY | 189 | 64 |
| ADDRESS | 49 | 41 |
| **Total** | **486** | — |

SSN, CREDIT_CARD, IP and DOB do not occur in this document (0 redactions) — it is an
Indian financial prospectus, not a US ticket log. Their detectors still ship and are
unit-tested.

## 2. Evaluation methodology

### 2.1 Ground-truth creation

Annotating all 1006 paragraphs by hand would take too long and be error-prone in the
24-hour window, so I annotated a sample chosen to test both recall and precision:

* **PII-dense units** — the cover/contact blocks, the promoter/director tables and the
  registered-office lines, where almost all of the real PII lives.
* **Prose units** — a seeded random sample of ordinary body paragraphs, included so
  that false positives in non-PII text are actually counted.

This gives **70 units / 92 gold spans**. I created the annotations by reading each
sampled unit's text and recording the PII spans I expected (`scripts/build_ground_truth.py`),
without looking at the detector output. I deliberately included entities I expected the
detectors to miss (a CEO named only in prose, firms without a legal suffix,
Corporation-suffixed customers, address fragments), so recall isn't flattered. The gold
file stores category + character offsets only — no raw PII values are committed to it.

### 2.2 Span matching

A prediction matches a gold span when they share the same unit, the same category, and:

* **strict** — identical start/end offsets, or
* **overlap** — any character overlap (fair for boundary-fuzzy NAME/ADDRESS/COMPANY).

Matching is greedy one-to-one; unmatched predictions are false positives, unmatched
gold spans are false negatives. Both modes are reported.

### 2.3 On raw accuracy (important caveat)

Token-level accuracy is **0.9955**, but I don't treat it as the main metric. In a
446k-character document only a few hundred characters are PII, so the non-PII text
dominates — a detector that redacts almost nothing would still score around 0.99
accuracy. I report it for completeness, but precision and recall per category are the
useful numbers, because they separately show leaks (low recall) and over-redaction
(low precision), which accuracy hides.

## 3. Results

The main result is the stricter exact-offset matching: **precision 0.989, recall 0.989,
F1 0.989** on the sample. With overlap matching the numbers rise to 1.000 / 1.000 /
1.000, because the one remaining strict mismatch is a boundary difference in an address
(the address is redacted; the offsets just differ by a few characters).

### Strict (exact-offset) matching

| Category | TP | FP | FN | Precision | Recall | F1 | Support |
|---|---|---|---|---|---|---|---|
| EMAIL | 18 | 0 | 0 | 1.000 | 1.000 | 1.000 | 18 |
| PHONE | 16 | 0 | 0 | 1.000 | 1.000 | 1.000 | 16 |
| NAME | 10 | 0 | 0 | 1.000 | 1.000 | 1.000 | 10 |
| COMPANY | 30 | 0 | 0 | 1.000 | 1.000 | 1.000 | 30 |
| ADDRESS | 17 | 1 | 1 | 0.944 | 0.944 | 0.944 | 18 |
| SSN / CREDIT_CARD / DOB / IP | 0 | 0 | 0 | n/a | n/a | n/a | 0 (not present) |
| **Overall (micro)** | **91** | **1** | **1** | **0.989** | **0.989** | **0.989** | **92** |

### Overlap matching

| Category | TP | FP | FN | Precision | Recall | F1 | Support |
|---|---|---|---|---|---|---|---|
| EMAIL | 18 | 0 | 0 | 1.000 | 1.000 | 1.000 | 18 |
| PHONE | 16 | 0 | 0 | 1.000 | 1.000 | 1.000 | 16 |
| NAME | 10 | 0 | 0 | 1.000 | 1.000 | 1.000 | 10 |
| COMPANY | 30 | 0 | 0 | 1.000 | 1.000 | 1.000 | 30 |
| ADDRESS | 18 | 0 | 0 | 1.000 | 1.000 | 1.000 | 18 |
| SSN / CREDIT_CARD / DOB / IP | 0 | 0 | 0 | n/a | n/a | n/a | 0 (not present) |
| **Overall (micro)** | **92** | **0** | **0** | **1.000** | **1.000** | **1.000** | **92** |

## 4. Error analysis

* **EMAIL / PHONE** — perfect on the sample. Phone required a fix so that numbers in a
  comma-separated list (`+91 22 30752929, +91 22 30752928`) are all caught.
* **NAME** — perfect on the sample after adding a `being <name>` anchor (CEO named only
  in prose) and first+last aliases (`Kushal Subbayya Hegde` also appears as
  `Kushal Hegde`).
* **COMPANY** — perfect on the sample after adding `Corporation/Corp/Co./Associates`
  suffixes and parenthesis handling (`Transformers & Rectifiers (India) Limited`).
  The single hardest residual case type is a firm referred to only by an abbreviation
  with no legal suffix (e.g. "Nuvama" standing alone), which can be missed.
* **ADDRESS** — the only category below 1.0 under strict matching. The one strict FP/FN
  pair is a **boundary** difference (the detector redacts a slightly larger block than
  the annotated span); overlap matching confirms the address itself is fully covered.
  Addresses split across paragraphs (a bare `Pune – 411 0xx` line) are handled by a
  city+PIN fallback but remain the fuzziest category.

## 5. Limitations

1. **Sampled evaluation.** Metrics are computed on a 70-unit stratified sample, not all
   1006 paragraphs. The sample is weighted toward PII-dense regions, so it is a strong
   test of recall on real PII while still checking prose for false positives — but it
   is a sample, and the true document-wide figures could differ slightly.
2. **Iterative tuning.** I refined several rules after seeing misses on this sample. The
   fixes are fairly general (comma-in-phone, extra legal suffixes, prose name anchors)
   and I re-checked them against the whole document for new false positives, but the
   sample results are best read as "on this annotated sample" rather than a guarantee on
   a different prospectus.
3. **Structural name/company detection.** Person and company detection leans partly on
   document structure, so a prospectus with different table layouts or phrasing would
   need its anchors reviewed. This is the tradeoff I accepted for higher precision and
   for avoiding a heavy NER dependency.
4. **Over- vs under-redaction.** Where the tool errs it tends to over-redact (extra
   address context, or a company caught inside an address block) rather than leak PII,
   which is the safer failure mode for a redaction tool. In the leakage check, none of
   the original emails, names, companies, phones or addresses from the detected set
   remained in the redacted output. This covers the values the detectors found; it does
   not prove that every possible PII value in any future document would be caught.
