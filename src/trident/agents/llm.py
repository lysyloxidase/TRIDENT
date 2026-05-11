"""LiteLLM-backed completion helper with deterministic offline fallback."""

from __future__ import annotations

import os
from dataclasses import dataclass

from trident.agents.base import FALLBACK_LLM_MODEL, PRIMARY_LLM_MODEL


@dataclass
class LLMResponse:
    text: str
    model_name: str
    used_fallback: bool = False


class LLMClient:
    """Call Claude Sonnet via LiteLLM, falling back to Llama 3.3 when enabled."""

    def __init__(
        self,
        primary_model: str = PRIMARY_LLM_MODEL,
        fallback_model: str = FALLBACK_LLM_MODEL,
        live: bool | None = None,
    ) -> None:
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.live = live if live is not None else os.getenv("TRIDENT_LIVE_LLM") == "1"

    def complete(self, prompt: str, *, system: str | None = None) -> LLMResponse:
        if not self.live:
            return LLMResponse(text=self._offline_completion(prompt), model_name=self.primary_model)

        try:
            return self._complete_with_model(self.primary_model, prompt, system=system)
        except Exception:
            response = self._complete_with_model(self.fallback_model, prompt, system=system)
            response.used_fallback = True
            return response

    def _complete_with_model(
        self,
        model: str,
        prompt: str,
        *,
        system: str | None,
    ) -> LLMResponse:
        from litellm import completion

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = completion(model=model, messages=messages, temperature=0.0)
        text = response["choices"][0]["message"]["content"]
        return LLMResponse(text=text, model_name=model)

    @staticmethod
    def _offline_completion(prompt: str) -> str:
        first_line = prompt.strip().splitlines()[0] if prompt.strip() else "TRIDENT synthesis"
        return (
            f"{first_line}\n\n"
            "Offline deterministic synthesis: evidence was ranked from verified "
            "fixture sources. Enable TRIDENT_LIVE_LLM=1 for LiteLLM execution."
        )
