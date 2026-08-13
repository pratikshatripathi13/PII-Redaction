"""Load gold spans from JSONL (offsets + category only; no raw PII stored)."""
from __future__ import annotations

import json
from collections import defaultdict

from ..models import GoldSpan


def load_gold(path: str) -> dict:
    gold = defaultdict(list)
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            d = json.loads(line)
            gold[d["unit_id"]].append(
                GoldSpan(d["unit_id"], int(d["start"]), int(d["end"]), d["category"])
            )
    return dict(gold)
