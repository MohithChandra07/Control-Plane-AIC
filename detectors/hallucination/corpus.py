"""Loads the small fake-enterprise corpus (data/corpus/*.md) that
ClaimVerifier grounds claims against.

Paragraph-level passages (split on blank lines) rather than whole
documents: fine-grained enough that a single fabricated sentence doesn't
get "supported" just because it shares a document with true ones.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "corpus"


@dataclass
class Passage:
    doc_id: str
    text: str


def load_corpus(corpus_dir: Path = CORPUS_DIR) -> list[Passage]:
    passages: list[Passage] = []
    for path in sorted(corpus_dir.glob("*.md")):
        doc_id = path.stem
        for paragraph in path.read_text().split("\n\n"):
            stripped = paragraph.strip().lstrip("#").strip()
            if stripped:
                passages.append(Passage(doc_id=doc_id, text=stripped))
    return passages
