from __future__ import annotations

import hashlib
import math
import re

from .types import Generation

DIMENSIONS = 1536
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "do", "does", "for", "how", "i",
    "in", "is", "it", "my", "of", "on", "or", "the", "to", "what", "when", "with",
}


class MockProvider:
    name = "mock"
    model = "deterministic-local"

    def generate(self, instruction: str, verified_text: str) -> Generation:
        return Generation(
            verified_text,
            input_tokens=len(instruction.split()) + len(verified_text.split()),
            output_tokens=len(verified_text.split()),
        )

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * DIMENSIONS
        tokens = [
            token for token in re.findall(r"[a-z0-9]+", text.casefold())
            if len(token) > 2 and token not in STOP_WORDS
        ]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % DIMENSIONS
            vector[index] += 1.0 if digest[4] & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
