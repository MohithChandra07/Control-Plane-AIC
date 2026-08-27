import pytest

from detectors.base import Provenance, ProvenanceSource, Verdict
from policy.engine import BLOCK_MESSAGE, Decision, GovernanceEngine
from policy.loader import load_policy
from policy.models import Remediation


class FakeVerifier:
    """Returns a scripted (verdict, score, provenance) per exact claim text;
    defaults to UNVERIFIABLE/model_prior for anything not scripted."""

    def __init__(self, script: dict[str, tuple[Verdict, float, Provenance]]):
        self._script = script

    def verify(self, claim_text: str):
        if claim_text in self._script:
            return self._script[claim_text]
        return (
            Verdict.UNVERIFIABLE,
            0.5,
            Provenance(source=ProvenanceSource.MODEL_PRIOR, verdict=Verdict.UNVERIFIABLE),
        )


SUPPORTED_1 = "Refunds are available within 30 days."
SUPPORTED_2 = "Refunds are issued to the original payment method."
CONTRADICTED_1 = "Your refund processing will definitely take 2 hours."


def _supported(text: str) -> tuple[Verdict, float, Provenance]:
    return (
        Verdict.SUPPORTED,
        0.9,
        Provenance(source=ProvenanceSource.RETRIEVED_DOC, source_id="refund_policy", verdict=Verdict.SUPPORTED),
    )


def _contradicted(text: str) -> tuple[Verdict, float, Provenance]:
    return (
        Verdict.CONTRADICTED,
        0.9,
        Provenance(source=ProvenanceSource.RETRIEVED_DOC, source_id="refund_policy", verdict=Verdict.CONTRADICTED),
    )


@pytest.fixture
def customer_support():
    return load_policy("customer_support")


@pytest.fixture
def internal_copilot():
    return load_policy("internal_copilot")


@pytest.fixture
def regulated_agent():
    return load_policy("regulated_agent")


def test_clean_text_skips_tier1_and_allows(customer_support):
    engine = GovernanceEngine(FakeVerifier({}))
    result = engine.evaluate("Hello! How can I help you today?", customer_support)
    assert result.decision == Decision.ALLOW
    assert result.tier == 0
    assert result.claims == []


def test_surgical_remediation_keeps_good_claims_and_flags_bad_one(customer_support):
    engine = GovernanceEngine(
        FakeVerifier(
            {
                SUPPORTED_1: _supported(SUPPORTED_1),
                SUPPORTED_2: _supported(SUPPORTED_2),
                CONTRADICTED_1: _contradicted(CONTRADICTED_1),
            }
        )
    )
    text = f"{SUPPORTED_1} {SUPPORTED_2} {CONTRADICTED_1}"
    result = engine.evaluate(text, customer_support)

    assert result.tier == 1
    assert "30 days" in result.final_text
    assert "original payment method" in result.final_text
    assert "2 hours" not in result.final_text  # the contradicted claim was removed, not the whole response
    assert result.decision in (Decision.ESCALATE, Decision.MODIFY)


def test_unverifiable_pii_claim_gets_both_risk_labels_and_redaction(customer_support):
    engine = GovernanceEngine(FakeVerifier({}))
    text = "The customer's phone number is 9876543210 according to our records."
    result = engine.evaluate(text, customer_support)

    assert result.tier == 1
    claim = result.claims[0]
    assert claim.risk.hallucination.detected is True
    assert claim.risk.pii.detected is True
    assert claim.remediation == Remediation.REDACT
    assert "9876543210" not in result.final_text
    assert "[REDACTED_PHONE]" in result.final_text
    assert result.decision == Decision.MODIFY


def test_unverifiable_handling_differs_by_tenant(customer_support, internal_copilot, regulated_agent):
    text = "The customer's account balance is 48000 rupees, unverified."
    for policy, expected in (
        (customer_support, Remediation.HEDGE),
        (internal_copilot, Remediation.ALLOW),
        (regulated_agent, Remediation.ESCALATE),
    ):
        engine = GovernanceEngine(FakeVerifier({}))
        result = engine.evaluate(text, policy)
        assert result.claims[0].remediation == expected, policy.tenant_id


def test_hard_block_pii_category_blocks_entire_response(customer_support):
    engine = GovernanceEngine(FakeVerifier({}))
    text = "On file: SSN 123-45-6789 for verification purposes today."
    result = engine.evaluate(text, customer_support)
    assert result.decision == Decision.BLOCK
    assert result.final_text == BLOCK_MESSAGE


def test_escalated_claim_is_removed_under_fail_closed_tenant(customer_support):
    assert customer_support.fail_mode.value == "fail_closed"
    engine = GovernanceEngine(
        FakeVerifier({CONTRADICTED_1: _contradicted(CONTRADICTED_1)})
    )
    result = engine.evaluate(CONTRADICTED_1, customer_support)
    assert result.final_text == "" or "2 hours" not in result.final_text
