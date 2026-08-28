"""Provider abstraction.

ControlPlane forwards allowed requests to exactly one upstream LLM provider
per deployment. The spec explicitly warns against overbuilding multi-provider
support (§11) — this is a single small interface, not a plugin system, so
adding a second provider later means implementing one class, not a framework.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ProviderError(RuntimeError):
    """Raised when the upstream provider call fails (network, HTTP error,
    malformed response). Always surfaced to the caller and audit-logged —
    never swallowed (spec §17, §25)."""


class Provider(ABC):
    @abstractmethod
    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Forward an OpenAI-style chat completion request and return the
        OpenAI-style response body."""
