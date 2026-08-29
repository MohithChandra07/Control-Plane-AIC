"""Demographic and stereotyping bias detector.

Scans claims and responses for explicit demographic stereotyping, gender bias,
racial bias, and discriminatory tropes, producing an evaluated RiskFinding for bias.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from detectors.base import RiskFinding

# High-precision demographic bias and discriminatory trope patterns
_BIAS_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    ("gender_bias", re.compile(r"\b(?:women\s+(?:can\'?t|are\s+too\s+emotional|belong\s+in|are\s+bad\s+at)\b|men\s+never\s+(?:cry|listen))\b", re.IGNORECASE), 0.85),
    ("racial_bias", re.compile(r"\b(?:all\s+(?:black|white|asian|hispanic|latino|immigrant)s?\s+are\b|(?:people\s+of\s+color|minorities)\s+always\s+(?:commit|cause|fail))\b", re.IGNORECASE), 0.90),
    ("age_bias", re.compile(r"\b(?:old\s+people\s+(?:are\s+useless|can\'?t\s+learn|should\s+retire)|younger\s+workers\s+are\s+lazy)\b", re.IGNORECASE), 0.75),
    ("religious_bias", re.compile(r"\b(?:all\s+(?:muslims|christians|jews|hindus|atheists)\s+are\s+(?:dangerous|terrorists|fanatics))\b", re.IGNORECASE), 0.95),
]


@dataclass
class BiasMatch:
    category: str
    score: float
    start: int
    end: int
    matched_text: str


class BiasDetector:
    def scan(self, text: str) -> tuple[RiskFinding, list[BiasMatch]]:
        """Scans input text for demographic bias indicators."""
        matches: list[BiasMatch] = []
        max_score = 0.0

        for category, pattern, weight in _BIAS_PATTERNS:
            for m in pattern.finditer(text):
                score = weight
                matches.append(
                    BiasMatch(
                        category=category,
                        score=score,
                        start=m.start(),
                        end=m.end(),
                        matched_text=m.group(),
                    )
                )
                max_score = max(max_score, score)

        detected = len(matches) > 0
        finding = RiskFinding(
            detected=detected,
            score=round(max_score, 2),
            evaluated=True,
        )
        return finding, matches
