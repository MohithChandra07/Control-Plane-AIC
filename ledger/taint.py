"""Taint propagation: was this value asserted by an unverified/contradicted
claim earlier in this conversation?

Deliberately has no separate datastore. The audit ledger (ledger/audit.py)
is already the append-only, hash-chained record of every claim this
tenant's gateway has made -- adding a second, unaudited taint store would
violate CLAUDE.md rule #5 ("don't add a second, unaudited way to make a
governance decision"). Instead this module queries audit_events directly:
a value is tainted if some earlier claim in the same conversation, with
verdict CONTRADICTED or UNVERIFIABLE, asserted that same number.

This only catches numeric values (spec's own example -- a fabricated
refund amount -- is numeric) reused verbatim or with different
formatting/currency symbols ("₹48,000" vs 48000). It does not catch a
value derived through arithmetic from a tainted one, or non-numeric
tainted facts (e.g. a fabricated policy clause used as justification) --
a documented Phase 3 limitation, not a silent gap: see docs/roadmap.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ledger.models import AuditEvent

_TAINTED_VERDICTS = ("CONTRADICTED", "UNVERIFIABLE")
_NUMBER_TOKEN = re.compile(r"\d[\d,]*(?:\.\d+)?")


@dataclass
class TaintMatch:
    claim_id: str
    claim_text: str
    verdict: str
    request_id: str
    turn_id: int | None


def _normalize_amount(value: Any) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return str(round(value))
    if isinstance(value, str):
        cleaned = re.sub(r"[^\d.]", "", value)
        if not cleaned:
            return None
        try:
            return str(round(float(cleaned)))
        except ValueError:
            return None
    return None


def _numbers_in_text(text: str) -> set[str]:
    numbers: set[str] = set()
    for token in _NUMBER_TOKEN.findall(text):
        try:
            numbers.add(str(round(float(token.replace(",", "")))))
        except ValueError:
            continue
    return numbers


async def find_taint(
    session: AsyncSession, conversation_id: str | None, value: Any
) -> TaintMatch | None:
    """Returns the earliest prior claim in `conversation_id` whose text
    asserts the same numeric value, if that claim's verdict was
    CONTRADICTED or UNVERIFIABLE. None if the value isn't numeric, there's
    no conversation to search, or no match is found."""

    if not conversation_id:
        return None
    normalized = _normalize_amount(value)
    if normalized is None:
        return None

    result = await session.execute(
        select(AuditEvent)
        .where(AuditEvent.conversation_id == conversation_id)
        .where(AuditEvent.claim_id.is_not(None))
        .where(AuditEvent.verdict.in_(_TAINTED_VERDICTS))
        .order_by(AuditEvent.id)
    )
    for event in result.scalars().all():
        if not event.claim_text:
            continue
        if normalized in _numbers_in_text(event.claim_text):
            return TaintMatch(
                claim_id=event.claim_id,
                claim_text=event.claim_text,
                verdict=event.verdict,
                request_id=event.request_id,
                turn_id=event.turn_id,
            )
    return None
