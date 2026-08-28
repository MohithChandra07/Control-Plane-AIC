from detectors.tier0 import quick_risk_score


def test_clean_greeting_scores_zero():
    assert quick_risk_score("Hello! How can I help you today?") == 0.0


def test_pii_pattern_scores_high():
    assert quick_risk_score("Call us at 9876543210.") >= 0.9


def test_digits_raise_score_below_pii_level():
    score = quick_risk_score("Refunds are available within 30 days.")
    assert 0.0 < score < 0.9


def test_score_is_capped_at_one():
    assert quick_risk_score("Call 9876543210 or 1234567890 or 5555555555.") <= 1.0
