"""Regex-based PII detector.

Spec §11 suggests Presidio (spaCy-backed NER + regex). This prototype uses
plain regexes instead: no model download, no spaCy dependency, and it's
good enough to catch the PII categories the tenant configs actually gate on
(phone, email, credit_card, government_id, bank_account) — see
docs/roadmap.md for this being a documented Phase 2 simplification, not a
claim that it matches Presidio's recall on free-form NER-requiring PII
(names, addresses).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "phone": re.compile(r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?\d{10}(?!\d)"),
    "credit_card": re.compile(r"(?<!\d)(?:\d[ -]?){13,16}(?!\d)"),
    "government_id": re.compile(r"\b\d{3}[-\s]\d{2}[-\s]\d{4}\b"),
    "bank_account": re.compile(r"\b\d{9,18}\b"),
}

# Order matters: more specific patterns are checked first so a single span
# isn't double-counted under a looser category (e.g. a 16-digit card number
# would also match the bank_account digit-run pattern).
_CATEGORY_PRIORITY = ["email", "government_id", "credit_card", "phone", "bank_account"]


@dataclass
class PiiMatch:
    category: str
    start: int
    end: int
    text: str


def detect_pii(text: str) -> list[PiiMatch]:
    matches: list[PiiMatch] = []
    claimed: list[tuple[int, int]] = []

    for category in _CATEGORY_PRIORITY:
        for m in _PATTERNS[category].finditer(text):
            span = (m.start(), m.end())
            if any(span[0] < c_end and span[1] > c_start for c_start, c_end in claimed):
                continue
            matches.append(PiiMatch(category=category, start=span[0], end=span[1], text=m.group()))
            claimed.append(span)

    return sorted(matches, key=lambda m: m.start)


def quick_pii_scan(text: str) -> bool:
    """Cheap existence check used by Tier 0 — stops at the first match."""
    return any(pattern.search(text) for pattern in _PATTERNS.values())


def redact(text: str, matches: list[PiiMatch]) -> str:
    """Replace each matched span with a [REDACTED_<CATEGORY>] token."""
    if not matches:
        return text
    parts: list[str] = []
    cursor = 0
    for m in sorted(matches, key=lambda m: m.start):
        parts.append(text[cursor : m.start])
        parts.append(f"[REDACTED_{m.category.upper()}]")
        cursor = m.end
    parts.append(text[cursor:])
    return "".join(parts)
