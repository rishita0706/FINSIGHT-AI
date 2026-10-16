from __future__ import annotations

import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .types import Generation


class ProviderError(RuntimeError):
    pass


class OpenAIProvider:
    name = "openai"
    model = ""
    embedding_model = ""

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "10"))
        if not 0 < self.timeout <= 30:
            raise RuntimeError("LLM_TIMEOUT_SECONDS must be greater than 0 and no more than 30")

    def _post(self, path: str, payload: dict) -> dict:
        request = Request(
            f"{self.base_url}/{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read(2_000_001)
                    if len(raw) > 2_000_000:
                        raise ProviderError("LLM provider response exceeded the 2 MB limit")
                    return json.loads(raw)
            except HTTPError as exc:
                last_error = exc
                if exc.code not in {408, 429, 500, 502, 503, 504}:
                    raise ProviderError(f"LLM provider returned HTTP {exc.code}") from exc
            except (TimeoutError, URLError, OSError) as exc:
                last_error = exc
            if attempt < 2:
                time.sleep(0.1 * (attempt + 1))
        raise ProviderError("LLM provider request failed after 3 attempts") from last_error

    def generate(self, instruction: str, verified_text: str) -> Generation:
        result = self._post(
            "chat/completions",
            {
                "model": self.model,
                "temperature": 0,
                "max_tokens": 512,
                "messages": [
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": verified_text},
                ],
            },
        )
        usage = result.get("usage", {})
        return Generation(
            text=result["choices"][0]["message"]["content"],
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
        )

    def embed(self, text: str) -> list[float]:
        result = self._post(
            "embeddings",
            {"model": self.embedding_model, "input": text},
        )
        vector = result["data"][0]["embedding"]
        if len(vector) != 1536:
            raise ProviderError("Embedding model returned an unexpected vector dimension")
        return vector
