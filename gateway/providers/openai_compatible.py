from __future__ import annotations

from typing import Any

import httpx

from gateway.providers.base import Provider, ProviderError


class OpenAICompatibleProvider(Provider):
    """Forwards requests to any OpenAI-compatible /chat/completions endpoint."""

    def __init__(self, base_url: str, api_key: str, timeout_s: float = 30.0):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout_s = timeout_s

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"upstream returned {exc.response.status_code}: {exc.response.text[:500]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"upstream request failed: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise ProviderError("upstream returned non-JSON response") from exc
