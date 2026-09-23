# Author: 晨星
"""Hybrid retrieval: dense (vector store) + sparse (BM25) fused with
Reciprocal Rank Fusion (RRF k=60). An optional reranker participates
as a THIRD weighted signal (default w=0.5) and never takes over the
final ordering — a reranker that is weak on the query language must not
veto correct results (ADR-005)."""
from __future__ import annotations

from typing import Protocol

from rank_bm25 import BM25Okapi

from .embed import Embedder
from .tokenizer import tokenize
from .types import Chunk, SearchHit
from .vector import VectorStore

RRF_K = 60
RERANK_WEIGHT = 0.5


class Reranker(Protocol):
    """Cross-encoder style scorer. Higher score = more relevant."""

    name: str

    def score(self, query: str, texts: list[str]) -> list[float]:
        ...


class NoopReranker:
    """Neutral passthrough: returns zeros so fused order is preserved."""

    name = "noop"

    def score(self, query: str, texts: list[str]) -> list[float]:
        return [0.0] * len(texts)


class HybridRetriever:
    """Two-stage hybrid retriever with rerank-as-signal fusion."""

    def __init__(
        self,
        embedder: Embedder,
        store: VectorStore,
        reranker: Reranker | None = None,
        rerank_weight: float = RERANK_WEIGHT,
    ):
        self._embedder = embedder
        self._store = store
        self._reranker = reranker or NoopReranker()
        self._rerank_weight = rerank_weight
        self._chunks: dict[str, Chunk] = {}
        self._bm25: BM25Okapi | None = None
        self._bm25_ids: list[str] = []

    # -- indexing ---------------------------------------------------------
    def add_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        ids = [c.id for c in chunks]
        vectors = self._embedder.embed([c.text for c in chunks])
        self._store.add(ids, vectors)
        for c in chunks:
            self._chunks[c.id] = c
            self._bm25_ids.append(c.id)
        corpus = [tokenize(self._chunks[cid].text) for cid in self._bm25_ids]
        self._bm25 = BM25Okapi(corpus)

    # -- search ------------------------------------------------------------
    def search(
        self, query: str, k: int = 5, mode: str = "hybrid", trace: bool = False
    ) -> list[SearchHit] | tuple[list[SearchHit], dict[str, list[str]]]:
        dense_ids: list[str] = []
        if mode in ("hybrid", "dense"):
            qv = self._embedder.embed([query])[0]
            dense = self._store.search(qv, k * 2)
            dense_ids = [cid for cid, _ in dense]
        bm25_ids: list[str] = []
        if mode in ("hybrid", "bm25") and self._bm25 is not None:
            scores = self._bm25.get_scores(tokenize(query))
            order = sorted(range(len(scores)), key=lambda i: -scores[i])[: k * 2]
            bm25_ids = [self._bm25_ids[i] for i in order if scores[i] > 0]

        fused = self._rrf([dense_ids, bm25_ids])
        candidates = sorted(fused, key=lambda cid: -fused[cid])[: max(k * 2, k)]

        # Rerank as third weighted signal over the shortlist only.
        shortlist = candidates[: max(k, 8)]
        rerank_ids: list[str] = []
        if shortlist and self._rerank_weight > 0:
            scores = self._reranker.score(
                query, [self._chunks[cid].text for cid in shortlist]
            )
            order = sorted(range(len(shortlist)), key=lambda i: -scores[i])
            rerank_ids = [shortlist[i] for i in order]
            rerank_scores = self._rrf([rerank_ids])
            for cid in shortlist:
                fused[cid] = fused.get(cid, 0.0) + self._rerank_weight * rerank_scores.get(
                    cid, 0.0
                )

        final_ids = sorted(fused, key=lambda cid: -fused[cid])[:k]
        hits = [
            SearchHit(chunk=self._chunks[cid], score=fused[cid], source="fusion")
            for cid in final_ids
            if cid in self._chunks
        ]
        if trace:
            return hits, {
                "dense_order": dense_ids,
                "bm25_order": bm25_ids,
                "rerank_order": rerank_ids,
                "fused_order": final_ids,
            }
        return hits

    @staticmethod
    def _rrf(rankings: list[list[str]], k: int = RRF_K) -> dict[str, float]:
        scores: dict[str, float] = {}
        for ranking in rankings:
            for rank, cid in enumerate(ranking):
                scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        return scores

    def count(self) -> int:
        return len(self._chunks)
