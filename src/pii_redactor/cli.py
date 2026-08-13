"""Command-line entry point.

  python -m pii_redactor.cli redact   --input <in.docx> --output <out.docx>
  python -m pii_redactor.cli evaluate --input <in.docx> --gold <gold.jsonl>
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .config import load_settings
from .redactor import redact

_DEFAULT_CONFIG = os.path.join(os.path.dirname(__file__), "..", "..", "config", "default.yaml")


def _add_common(p):
    p.add_argument("--input", required=True)
    p.add_argument("--config", default=_DEFAULT_CONFIG)


def main(argv=None):
    parser = argparse.ArgumentParser(description="PII redaction for DOCX")
    sub = parser.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("redact", help="produce a redacted DOCX")
    _add_common(r)
    r.add_argument("--output", required=True)
    r.add_argument("--audit", default=None, help="optional audit_log.jsonl path")

    e = sub.add_parser("evaluate", help="score detections against gold spans")
    _add_common(e)
    e.add_argument("--gold", required=True)
    e.add_argument("--report", default=None)

    args = parser.parse_args(argv)
    settings = load_settings(args.config)

    if args.cmd == "redact":
        out = redact(args.input, args.output, settings)
        if args.audit:
            out.auditor.write_jsonl(args.audit)
        print(json.dumps(out.auditor.summary(), indent=2))
        print(f"Redacted DOCX written to {args.output}")

    elif args.cmd == "evaluate":
        from .evaluation.ground_truth import load_gold
        from .evaluation.metrics import evaluate
        out = redact(args.input, None, settings)
        gold = load_gold(args.gold)
        report = evaluate(out.predictions, gold, settings, out.unit_lengths)
        text = report.render()
        if args.report:
            with open(args.report, "w", encoding="utf-8") as f:
                f.write(text)
        print(text)


if __name__ == "__main__":
    sys.exit(main())
