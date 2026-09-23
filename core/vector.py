# Author: 晨星
"""Vector store abstraction. Default in-memory cosine store (offline);
production store backed by faiss-cpu IndexFlatIP."""
from __future__ import annotations

import os
from typing import Protocol

import numpy as np


class VectorStore(Protocol):
    """Nearest-neighbour search contract over L2-normalized vectors."""

    def add(self, ids: list[str], vectors: list[list[float]]) -> None:
        ...

    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
        """Return (id, cosine_score) pairs sorted by score desc."""
        ...

    def count(self) -> int:
        ...


class InMemoryVectorStore:
    """Numpy cosine store. Zero-dependency offline default."""

    def __init__(self, dim: int):
        self._dim = dim
        self._ids: list[str] = []
        self._mat = np.zeros((0, dim), dtype=np.float32)

    def add(self, ids: list[str], vectors: list[list[float]]) -> None:
        arr = np.asarray(vectors, dtype=np.float32)
        if arr.shape[1] != self._dim:
            raise ValueError(f"vector dim {arr.shape[1]} != store dim {self._dim}")
        self._ids.extend(ids)
        self._mat = np.vstack([self._mat, arr])

    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
        if len(self._ids) == 0:
            return []
        q = np.asarray(vector, dtype=np.float32)
        scores = self._mat @ q  # vectors are L2-normalized -> dot == cosine
        k = min(k, len(self._ids))
        top = np.argpartition(-scores, k - 1)[:k]
        top = top[np.argsort(-scores[top])]
        return [(self._ids[i], float(scores[i])) for i in top]

    def count(self) -> int:
        return len(self._ids)


class FaissVectorStore:
    """faiss-cpu IndexFlatIP store (exact inner product on normalized
    vectors == exact cosine). Production default for large corpora."""

    def __init__(self, dim: int):
        import faiss  # deferred: heavy import

        self._dim = dim
        self._index = faiss.IndexFlatIP(dim)
        self._ids: list[str] = []

    def add(self, ids: list[str], vectors: list[list[float]]) -> None:
        arr = np.asarray(vectors, dtype=np.float32)
        if arr.shape[1] != self._dim:
            raise ValueError(f"vector dim {arr.shape[1]} != store dim {self._dim}")
        self._index.add(arr)
        self._ids.extend(ids)

    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
        if len(self._ids) == 0:
            return []
        q = np.asarray([vector], dtype=np.float32)
        k = min(k, len(self._ids))
        scores, idxs = self._index.search(q, k)
        return [
            (self._ids[i], float(s))
            for s, i in zip(scores[0], idxs[0])
            if 0 <= i < len(self._ids)
        ]

    def count(self) -> int:
        return len(self._ids)


def get_vector_store(kind: str | None = None, dim: int = 384) -> VectorStore:
    """Factory: WORLDAI_VECTOR = memory | faiss (default memory)."""
    which = (kind or os.environ.get("WORLDAI_VECTOR") or "memory").lower()
    if which == "memory":
        return InMemoryVectorStore(dim=dim)
    if which == "faiss":
        return FaissVectorStore(dim=dim)
    raise ValueError(f"unknown vector store: {which}")
