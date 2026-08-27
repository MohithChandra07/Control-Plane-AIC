"""Heuristic claim verifier: grounds a claim against the local corpus and
returns SUPPORTED / CONTRADICTED / UNVERIFIABLE.

This is a deterministic keyword+number-overlap heuristic, not a real NLI
cross-encoder (spec §11 suggests one; not used here — see
docs/roadmap.md). Method:

1. Find the corpus passage with the highest word-overlap with the claim.
   Below a relevance floor, there's no real evidence either way ->
   UNVERIFIABLE (never CONTRADICTED merely for lack of evidence — that
   would violate "UNVERIFIABLE != FALSE").
2. If the claim asserts numbers not present in the best-matching passage,
   that's a direct conflict -> CONTRADICTED.
3. Otherwise, if the overlap is strong -> SUPPORTED; if only partial ->
   UNVERIFIABLE (topically related but not confidently grounded).
"""

from __future__ import annotations

import re

from detectors.base import Provenance, ProvenanceSource, Verdict
from detectors.hallucination.corpus import Passage

_WORD = re.compile(r"[a-zA-Z]{4,}")
_NUMBER = re.compile(r"\d+")
_STOPWORDS = {
    "this",
    "that",
    "with",
    "your",
    "have",
    "been",
    "will",
    "from",
    "into",
    "within",
    "available",
    "please",
}

_RELEVANCE_FLOOR = 0.34
_SUPPORTED_FLOOR = 0.6


def _keywords(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(text)} - _STOPWORDS


def _numbers(text: str) -> set[str]:
    return set(_NUMBER.findall(text))


class ClaimVerifier:
    def __init__(self, corpus: list[Passage]):
        self._corpus = corpus
        self._passage_keywords = [(p, _keywords(p.text)) for p in corpus]

    def verify(self, claim_text: str) -> tuple[Verdict, float, Provenance]:
        claim_words = _keywords(claim_text)

        best_passage: Passage | None = None
        best_overlap = 0.0
        if claim_words:
            for passage, words in self._passage_keywords:
                if not words:
                    continue
                overlap = len(claim_words & words) / len(claim_words)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_passage = passage

        if best_passage is None or best_overlap < _RELEVANCE_FLOOR:
            return (
                Verdict.UNVERIFIABLE,
                0.5,
                Provenance(source=ProvenanceSource.MODEL_PRIOR, verdict=Verdict.UNVERIFIABLE),
            )

        claim_numbers = _numbers(claim_text)
        passage_numbers = _numbers(best_passage.text)
        provenance_kwargs = {"source": ProvenanceSource.RETRIEVED_DOC, "source_id": best_passage.doc_id}

        if claim_numbers and not claim_numbers.issubset(passage_numbers):
            verdict = Verdict.CONTRADICTED
            score = 0.9
        elif claim_numbers and claim_numbers.issubset(passage_numbers):
            verdict = Verdict.SUPPORTED
            score = 0.9
        elif best_overlap >= _SUPPORTED_FLOOR:
            verdict = Verdict.SUPPORTED
            score = best_overlap
        else:
            verdict = Verdict.UNVERIFIABLE
            score = best_overlap

        return verdict, score, Provenance(verdict=verdict, **provenance_kwargs)
