# Author: 晨星
"""LLM provider abstraction. Default is an offline deterministic mock;
production providers (llama.cpp GGUF / OpenAI-compatible) are injected
via environment variables."""
from __future__ import annotations

import os
import re
from typing import Protocol


class LLMProvider(Protocol):
    """Minimal text-generation contract every provider must satisfy."""

    name: str

    def generate(
        self, prompt: str, *, max_tokens: int = 512, temperature: float = 0.2
    ) -> str:
        ...


class MockLLM:
    """Zero-dependency deterministic provider for offline tests/E2E.

    It extracts the most salient sentences from the prompt's context block
    so answers are stable and assertable without any network or model file.
    """

    name = "mock"

    def generate(
        self, prompt: str, *, max_tokens: int = 512, temperature: float = 0.2
    ) -> str:
        context = self._extract_context(prompt)
        if not context:
            return "未在知识库中找到相关内容，请先摄入文档。"
        sentences = re.split(r"(?<=[。！？.!?\n])", context)
        picked = [s.strip() for s in sentences if len(s.strip()) >= 8][:3]
        if not picked:
            picked = [context.strip()[:200]]
        return "根据知识库内容：" + "".join(picked)

    @staticmethod
    def _extract_context(prompt: str) -> str:
        # Unique tag name: instructions text must never collide with it.
        m = re.search(r"<kb-context>(.*?)</kb-context>", prompt, re.DOTALL)
        return m.group(1).strip() if m else ""


class LlamaCppLLM:
    """Local GGUF inference via llama-cpp-python (CPU-first).

    Requires env WORLDAI_GGUF pointing to a .gguf model file.
    Q4_K_M quantization is recommended for 16GB RAM machines.
    """

    name = "llamacpp"

    def __init__(self, model_path: str, n_ctx: int = 4096, n_threads: int = 4):
        from llama_cpp import Llama  # deferred: heavy import

        # Small quantized models are memory-bandwidth bound on CPU;
        # 2-4 threads beat cpu_count-1 by a wide margin.
        self._llm = Llama(
            model_path=model_path, n_ctx=n_ctx, n_threads=n_threads, verbose=False
        )

    def generate(
        self, prompt: str, *, max_tokens: int = 512, temperature: float = 0.2
    ) -> str:
        out = self._llm(
            prompt, max_tokens=max_tokens, temperature=temperature, stop=["</s>"]
        )
        return str(out["choices"][0]["text"]).strip()


class OpenAICompatLLM:
    """Any OpenAI-compatible chat endpoint (vLLM, Ollama, hosted APIs)."""

    name = "openai"

    def __init__(self, base_url: str, api_key: str, model: str):
        self._base = base_url.rstrip("/")
        self._key = api_key
        self._model = model

    def generate(
        self, prompt: str, *, max_tokens: int = 512, temperature: float = 0.2
    ) -> str:
        import httpx

        resp = httpx.post(
            f"{self._base}/chat/completions",
            headers={"Authorization": f"Bearer {self._key}"},
            json={
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=120,
        )
        resp.raise_for_status()
        return str(resp.json()["choices"][0]["message"]["content"]).strip()


def get_llm(provider: str | None = None) -> LLMProvider:
    """Factory: WORLDAI_LLM_PROVIDER = mock | llamacpp | openai (default mock)."""
    kind = (provider or os.environ.get("WORLDAI_LLM_PROVIDER") or "mock").lower()
    if kind == "mock":
        return MockLLM()
    if kind == "llamacpp":
        path = os.environ.get("WORLDAI_GGUF")
        if not path:
            raise RuntimeError("WORLDAI_GGUF not set for llamacpp provider")
        return LlamaCppLLM(
            path, n_threads=int(os.environ.get("WORLDAI_LLM_THREADS", "4"))
        )
    if kind == "openai":
        return OpenAICompatLLM(
            base_url=os.environ.get("WORLDAI_LLM_BASE", "http://localhost:11434/v1"),
            api_key=os.environ.get("WORLDAI_LLM_KEY", "ollama"),
            model=os.environ.get("WORLDAI_LLM_MODEL", "qwen2.5:7b"),
        )
    raise ValueError(f"unknown LLM provider: {kind}")
