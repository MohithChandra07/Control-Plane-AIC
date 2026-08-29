"""Toxicity and harmful language detector.

Scans claims and responses for profanity, toxic phrasing, personal attacks,
and harassment markers, producing an evaluated RiskFinding for toxicity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from detectors.base import RiskFinding

# Curated high-precision toxicity & profanity indicator patterns
_TOXIC_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    ("profanity", re.compile(r"\b(?:fuck|shit|bitch|bastard|asshole|cunt|dick|pussy)\b", re.IGNORECASE), 0.85),
    ("hate_slur", re.compile(r"\b(?:nigger|faggot|retard|chink|kike|spic|whore|slut)\b", re.IGNORECASE), 0.95),
    ("harassment", re.compile(r"\b(?:kill\s+yourself|go\s+die|you\s+are\s+worthless|shut\s+the\s+fuck\s+up|i\s+hate\s+you)\b", re.IGNORECASE), 0.90),
    ("threat", re.compile(r"\b(?:i\s+will\s+(?:kill|stab|shoot|track|hurt)\s+you)\b", re.IGNORECASE), 0.95),
    ("insult", re.compile(r"\b(?:you\s+are\s+(?:stupid|idiot|dumb|moron|useless|piece\s+of\s+trash))\b", re.IGNORECASE), 0.75),
]


@dataclass
class ToxicityMatch:
    category: str
    score: float
    start: int
    end: int
    matched_text: str


class ToxicityDetector:
    def scan(self, text: str) -> tuple[RiskFinding, list[ToxicityMatch]]:
        """Scans input text for toxicity indicators."""
        matches: list[ToxicityMatch] = []
        max_score = 0.0

        for category, pattern, weight in _TOXIC_PATTERNS:
            for m in pattern.finditer(text):
                score = weight
                matches.append(
                    ToxicityMatch(
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
