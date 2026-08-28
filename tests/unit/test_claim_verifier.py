from detectors.base import ProvenanceSource, Verdict
from detectors.hallucination.claim_verifier import ClaimVerifier
from detectors.hallucination.corpus import Passage

CORPUS = [
    Passage(doc_id="refund_policy", text="Refunds are available within 30 days of purchase."),
    Passage(doc_id="refund_policy", text="Refund processing takes 5 to 7 business days after approval."),
    Passage(doc_id="support_hours", text="Our support team is available Monday through Friday, 9am to 6pm."),
]


def _verifier():
    return ClaimVerifier(CORPUS)


def test_grounded_claim_is_supported():
    verdict, score, provenance = _verifier().verify("Refunds are available within 30 days of purchase.")
    assert verdict == Verdict.SUPPORTED
    assert score > 0
    assert provenance.source == ProvenanceSource.RETRIEVED_DOC
    assert provenance.source_id == "refund_policy"


def test_wrong_number_is_contradicted():
    verdict, _score, provenance = _verifier().verify(
        "Refund processing takes 2 hours after approval."
    )
    assert verdict == Verdict.CONTRADICTED
    assert provenance.source_id == "refund_policy"


def test_unrelated_claim_is_unverifiable_not_contradicted():
    verdict, _, provenance = _verifier().verify("The customer's phone number is 9876543210.")
    assert verdict == Verdict.UNVERIFIABLE
    assert provenance.source == ProvenanceSource.MODEL_PRIOR


def test_empty_corpus_is_always_unverifiable():
    verdict, _, _ = ClaimVerifier([]).verify("Refunds are available within 30 days of purchase.")
    assert verdict == Verdict.UNVERIFIABLE
