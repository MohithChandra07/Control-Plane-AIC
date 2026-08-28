"""Tool sink catalog loader (data/tools.yaml).

Classifies known tool/function names by consequence (spec §9 step 4 --
"classify the consequence of the sink") and which of their arguments
should be checked for taint. Shared across tenants: a tool's nature
doesn't change per tenant. What differs per tenant -- whether a sink is
consequential for them, and what happens on a tainted argument -- lives in
policy.models.ToolCallPolicy instead, per "policy lives in configs/, not
scattered in source" (CLAUDE.md rule #4).
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

TOOLS_CONFIG = Path(__file__).resolve().parent.parent / "data" / "tools.yaml"


class ToolSpec(BaseModel):
    sink: str
    tainted_args: list[str] = Field(default_factory=list)


def load_tool_specs(path: Path = TOOLS_CONFIG) -> dict[str, ToolSpec]:
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text()) or {}
    return {name: ToolSpec.model_validate(spec) for name, spec in raw.items()}
