from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from dataclasses import dataclass
from typing import List, Protocol


class EmbeddingProvider(Protocol):
    def embed(self, texts: List[str]) -> List[List[float]]:
        ...


class LLMProvider(Protocol):
    def answer(self, system_prompt: str, user_prompt: str) -> str:
        ...


class HashEmbeddingProvider:
    """Deterministic local fallback for development and tests."""

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def embed(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> List[float]:
        vec = [0.0] * self.dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:2], "big") % self.dimensions
            vec[idx] += 1.0
        norm = sum(value * value for value in vec) ** 0.5 or 1.0
        return [value / norm for value in vec]


class DashScopeEmbeddingProvider:
    """OpenAI-compatible DashScope embedding provider for text-embedding-v4."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-v4",
        base_url: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.model = os.getenv("DASHSCOPE_EMBEDDING_MODEL", model)
        self.dimensions = dimensions or int(os.getenv("DASHSCOPE_EMBEDDING_DIMENSIONS", "1024"))
        self.base_url = base_url or os.getenv(
            "DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings",
        )
        if not self.api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is required for DashScopeEmbeddingProvider")

    def embed(self, texts: List[str]) -> List[List[float]]:
        payload = json.dumps({"model": self.model, "input": texts, "dimensions": self.dimensions}).encode("utf-8")
        request = urllib.request.Request(
            self.base_url,
            data=payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        return [item["embedding"] for item in sorted(data["data"], key=lambda item: item["index"])]


@dataclass
class TemplateLLMProvider:
    """Local answer generator that keeps the product runnable without API keys."""

    def answer(self, system_prompt: str, user_prompt: str) -> str:
        return user_prompt


class DeepSeekLLMProvider:
    def __init__(self, api_key: str | None = None, model: str = "deepseek-v4-flash", base_url: str | None = None) -> None:
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = os.getenv("DEEPSEEK_MODEL", model)
        self.base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions")
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required for DeepSeekLLMProvider")

    def answer(self, system_prompt: str, user_prompt: str) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.base_url,
            data=payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
