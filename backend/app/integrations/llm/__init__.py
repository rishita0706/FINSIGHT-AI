"""LLM and embedding adapters used only to phrase or retrieve verified content."""

from __future__ import annotations

import os
import re
from typing import Protocol

from .types import Generation
from .mock import MockProvider
from .openai import OpenAIProvider, ProviderError


class Provider(Protocol):
    name: str
    model: str

    def generate(self, instruction: str, verified_text: str) -> Generation: ...

    def embed(self, text: str) -> list[float]: ...

def get_provider() -> Provider:
    provider_name = os.getenv("LLM_PROVIDER", "mock").casefold()
    if provider_name == "mock":
        return MockProvider()
    if provider_name == "openai":
        return OpenAIProvider()
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider_name}")


def phrase_verified(provider: Provider, verified_text: str) -> Generation:
    """Accept a rewrite only when it retains the verifiable facts in the source."""
    generation = provider.generate(
        "Rewrite the verified answer for clarity. Add no facts, advice, figures, or citations.",
        verified_text,
    )
    source_numbers = set(re.findall(r"(?<!\w)[₹$]?\d[\d,]*(?:\.\d+)?%?", verified_text))
    result_numbers = set(re.findall(r"(?<!\w)[₹$]?\d[\d,]*(?:\.\d+)?%?", generation.text))
    source_urls = set(re.findall(r"https?://\S+", verified_text))
    result_urls = set(re.findall(r"https?://\S+", generation.text))
    if not generation.text.strip() or source_numbers != result_numbers or source_urls != result_urls:
        return Generation(verified_text, generation.input_tokens, 0)
    return generation


__all__ = ["Generation", "Provider", "ProviderError", "get_provider", "phrase_verified"]
