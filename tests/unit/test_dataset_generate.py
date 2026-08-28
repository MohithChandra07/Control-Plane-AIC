from bench.dataset.generate import TENANTS, generate_dataset
from detectors.hallucination.corpus import load_corpus


def test_generates_requested_count():
    items = generate_dataset(count=400, seed=42)
    assert len(items) == 400


def test_deterministic_for_same_seed():
    a = generate_dataset(count=100, seed=7)
    b = generate_dataset(count=100, seed=7)
    assert [i.to_dict() for i in a] == [i.to_dict() for i in b]


def test_different_seed_gives_different_dataset():
    a = generate_dataset(count=100, seed=1)
    b = generate_dataset(count=100, seed=2)
    assert [i.response_text for i in a] != [i.response_text for i in b]


def test_covers_all_ground_truth_dimensions():
    items = generate_dataset(count=400, seed=42)
    categories = {i.category for i in items}
    assert categories == {
        "grounded",
        "grounded_with_pii",
        "hallucinated_contradicted",
        "hallucinated_unverifiable",
        "pii",
        "policy_violation",
        "clean_greeting",
    }
    assert any(i.grounded is True for i in items)
    assert any(i.grounded is False for i in items)
    assert any(i.has_pii for i in items)
    assert any(not i.has_pii for i in items)
    assert any(i.policy_violation for i in items)


def test_grounded_with_pii_is_both_true_and_flagged():
    items = [i for i in generate_dataset(count=400, seed=42) if i.category == "grounded_with_pii"]
    assert items
    for item in items:
        assert item.grounded is True
        assert item.has_pii is True


def test_uses_all_three_tenants():
    items = generate_dataset(count=400, seed=42)
    assert {i.tenant for i in items} == set(TENANTS)


def test_item_ids_are_unique():
    items = generate_dataset(count=400, seed=42)
    assert len({i.id for i in items}) == len(items)


def test_hallucinated_contradicted_never_matches_a_real_corpus_fact_verbatim():
    """Regression test: mutating a fact with no digits in it is a no-op,
    which would silently mislabel a still-true fact as hallucinated."""
    corpus_texts = {p.text for p in load_corpus()}
    items = [i for i in generate_dataset(count=400, seed=42) if i.category == "hallucinated_contradicted"]
    assert items
    for item in items:
        assert item.response_text not in corpus_texts


def test_mutated_number_never_collides_with_another_number_in_the_same_fact():
    """Regression test: "5 to 7 business days" mutating "5" into "7"
    leaves the claim's numbers a subset of the original passage's numbers
    again -- silently un-mutated from the verifier's point of view, even
    though the text visibly changed."""
    from random import Random

    from bench.dataset.generate import _NUMBER, _mutate_number

    text = "Refund processing takes 5 to 7 business days after approval."
    rng = Random(0)
    for _ in range(200):
        mutated = _mutate_number(text, rng)
        original_numbers = {int(n) for n in _NUMBER.findall(text)}
        mutated_numbers = {int(n) for n in _NUMBER.findall(mutated)}
        assert not mutated_numbers.issubset(original_numbers)
