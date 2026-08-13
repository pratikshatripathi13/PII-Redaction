"""Run redaction, score predictions against gold, and write the evaluation report.

Reports BOTH strict and overlap span-matching so boundary-fuzzy categories
(NAME/ADDRESS/COMPANY) are judged fairly.
"""
from __future__ import annotations

import json

from pii_redactor.config import load_settings
from pii_redactor.evaluation.ground_truth import load_gold
from pii_redactor.evaluation.metrics import evaluate
from pii_redactor.redactor import redact

INPUT = "Red Herring Prospectus (1).docx"


def main():
    settings = load_settings("config/default.yaml")
    out = redact(INPUT, None, settings)
    gold = load_gold("ground_truth/gold_spans.jsonl")
    scope = set(json.load(open("ground_truth/scope.json")))

    sections = []
    for mode in ("strict", "overlap"):
        settings.match_mode = mode
        rep = evaluate(out.predictions, gold, settings, out.unit_lengths, scope)
        sections.append(rep.render())

    body = "\n\n---\n\n".join(sections)
    print(body)
    return body


if __name__ == "__main__":
    main()
