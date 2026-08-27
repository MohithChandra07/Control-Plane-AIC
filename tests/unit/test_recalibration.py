from policy.recalibration import suggest_recalibration


def test_no_suggestion_with_too_few_reviews():
    reviews = [{"decision": "ESCALATE", "agree": False}] * 2
    assert suggest_recalibration("t", reviews, min_reviews=3) is None


def test_no_suggestion_when_agreement_is_high():
    reviews = [{"decision": "ESCALATE", "agree": True}] * 8 + [{"decision": "ESCALATE", "agree": False}] * 2
    assert suggest_recalibration("t", reviews, disagreement_threshold=0.3) is None


def test_suggestion_when_disagreement_is_high():
    reviews = [{"decision": "ESCALATE", "agree": False}] * 7 + [{"decision": "ESCALATE", "agree": True}] * 3
    result = suggest_recalibration("customer_support", reviews, disagreement_threshold=0.3)
    assert result is not None
    assert result.tenant_id == "customer_support"
    assert result.reviewed_count == 10
    assert result.disagreement_rate == 0.7
    assert result.suggested_appetite_delta < 0  # relax, not tighten
    assert "customer_support" in result.message


def test_non_escalation_reviews_are_ignored():
    reviews = [{"decision": "ALLOW", "agree": False}] * 10  # never escalated, irrelevant to this heuristic
    assert suggest_recalibration("t", reviews) is None


def test_block_decisions_count_same_as_escalate():
    reviews = [{"decision": "BLOCK", "agree": False}] * 5
    result = suggest_recalibration("t", reviews, min_reviews=3, disagreement_threshold=0.3)
    assert result is not None
    assert result.reviewed_count == 5
