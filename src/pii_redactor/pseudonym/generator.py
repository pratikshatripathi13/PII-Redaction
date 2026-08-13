"""Format-preserving synthetic value generators.

Each generator is seeded deterministically (see MappingStore) so the same entity
always yields the same fake, and the fake keeps the shape of the original
(a +91 phone stays a +91 phone; an email keeps first.last@domain form).
"""
from __future__ import annotations

import re

from faker import Faker


class Generator:
    def __init__(self):
        self.fake = Faker("en_IN")

    def generate(self, category: str, original: str, seed: int) -> str:
        self.fake.seed_instance(seed)
        fn = getattr(self, f"_{category.lower()}", None)
        return fn(original) if fn else "[REDACTED]"

    # -- structured ------------------------------------------------------
    def _email(self, original: str) -> str:
        first = self.fake.first_name().lower()
        last = self.fake.last_name().lower()
        return f"{first}.{last}@example.com"

    def _phone(self, original: str) -> str:
        digits = re.sub(r"\D", "", original)
        n = len(digits)
        if original.strip().startswith("+91") or digits.startswith("91"):
            body = f"{self.fake.random_int(70000, 99999)} {self.fake.random_int(10000, 99999)}"
            return "+91 " + body
        if n == 10:
            new = str(self.fake.random_int(6000000000, 9999999999))
            # preserve original grouping (spaces/hyphens positions)
            return _reshape(original, new)
        new = str(self.fake.random_int(10 ** (n - 1), 10 ** n - 1))
        return _reshape(original, new)

    def _ssn(self, original: str) -> str:
        return f"{self.fake.random_int(100,899):03d}-{self.fake.random_int(10,99):02d}-{self.fake.random_int(1000,9999):04d}"

    def _credit_card(self, original: str) -> str:
        # keep digit count; produce a Luhn-valid number of the same length
        n = len(re.sub(r"\D", "", original))
        return _reshape(original, _luhn_number(n, self.fake))

    def _ip(self, original: str) -> str:
        return ".".join(str(self.fake.random_int(1, 254)) for _ in range(4))

    def _dob(self, original: str) -> str:
        d = self.fake.date_of_birth(minimum_age=25, maximum_age=75)
        return d.strftime("%B %d, %Y")

    # -- entities --------------------------------------------------------
    def _name(self, original: str) -> str:
        parts = original.split()
        names = [self.fake.first_name()] + [self.fake.last_name() for _ in parts[1:]]
        return " ".join(names[: len(parts)])

    def _company(self, original: str) -> str:
        if original.strip().lower().endswith("family trust"):
            return f"{self.fake.last_name()} Family Trust"
        suffix_m = re.search(
            r"(Limited|Ltd\.?|LLP|Securities|Capital|Advisors|Bank|Ventures|"
            r"Partners|Technologies|Industries|Financial Services)$", original)
        base = self.fake.company().split(" ")[0]
        suffix = suffix_m.group(1) if suffix_m else "Limited"
        return f"{base} {suffix}"

    def _address(self, original: str) -> str:
        line = self.fake.street_address().replace("\n", ", ")
        pin = self.fake.random_int(100000, 999999)
        return f"{line} – {pin}"


def _reshape(template: str, digits: str) -> str:
    """Place `digits` into the non-digit skeleton of `template`."""
    out, di = [], 0
    for ch in template:
        if ch.isdigit():
            if di < len(digits):
                out.append(digits[di]); di += 1
        else:
            out.append(ch)
    out.append(digits[di:])
    return "".join(out)


def _luhn_number(length: int, fake) -> str:
    body = [str(fake.random_int(0, 9)) for _ in range(length - 1)]
    # choose last digit to satisfy Luhn
    for check in range(10):
        cand = "".join(body) + str(check)
        total, alt = 0, False
        for d in reversed(cand):
            x = int(d)
            if alt:
                x *= 2
                if x > 9:
                    x -= 9
            total += x; alt = not alt
        if total % 10 == 0:
            return cand
    return "".join(body) + "0"
