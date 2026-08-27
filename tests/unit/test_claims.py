from detectors.claims import extract_claims


def test_splits_multiple_sentences_and_preserves_spans():
    text = "Refunds are available within 30 days. Refunds are issued to the original method."
    claims = extract_claims(text)
    assert [c.text for c in claims] == [
        "Refunds are available within 30 days.",
        "Refunds are issued to the original method.",
    ]
    for claim in claims:
        assert text[claim.start : claim.end] == claim.text


def test_skips_questions():
    claims = extract_claims("How can I help you today?")
    assert claims == []


def test_skips_short_greetings():
    claims = extract_claims("Hello! Thanks.")
    assert claims == []


def test_mixed_question_and_claim():
    text = "Is there anything else? Refunds are available within 30 days of purchase."
    claims = extract_claims(text)
    assert len(claims) == 1
    assert claims[0].text == "Refunds are available within 30 days of purchase."
