# Author: 晨星
"""RAG pipeline: ingestion -> hybrid retrieval -> grounded generation.
Assembles the core modules; every dependency is injected (DIP)."""
from __future__ import annotations

from .embed import Embedder, get_embedder
from .ingest import (
    chunk_document,
    document_from_text,
    load_document,
)
from .llm import LLMProvider, get_llm
from .retrieval import HybridRetriever, Reranker
from .types import Citation, Document, QueryAnswer
from .vector import VectorStore, get_vector_store

PROMPT_TEMPLATE = """<instructions>你是 WorldAI 知识库助手。仅根据知识库上下文回答问题，不要编造。
如果上下文不足以回答，明确说"知识库中没有足够信息"。</instructions>
<kb-context>
{context}
</kb-context>
<question>{question}</question>
请用中文简洁回答："""


class RAGPipeline:
    """End-to-end RAG: documents in, grounded answers out."""

    def __init__(
        self,
        embedder: Embedder,
        store: VectorStore,
        llm: LLMProvider,
        reranker: Reranker | None = None,
    ):
        self._llm = llm
        self._retriever = HybridRetriever(embedder, store, reranker=reranker)
        self._docs: dict[str, Document] = {}

    # -- ingestion ----------------------------------------------------------
    def ingest_path(self, path: str) -> tuple[str, int]:
        doc = load_document(path)
        return self._ingest_doc(doc)

    def ingest_text(self, title: str, text: str) -> tuple[str, int]:
        doc = document_from_text(title, text)
        return self._ingest_doc(doc)

    def make_document(self, title: str, text: str) -> Document:
        """Build a Document without ingesting (for pre-flight checks)."""
        return document_from_text(title, text)

    def has_document(self, doc_id: str) -> bool:
        return doc_id in self._docs

    def ingest_document(self, doc: Document) -> tuple[str, int]:
        return self._ingest_doc(doc)

    def _ingest_doc(self, doc: Document) -> tuple[str, int]:
        chunks = chunk_document(doc)
        self._retriever.add_chunks(chunks)
        self._docs[doc.id] = doc
        return doc.id, len(chunks)

    # -- query --------------------------------------------------------------
    def query(self, question: str, top_k: int = 5, mode: str = "hybrid") -> QueryAnswer:
        hits = self._retriever.search(question, k=top_k, mode=mode)
        assert isinstance(hits, list)
        context = "\n".join(f"[{i + 1}] {h.chunk.text}" for i, h in enumerate(hits))
        prompt = PROMPT_TEMPLATE.format(context=context, question=question)
        answer = self._llm.generate(prompt)
        citations = [
            Citation(
                chunk_id=h.chunk.id,
                doc_id=h.chunk.doc_id,
                snippet=h.chunk.text[:120],
                score=round(h.score, 6),
            )
            for h in hits
        ]
        return QueryAnswer(
            question=question,
            answer=answer,
            citations=citations,
            provider=self._llm.name,
            retrieval_mode=mode,
        )

    def retrieval_trace(self, question: str, top_k: int = 5) -> dict[str, list[str]]:
        """Expose dense/bm25/rerank/fused orderings for debugging."""
        _, trace = self._retriever.search(question, k=top_k, trace=True)  # type: ignore[misc]
        return trace

    # -- introspection --------------------------------------------------------
    def stats(self) -> dict[str, int]:
        return {"documents": len(self._docs), "chunks": self._retriever.count()}

    def list_documents(self) -> list[dict[str, str]]:
        return [
            {"id": d.id, "title": d.title, "chars": str(len(d.text))}
            for d in self._docs.values()
        ]


def build_pipeline(
    embedder: str | None = None,
    vector: str | None = None,
    llm: str | None = None,
    reranker: Reranker | None = None,
    dim: int = 384,
) -> RAGPipeline:
    """Factory honoring env-based provider selection. Defaults are fully
    offline (hash embedder + memory store + mock LLM)."""
    emb = get_embedder(embedder, dim=dim)
    store = get_vector_store(vector, dim=emb.dim)
    return RAGPipeline(emb, store, get_llm(llm), reranker=reranker)
