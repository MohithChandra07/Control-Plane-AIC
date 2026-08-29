"""Heuristic claim verifier: grounds a claim against the local corpus and
returns SUPPORTED / CONTRADICTED / UNVERIFIABLE.

This is a deterministic keyword+number-overlap heuristic, not a real NLI
cross-encoder.

Method:
1. Find the corpus passage with the highest normalized word overlap.
2. Below the relevance floor -> UNVERIFIABLE.
3. Missing claim numbers -> CONTRADICTED.
4. Different negation -> CONTRADICTED.
5. Strong semantic overlap -> SUPPORTED.
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

_NEGATION_WORDS = {
    "not",
    "no",
    "never",
    "cannot",
    "can't",
    "without",
}

_SEMANTIC_PHRASES = {
    "get their money back": "refund",
    "receive their money back": "refund",
    "money back": "refund",
    "first month": "days",
    "one month": "days",
}

_RELEVANCE_FLOOR = 0.34
_SUPPORTED_FLOOR = 0.6


def _normalize_word(word: str) -> str:
    word = word.lower()

    if word in {"buy", "bought", "buying"}:
        return "purchase"

    if word in {"refunds", "refunded", "refunding"}:
        return "refund"

    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"

    if word.endswith("ing") and len(word) > 5:
        return word[:-3]

    if word.endswith("ed") and len(word) > 4:
        return word[:-2]

    if word.endswith("s") and len(word) > 4:
        return word[:-1]

    return word


def _keywords(text: str) -> set[str]:
    normalized = text.lower()

    for phrase, replacement in _SEMANTIC_PHRASES.items():
        normalized = normalized.replace(phrase, replacement)

    words = {
        _normalize_word(word)
        for word in _WORD.findall(normalized)
    }

    return words - _STOPWORDS


def _numbers(text: str) -> set[str]:
    return set(_NUMBER.findall(text))


def _has_negation(text: str) -> bool:
    words = set(re.findall(r"[a-zA-Z]+", text.lower()))
    return bool(words & _NEGATION_WORDS)


class ClaimVerifier:
    def __init__(self, corpus: list[Passage]):
        self._corpus = corpus
        self._passage_keywords = [
            (passage, _keywords(passage.text))
            for passage in corpus
        ]

    def verify(
        self,
        claim_text: str,
    ) -> tuple[Verdict, float, Provenance]:
        claim_words = _keywords(claim_text)

        best_passage: Passage | None = None
        best_overlap = 0.0

        if claim_words:
            for passage, words in self._passage_keywords:
                if not words:
                    continue

                matched_words = len(claim_words & words)
                overlap = matched_words / min(
                    len(claim_words),
                    len(words),
                )

                if overlap > best_overlap:
                    best_overlap = overlap
                    best_passage = passage

        if best_passage is None or best_overlap < _RELEVANCE_FLOOR:
            return (
                Verdict.UNVERIFIABLE,
                0.5,
                Provenance(
                    source=ProvenanceSource.MODEL_PRIOR,
                    verdict=Verdict.UNVERIFIABLE,
                ),
            )

        claim_numbers = _numbers(claim_text)
        passage_numbers = _numbers(best_passage.text)

        provenance_kwargs = {
            "source": ProvenanceSource.RETRIEVED_DOC,
            "source_id": best_passage.doc_id,
        }

        claim_negated = _has_negation(claim_text)
        passage_negated = _has_negation(best_passage.text)

        if claim_negated != passage_negated:
            verdict = Verdict.CONTRADICTED
            score = 0.9

            return (
                verdict,
                score,
                Provenance(
                    verdict=verdict,
                    **provenance_kwargs,
                ),
            )

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

        return (
            verdict,
            score,
            Provenance(
                verdict=verdict,
                **provenance_kwargs,
            ),
        )