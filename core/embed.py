# Author: 晨星
"""Embedding abstraction. Default is a deterministic hash embedder that
works offline and handles Chinese via character bigrams; the production
embedder uses fastembed (ONNX, CPU, no torch)."""
from __future__ import annotations

import hashlib
import math
import os
from typing import Protocol


class Embedder(Protocol):
    """Text-to-vector contract."""

    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return vec
    return [v / norm for v in vec]


class HashEmbedder:
    """Deterministic char-bigram hashing embedder (offline default).

    Word-level features fail on unsegmented Chinese; character bigrams
    give stable, language-agnostic lexical similarity. NOT semantic —
    use FastembedEmbedder in production.
    """

    def __init__(self, dim: int = 384):
        self.dim = dim

    def _features(self, text: str) -> list[str]:
        t = text.lower()
        feats = [c for c in t if not c.isspace()]  # unigrams keep short texts alive
        feats.extend(t[i : i + 2] for i in range(len(t) - 1))
        return feats

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dim
            for feat in self._features(text):
                digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=8).digest()
                idx = int.from_bytes(digest, "little") % self.dim
                vec[idx] += 1.0
            out.append(_l2_normalize(vec))
        return out


class FastembedEmbedder:
    """Production embedder backed by fastembed ONNX runtime (CPU, no torch).

    Model weights must be pre-cached (fastembed downloads on first use);
    set WORLDAI_FASTEMBED_MODEL to override the default.
    """

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        from fastembed import TextEmbedding  # deferred: heavy import

        self._model = TextEmbedding(model_name=model_name)
        probe = next(iter(self._model.embed(["probe"])))
        self.dim = len(probe)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, v)) for v in self._model.embed(texts)]


def get_embedder(kind: str | None = None, dim: int = 384) -> Embedder:
    """Factory: WORLDAI_EMBEDDER = hash | fastembed (default hash)."""
    which = (kind or os.environ.get("WORLDAI_EMBEDDER") or "hash").lower()
    if which == "hash":
        return HashEmbedder(dim=dim)
    if which == "fastembed":
        return FastembedEmbedder(
            model_name=os.environ.get("WORLDAI_FASTEMBED_MODEL", "BAAI/bge-small-zh-v1.5")
        )
    raise ValueError(f"unknown embedder: {which}")
