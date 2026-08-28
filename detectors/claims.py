"""Claim extraction: splits a response into atomic, span-tracked claims.

Heuristic sentence segmentation (regex, not a real sentence tokenizer) —
adequate for a Phase 2 prototype's demo scenarios, not abbreviation-aware
(e.g. "Dr. Smith" would split wrongly). Questions and very short fragments
(greetings, acknowledgements) are skipped: they aren't factual assertions,
so verifying/redacting them would be wasted work and noise in the audit
trail. Spans are preserved so policy/engine.py can reconstruct the response
after surgical remediation without touching untouched text.
"""

from __future__ import annotations

import re
import uuid

from detectors.base import Claim

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_MIN_CLAIM_LENGTH = 15


def extract_claims(text: str) -> list[Claim]:
    claims: list[Claim] = []
    cursor = 0
    for sentence in _SENTENCE_BOUNDARY.split(text):
        start = text.index(sentence, cursor)
        end = start + len(sentence)
        cursor = end

        stripped = sentence.strip()
        if not stripped:
            continue
        if stripped.endswith("?"):
            continue
        if len(stripped) < _MIN_CLAIM_LENGTH:
            continue

        claims.append(Claim(claim_id=str(uuid.uuid4()), text=sentence, start=start, end=end))

    return claims
