"""Deterministic entity -> replacement mapping.

Guarantees:
  * Same (category, normalized value) always maps to the same replacement, within
    and across runs (seed derived from an HMAC of the value + config salt).
  * No raw PII is stored anywhere persistent: the audit identifier is the HMAC
    hex digest, never the original string.
"""
from __future__ import annotations

import hmac
import re
from hashlib import sha256

from .generator import Generator


class MappingStore:
    def __init__(self, salt: str):
        self._salt = salt.encode("utf-8")
        self._gen = Generator()
        self._cache: dict[str, str] = {}          # hashed_id -> replacement
        self._id_cache: dict[tuple, str] = {}     # (cat, norm) -> hashed_id

    @staticmethod
    def _normalize(category: str, value: str) -> str:
        v = value.strip()
        if category == "EMAIL":
            return v.lower()
        if category == "PHONE":
            return re.sub(r"\D", "", v)
        if category in ("NAME", "COMPANY", "ADDRESS"):
            return re.sub(r"\s+", " ", v).lower()
        return v

    def hashed_id(self, category: str, value: str) -> str:
        key = (category, self._normalize(category, value))
        if key not in self._id_cache:
            msg = f"{category}:{key[1]}".encode("utf-8")
            self._id_cache[key] = hmac.new(self._salt, msg, sha256).hexdigest()[:16]
        return self._id_cache[key]

    def replacement_for(self, category: str, value: str) -> str:
        hid = self.hashed_id(category, value)
        if hid not in self._cache:
            seed = int(hid, 16)
            self._cache[hid] = self._gen.generate(category, value, seed)
        return self._cache[hid]
