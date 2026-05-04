from __future__ import annotations

import re
from typing import Iterable

IMO_RE = re.compile(r"\b\d{7}\b")


def extract_imo_digits(text: str) -> str:
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) != 7:
        raise ValueError("IMO must contain exactly 7 digits")
    return digits


def normalize_imo(text: str) -> str:
    digits = extract_imo_digits(text)
    if not is_valid_imo(digits):
        raise ValueError("Invalid IMO checksum")
    return digits


def is_valid_imo(imo: str) -> bool:
    if len(imo) != 7 or not imo.isdigit():
        return False

    base = imo[:6]
    checksum = int(imo[-1])
    weighted_sum = sum(int(base[i]) * (7 - i) for i in range(6))
    return weighted_sum % 10 == checksum


def extract_imos(text: str) -> Iterable[str]:
    for found in IMO_RE.findall(text):
        if is_valid_imo(found):
            yield found
