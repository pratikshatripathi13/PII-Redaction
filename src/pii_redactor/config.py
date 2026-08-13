"""Load and validate the YAML policy configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Settings:
    categories: dict
    phone_regions: list
    company_allowlist: list
    extended_identifiers: dict
    salt: str
    match_mode: str

    @property
    def enabled_categories(self) -> list:
        return [c for c, on in self.categories.items() if on]


def load_settings(path: str | os.PathLike) -> Settings:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    # Environment override for a secret salt (keeps audit IDs irreversible).
    salt = os.environ.get("PII_SALT", data.get("pseudonymization", {}).get("salt", "salt"))
    return Settings(
        categories=data.get("categories", {}),
        phone_regions=data.get("phone", {}).get("regions", ["IN", "INTL"]),
        company_allowlist=data.get("company", {}).get("allowlist", []),
        extended_identifiers=data.get("extended_identifiers", {}),
        salt=salt,
        match_mode=data.get("evaluation", {}).get("match_mode", "overlap"),
    )
