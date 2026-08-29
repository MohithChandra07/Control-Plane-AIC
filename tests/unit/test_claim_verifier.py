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
def test_negation_is_not_supported_by_positive_evidence():
    corpus = [
        Passage(
            doc_id="refunds",
            text="Refunds are available within 30 days of purchase.",
        )
    ]

    verifier = ClaimVerifier(corpus)

    verdict, score, provenance = verifier.verify(
        "Refunds are not available within 30 days of purchase."
    )

    assert verdict == Verdict.CONTRADICTED
def test_conflicting_number_is_contradicted():
    corpus = [
        Passage(
            doc_id="refunds",
            text="Refund processing takes 5 to 7 business days after approval.",
        )
    ]

    verifier = ClaimVerifier(corpus)

    verdict, score, provenance = verifier.verify(
        "Refund processing takes 2 business days after approval."
    )

    assert verdict == Verdict.CONTRADICTED


def test_matching_number_is_supported():
    corpus = [
        Passage(
            doc_id="refunds",
            text="Refund processing takes 5 to 7 business days after approval.",
        )
    ]

    verifier = ClaimVerifier(corpus)

    verdict, score, provenance = verifier.verify(
        "Refund processing takes 5 to 7 business days after approval."
    )

    assert verdict == Verdict.SUPPORTED


def test_additional_unverified_number_is_not_automatically_supported():
    corpus = [
        Passage(
            doc_id="refunds",
            text="Refund processing takes 5 to 7 business days after approval.",
        )
    ]

    verifier = ClaimVerifier(corpus)

    verdict, score, provenance = verifier.verify(
        "Refund processing takes 5 to 7 business days and costs 500 rupees."
    )

    assert verdict == Verdict.CONTRADICTED

def test_semantic_paraphrase_is_supported():
    corpus = [
        Passage(
            doc_id="refunds",
            text="Refunds are available within 30 days of purchase.",
        )
    ]

    verifier = ClaimVerifier(corpus)

    verdict, score, provenance = verifier.verify(
        "Customers can get their money back during the first month after buying."
    )

    assert verdict == Verdict.SUPPORTED
def test_multiple_claims_with_one_unsupported_fact_are_not_fully_supported():
    corpus = [
        Passage(
            doc_id="refunds",
            text="Refunds are available within 30 days of purchase.",
        ),
        Passage(
            doc_id="support",
            text="Customer support is available Monday through Friday.",
        ),
    ]

    verifier = ClaimVerifier(corpus)

    verdict, score, provenance = verifier.verify(
        "Refunds are available within 30 days of purchase, "
        "and refunds are automatically deposited within 2 hours."
    )

    assert verdict != Verdict.SUPPORTED
def test_different_number_is_contradicted():
    corpus = [
        Passage(
            doc_id="refunds",
            text="Refunds are available within 30 days of purchase.",
        )
    ]

    verifier = ClaimVerifier(corpus)

    verdict, score, provenance = verifier.verify(
        "Refunds are available within 60 days of purchase."
    )

    assert verdict == Verdict.CONTRADICTED
def test_same_number_is_supported():
    corpus = [
        Passage(
            doc_id="refunds",
            text="Refunds are available within 30 days of purchase.",
        )
    ]

    verifier = ClaimVerifier(corpus)

    verdict, score, provenance = verifier.verify(
        "Customers can get a refund within 30 days of purchase."
    )

    assert verdict == Verdict.SUPPORTED
def test_multiple_claims_are_extracted_and_verified():
    corpus = [
        Passage(
            doc_id="refunds",
            text="Refunds are available within 30 days of purchase.",
        ),
        Passage(
            doc_id="shipping",
            text="Standard shipping takes 5 business days.",
        ),
    ]

    verifier = ClaimVerifier(corpus)

    verdict1, score1, provenance1 = verifier.verify(
        "Refunds are available within 30 days of purchase."
    )

    verdict2, score2, provenance2 = verifier.verify(
        "Standard shipping takes 5 business days."
    )

    assert verdict1 == Verdict.SUPPORTED
    assert verdict2 == Verdict.SUPPORTED
def test_ambiguous_claim_is_unverifiable():
    corpus = [
        Passage(
            doc_id="refunds",
            text="Refunds are available within 30 days of purchase.",
        )
    ]

    verifier = ClaimVerifier(corpus)

    verdict, score, provenance = verifier.verify(
        "Customers have a special refund arrangement."
    )

    assert verdict == Verdict.UNVERIFIABLE