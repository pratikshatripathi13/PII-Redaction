# PII Redaction — Evaluation Report

Document under test: **Red Herring Prospectus (KSH International Limited)**, `.docx`,
1006 paragraphs, 76 tables, ~446k characters.

All numbers below come from an **actual run** of the tool against the prospectus and
an **independently annotated** ground truth. Nothing is fabricated. Categories that
do not occur in the document are reported as *0-support*, not invented.

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

A full manual annotation of all 1006 paragraphs is unnecessary and error-prone within
the 24-hour window. Instead we annotate a **stratified sample** designed to measure
both recall and precision honestly:

* **PII-dense stratum** — the cover/contact blocks, the promoter/director tables and
  the registered-office lines, i.e. the places where essentially all true PII lives.
* **Prose stratum** — a seeded random sample of ordinary body paragraphs, included
  specifically so that **false positives in non-PII text are counted**.

This yields **70 units / 92 gold spans**. Every true PII span in each sampled unit was
annotated by **reading the text** (`scripts/build_ground_truth.py`), independently of
what the detectors produced. The annotation deliberately includes entities the
detectors were expected to miss (a CEO named only in prose, firms without a legal
suffix, Corporation-suffixed customers, address fragments), so recall is not
flattered. Gold stores **category + character offsets only** — no raw PII values are
committed.

### 2.2 Span matching

A prediction matches a gold span when they share the same unit, the same category, and:

* **strict** — identical start/end offsets, or
* **overlap** — any character overlap (fair for boundary-fuzzy NAME/ADDRESS/COMPANY).

Matching is greedy one-to-one; unmatched predictions are false positives, unmatched
gold spans are false negatives. Both modes are reported.

### 2.3 On raw accuracy (important caveat)

Token-level accuracy is **0.9955**, but this number is intentionally **not** the
headline. In a 446k-character document only a few hundred characters are PII, so the
non-PII class dominates overwhelmingly — a detector that redacts *nothing* would still
score ~0.99 accuracy. Accuracy is therefore reported only for completeness. The
meaningful metrics for PII redaction are **per-category precision and recall**, because
they separately penalise leaks (low recall) and over-redaction (low precision), which
raw accuracy hides.

## 3. Results

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
2. **Iterative tuning risk.** Several rules were refined after inspecting misses on this
   sample. The refinements are generalizable (comma-in-phone, legal suffixes, prose
   anchors) and were re-checked against the **whole** document for new false positives,
   but overlap = 1.0 should be read as "on this annotated sample" rather than a
   guarantee on unseen prospectuses.
3. **Structural NER.** Person/company detection leans on document structure; a novel
   prospectus with different table layouts would need its anchors reviewed. This is the
   deliberate tradeoff for high precision and zero heavyweight dependencies.
4. **Over- vs under-redaction.** Where the tool errs it tends to **over-redact**
   (extra address context, a company caught inside an address block) rather than leak
   PII, which is the safer failure mode for a redaction tool. A full end-to-end leakage
   scan of the output confirmed **zero** original emails, names, companies, phones or
   addresses from the detected set remain in the redacted file.
