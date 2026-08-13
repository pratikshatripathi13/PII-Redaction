"""Collect redaction events keyed by hashed identifiers (never raw PII)."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class Auditor:
    events: list = field(default_factory=list)
    counts: Counter = field(default_factory=Counter)
    unique_ids: dict = field(default_factory=dict)  # category -> set(hashed_id)

    def record(self, unit_id: str, category: str, hashed_id: str, replacement: str):
        self.events.append({
            "unit_id": unit_id,
            "category": category,
            "entity_id": hashed_id,      # HMAC digest, non-reversible
            "replacement": replacement,  # synthetic value, safe to log
        })
        self.counts[category] += 1
        self.unique_ids.setdefault(category, set()).add(hashed_id)

    def write_jsonl(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            for e in self.events:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    def summary(self) -> dict:
        return {
            "total_redactions": sum(self.counts.values()),
            "by_category": dict(self.counts),
            "unique_entities": {k: len(v) for k, v in self.unique_ids.items()},
        }
