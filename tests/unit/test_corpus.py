from detectors.hallucination.corpus import load_corpus


def test_loads_passages_from_all_corpus_docs():
    passages = load_corpus()
    doc_ids = {p.doc_id for p in passages}
    assert {"refund_policy", "support_hours", "customer_records"} <= doc_ids
    assert len(passages) > 0


def test_markdown_headings_are_excluded():
    passages = load_corpus()
    assert all(not p.text.startswith("#") for p in passages)
    # The doc titles themselves must not become matchable passages -- see
    # detectors/hallucination/corpus.py docstring for why this matters.
    heading_texts = {"Refund Policy", "Support Hours", "Customer Records Contact"}
    assert not any(p.text in heading_texts for p in passages)
