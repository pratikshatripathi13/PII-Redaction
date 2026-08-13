"""Compute per-category precision / recall / F1 and a caveated token accuracy."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .matcher import match_unit


@dataclass
class CatResult:
    category: str
    tp: int
    fp: int
    fn: int

    @property
    def support(self):
        return self.tp + self.fn

    @property
    def precision(self):
        d = self.tp + self.fp
        return self.tp / d if d else None

    @property
    def recall(self):
        d = self.tp + self.fn
        return self.tp / d if d else None

    @property
    def f1(self):
        p, r = self.precision, self.recall
        if not p or not r:
            return None
        return 2 * p * r / (p + r)


@dataclass
class Report:
    results: list
    match_mode: str
    token_accuracy: float
    scored_categories: list

    def render(self) -> str:
        lines = ["# Evaluation Report", ""]
        lines.append(f"Span-match mode: **{self.match_mode}**")
        lines.append("")
        lines.append("| Category | TP | FP | FN | Precision | Recall | F1 | Support |")
        lines.append("|---|---|---|---|---|---|---|---|")
        tot = [0, 0, 0]
        for r in self.results:
            if r.support == 0 and r.tp + r.fp == 0:
                lines.append(f"| {r.category} | 0 | 0 | 0 | n/a | n/a | n/a | 0 (not present) |")
                continue
            tot[0] += r.tp; tot[1] += r.fp; tot[2] += r.fn
            lines.append(
                f"| {r.category} | {r.tp} | {r.fp} | {r.fn} | "
                f"{_p(r.precision)} | {_p(r.recall)} | {_p(r.f1)} | {r.support} |"
            )
        micro = CatResult("MICRO", *tot)
        lines.append(
            f"| **Overall (micro)** | {tot[0]} | {tot[1]} | {tot[2]} | "
            f"{_p(micro.precision)} | {_p(micro.recall)} | {_p(micro.f1)} | {micro.support} |"
        )
        lines.append("")
        lines.append(f"Token-level accuracy: **{self.token_accuracy:.4f}** "
                     "(reported for completeness only — see caveat below).")
        return "\n".join(lines)


def _p(x):
    return "n/a" if x is None else f"{x:.3f}"


def evaluate(predictions: dict, gold: dict, settings, unit_lengths: dict | None = None,
             scope: set | None = None) -> Report:
    mode = settings.match_mode
    cats = settings.enabled_categories

    # Only score within the annotated scope. Predictions outside the scope are
    # ignored (we have no ground truth there, so they can be neither TP nor FP).
    units = set(scope) if scope else (set(predictions) | set(gold))

    # group spans by (unit, category), restricted to scope
    pred_by = defaultdict(list)
    for uid, spans in predictions.items():
        if uid not in units:
            continue
        for s in spans:
            pred_by[(uid, s.category)].append(s)
    gold_by = defaultdict(list)
    for uid, gspans in gold.items():
        for g in gspans:
            gold_by[(uid, g.category)].append(g)
    results = []
    for cat in cats:
        tp = fp = fn = 0
        for uid in units:
            preds = pred_by.get((uid, cat), [])
            golds = gold_by.get((uid, cat), [])
            t, mp, mg = match_unit(preds, golds, mode)
            tp += t
            fp += len(preds) - len(mp)
            fn += len(golds) - len(mg)
        results.append(CatResult(cat, tp, fp, fn))

    acc_units = {u: unit_lengths[u] for u in units if unit_lengths and u in unit_lengths}
    token_acc = _token_accuracy(predictions, gold, acc_units) if acc_units else 1.0
    scored = [r.category for r in results if r.support > 0]
    return Report(results, mode, token_acc, scored)


def _token_accuracy(predictions, gold, unit_lengths) -> float:
    """Character-level PII/non-PII classification accuracy across scored units."""
    correct = total = 0
    units = set(unit_lengths)
    for uid in units:
        n = unit_lengths[uid]
        if n == 0:
            continue
        pred_mask = bytearray(n)
        gold_mask = bytearray(n)
        for s in predictions.get(uid, []):
            for i in range(s.start, min(s.end, n)):
                pred_mask[i] = 1
        for g in gold.get(uid, []):
            for i in range(g.start, min(g.end, n)):
                gold_mask[i] = 1
        for i in range(n):
            if pred_mask[i] == gold_mask[i]:
                correct += 1
        total += n
    return correct / total if total else 1.0
