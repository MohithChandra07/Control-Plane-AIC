"""Prompt-injection detection for untrusted input (spec §4, §25: retrieved
documents must never have embedded instructions silently followed).

Scans `role="tool"` / `role="function"` messages -- the standard
OpenAI-style convention for retrieved/function-result content an
application injects into the conversation, as opposed to `role="user"` /
`"system"`, which the calling application's own developer controls -- for
common instruction-override phrasing, and neutralizes any match before the
request reaches the upstream model. Deliberately not scanning "user" or
"system" messages: those are the actual conversation participants, not
untrusted retrieved content, and flagging a user's own words as an
"injection attempt" would be a false-positive-prone overreach outside
this mechanism's scope.

Heuristic, not exhaustive -- this demonstrates the input-side control
mechanism the spec asks for (never automatically follow instructions from
retrieved content), not a claim of complete jailbreak coverage. See
docs/roadmap.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

UNTRUSTED_ROLES = {"tool", "function"}

_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore (all|any|the) (previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard (the )?(above|previous|prior)\s+instructions?", re.IGNORECASE),
    re.compile(r"\byou are now\b", re.IGNORECASE),
    re.compile(r"new instructions?\s*:", re.IGNORECASE),
    re.compile(r"system prompt\s*:", re.IGNORECASE),
    re.compile(r"reveal (the )?(system prompt|your instructions)", re.IGNORECASE),
    re.compile(r"forget (everything|all)\s+(you know|previous)", re.IGNORECASE),
]


@dataclass
class InjectionMatch:
    pattern: str
    text: str
    start: int
    end: int


def detect_injection(text: str) -> list[InjectionMatch]:
    matches: list[InjectionMatch] = []
    claimed: list[tuple[int, int]] = []
    for pattern in _PATTERNS:
        for m in pattern.finditer(text):
            span = (m.start(), m.end())
            if any(span[0] < c_end and span[1] > c_start for c_start, c_end in claimed):
                continue
            matches.append(InjectionMatch(pattern=pattern.pattern, text=m.group(), start=span[0], end=span[1]))
            claimed.append(span)
    return sorted(matches, key=lambda m: m.start)


def neutralize(text: str, matches: list[InjectionMatch]) -> str:
    """Replaces each matched span with a fixed marker -- surgical, like
    detectors/pii/regex_pii.py:redact(), not a wholesale block of the
    message: the rest of a retrieved document's legitimate content
    survives, only the injection attempt itself is removed."""
    if not matches:
        return text
    parts: list[str] = []
    cursor = 0
    for m in sorted(matches, key=lambda m: m.start):
        parts.append(text[cursor : m.start])
        parts.append("[REDACTED_INJECTION_ATTEMPT]")
        cursor = m.end
    parts.append(text[cursor:])
    return "".join(parts)


def is_untrusted_role(role: str | None) -> bool:
    return role in UNTRUSTED_ROLES
