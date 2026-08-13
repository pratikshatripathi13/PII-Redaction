"""Span matching between predictions and gold, per category, within a unit."""
from __future__ import annotations


def _overlap(a_start, a_end, b_start, b_end) -> int:
    return max(0, min(a_end, b_end) - max(a_start, b_start))


def match_unit(preds, golds, mode: str):
    """Greedy one-to-one matching within a single unit for a single category.

    Returns (tp, matched_pred_idx, matched_gold_idx).
    mode: "strict" (exact offsets) or "overlap" (any character overlap).
    """
    matched_p, matched_g = set(), set()
    tp = 0
    for gi, g in enumerate(golds):
        best = None
        for pi, p in enumerate(preds):
            if pi in matched_p:
                continue
            if mode == "strict":
                ok = (p.start == g.start and p.end == g.end)
                score = 1 if ok else 0
            else:
                score = _overlap(p.start, p.end, g.start, g.end)
            if score > 0 and (best is None or score > best[0]):
                best = (score, pi)
        if best is not None:
            tp += 1
            matched_p.add(best[1])
            matched_g.add(gi)
    return tp, matched_p, matched_g
