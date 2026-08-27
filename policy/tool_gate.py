"""Tool-call / action gating (spec §9).

Before a consequential tool call reaches the application, decide whether
any of its arguments trace back to tainted (unverified/contradicted)
information asserted earlier in the same conversation (ledger/taint.py).
This is the mechanism behind the critical Scene 7: an agent proposing
issue_refund(amount=48000) after having earlier told the customer, on
unverifiable grounds, that they're owed ₹48,000 -- the tool call must not
silently go through just because the number "sounds right" (spec
invariant #7: tainted information cannot silently become trusted).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ledger.taint import TaintMatch, find_taint
from policy.models import Policy, Remediation
from policy.tools import ToolSpec

_MEANINGFUL_ACTIONS = (Remediation.BLOCK, Remediation.ESCALATE, Remediation.ALLOW)


@dataclass
class ToolCallDecision:
    tool_name: str
    sink: str | None
    decision: Remediation
    tainted_args: dict[str, TaintMatch] = field(default_factory=dict)


async def gate_tool_call(
    session: AsyncSession,
    conversation_id: str | None,
    tool_name: str,
    arguments: dict[str, Any],
    policy: Policy,
    tool_specs: dict[str, ToolSpec],
) -> ToolCallDecision:
    if not policy.tool_calls.enabled:
        return ToolCallDecision(tool_name=tool_name, sink=None, decision=Remediation.ALLOW)

    spec = tool_specs.get(tool_name)
    if spec is None or spec.sink not in policy.tool_calls.consequential_sinks:
        # Unknown tool, or a sink this tenant hasn't flagged as
        # consequential -- nothing to gate.
        return ToolCallDecision(
            tool_name=tool_name, sink=spec.sink if spec else None, decision=Remediation.ALLOW
        )

    tainted: dict[str, TaintMatch] = {}
    for arg_name in spec.tainted_args:
        if arg_name not in arguments:
            continue
        match = await find_taint(session, conversation_id, arguments[arg_name])
        if match is not None:
            tainted[arg_name] = match

    if not tainted:
        return ToolCallDecision(tool_name=tool_name, sink=spec.sink, decision=Remediation.ALLOW)

    action = policy.tool_calls.tainted_argument_action
    # ToolCallPolicy.tainted_argument_action is typed as Remediation for
    # schema consistency with response-level remediation, but only
    # ALLOW/ESCALATE/BLOCK are meaningful for a tool call (you can't
    # "redact" a refund) -- anything else falls back to the conservative
    # ESCALATE rather than silently allowing a tainted call through.
    decision = action if action in _MEANINGFUL_ACTIONS else Remediation.ESCALATE

    return ToolCallDecision(tool_name=tool_name, sink=spec.sink, decision=decision, tainted_args=tainted)
