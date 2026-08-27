"""Synthetic labeled dataset generator (spec §18).

Generates ~400 (default) interactions with ground truth we know by
construction, since we wrote the templates. Covers the spec's required
dimensions:

  - grounded vs hallucinated (drives hallucination detector precision/recall)
  - PII vs clean (drives PII detector precision/recall)
  - policy_violation vs clean (labeled for future use -- no
    policy-violation detector exists yet, see bench/metrics/metrics.py)

`grounded` ground truth means "this response asserts a fact that appears,
verbatim or near-verbatim, in the corpus the claim verifier actually has
access to" -- i.e. the *correct* verdict is SUPPORTED. It deliberately
does NOT mean "true in the real world": a true fact the toy corpus can't
confirm should legitimately verify as UNVERIFIABLE, and labeling it
grounded=True would penalize the detector for correctly admitting it
can't check something it has no evidence for.

`has_pii`/`policy_violation` labels are assigned by template design, not
by running the real detector over the generated text -- keeping ground
truth independent of the system being evaluated (running detect_pii() to
label its own eval set would make precision/recall trivially perfect).

Deterministic: the same --seed always produces the same dataset (spec
invariant #12, reproducible evaluation).
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from random import Random

from detectors.hallucination.corpus import load_corpus

TENANTS = ["customer_support", "internal_copilot", "regulated_agent"]

# Facts drawn only from these docs are used for grounded/hallucinated
# claims -- none of them contain PII, so has_pii stays independently
# False for those categories (see module docstring).
_TEXT_FACT_DOCS = {"refund_policy", "support_hours"}
# customer_records.md facts are the ones written to also contain PII
# (see data/corpus/customer_records.md), for the grounded+PII category.
_PII_FACT_DOC = "customer_records"

GREETINGS = [
    "Thanks for reaching out! How can I help you today?",
    "Happy to help -- what can I do for you?",
    "Is there anything else I can help you with today?",
    "Sure, let me take a look into that for you.",
]

PII_TEMPLATES = [
    "You can reach our team directly at {email}.",
    "We've noted your phone number as {phone} for this case.",
    "For verification, the account holder's SSN on file is {ssn}.",
]

UNVERIFIABLE_TEMPLATES = [
    "Your account balance shows {amount} rupees pending release.",
    "Records indicate you are personally owed {amount} for this claim.",
    "The special adjustment amount approved for your case is {amount}.",
]

POLICY_VIOLATION_TEMPLATES = [
    "We can process this refund in cash outside our standard policy, just this once.",
    "I'll go ahead and waive the usual verification step for you personally.",
    "Don't worry about the standard approval process -- I'll approve this directly myself.",
]

_NUMBER = re.compile(r"\d+")


@dataclass
class DatasetItem:
    id: str
    tenant: str
    category: str
    prompt: str
    response_text: str
    has_claims: bool
    grounded: bool | None  # None = not scored for the hallucination metric
    has_pii: bool
    policy_violation: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _mutate_number(text: str, rng: Random) -> str:
    # Must not collide with any number already in the text (e.g. "5 to 7
    # business days" mutating "5" into "7" would make the claim's numbers
    # a subset of the original passage's numbers again -- still
    # (correctly) verified SUPPORTED, silently undoing the mutation).
    other_numbers = {int(n) for n in _NUMBER.findall(text)}

    def repl(match: re.Match) -> str:
        n = int(match.group())
        for _ in range(20):
            delta = rng.randint(1, max(1, n))
            mutated = max(1, n + rng.choice([-1, 1]) * delta)
            if mutated not in other_numbers:
                return str(mutated)
        return str(mutated)

    return _NUMBER.sub(repl, text, count=1)


def _fake_phone(rng: Random) -> str:
    return "".join(str(rng.randint(0, 9)) for _ in range(10))


def _fake_email(rng: Random) -> str:
    return f"user{rng.randint(1000, 9999)}@example.com"


def _fake_ssn(rng: Random) -> str:
    return f"{rng.randint(100, 999)}-{rng.randint(10, 99)}-{rng.randint(1000, 9999)}"


def _category_sequence(count: int) -> list[str]:
    # Proportions sum to 1.0; scaled to `count` and rounded, with any
    # remainder from rounding padded onto "grounded" (the largest, most
    # neutral bucket) so the total always matches exactly.
    weights = {
        "grounded": 0.25,
        "grounded_with_pii": 0.10,
        "hallucinated_contradicted": 0.20,
        "hallucinated_unverifiable": 0.15,
        "pii": 0.10,
        "policy_violation": 0.10,
        "clean_greeting": 0.10,
    }
    sequence: list[str] = []
    for category, weight in weights.items():
        sequence.extend([category] * round(count * weight))
    while len(sequence) < count:
        sequence.append("grounded")
    return sequence[:count]


def _build_item(idx: int, category: str, rng: Random, facts: dict[str, list[str]]) -> DatasetItem:
    item_id = f"item-{idx:04d}"
    tenant = TENANTS[idx % len(TENANTS)]
    prompt = "Can you help me with my request?"

    if category == "grounded":
        text = rng.choice(facts["text"])
        return DatasetItem(item_id, tenant, category, prompt, text, True, True, False, False)

    if category == "grounded_with_pii":
        text = rng.choice(facts["pii"])
        return DatasetItem(item_id, tenant, category, prompt, text, True, True, True, False)

    if category == "hallucinated_contradicted":
        # Only facts with a number are eligible -- mutating a fact with no
        # digits in it is a no-op, which would silently leave the original
        # (still-true, still-grounded) text mislabeled as hallucinated.
        text = _mutate_number(rng.choice(facts["text_with_numbers"]), rng)
        return DatasetItem(item_id, tenant, category, prompt, text, True, False, False, False)

    if category == "hallucinated_unverifiable":
        template = rng.choice(UNVERIFIABLE_TEMPLATES)
        text = template.format(amount=rng.randint(100, 90000))
        return DatasetItem(item_id, tenant, category, prompt, text, True, False, False, False)

    if category == "pii":
        template = rng.choice(PII_TEMPLATES)
        text = template.format(email=_fake_email(rng), phone=_fake_phone(rng), ssn=_fake_ssn(rng))
        return DatasetItem(item_id, tenant, category, prompt, text, True, False, True, False)

    if category == "policy_violation":
        text = rng.choice(POLICY_VIOLATION_TEMPLATES)
        return DatasetItem(item_id, tenant, category, prompt, text, True, None, False, True)

    if category == "clean_greeting":
        text = rng.choice(GREETINGS)
        return DatasetItem(item_id, tenant, category, prompt, text, False, None, False, False)

    raise ValueError(f"unknown category: {category}")


def generate_dataset(count: int = 400, seed: int = 42) -> list[DatasetItem]:
    rng = Random(seed)
    corpus = load_corpus()
    text_facts = [p.text for p in corpus if p.doc_id in _TEXT_FACT_DOCS]
    facts = {
        "text": text_facts,
        "text_with_numbers": [t for t in text_facts if _NUMBER.search(t)],
        "pii": [p.text for p in corpus if p.doc_id == _PII_FACT_DOC],
    }
    categories = _category_sequence(count)
    rng.shuffle(categories)
    return [_build_item(idx, category, rng, facts) for idx, category in enumerate(categories)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=400)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).resolve().parent / "dataset.jsonl"
    )
    args = parser.parse_args()

    items = generate_dataset(count=args.count, seed=args.seed)
    with args.out.open("w") as f:
        for item in items:
            f.write(json.dumps(item.to_dict()) + "\n")
    print(f"wrote {len(items)} interactions to {args.out}")


if __name__ == "__main__":
    main()
