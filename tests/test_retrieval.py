# Author: 晨星
"""Retrieval & pipeline tests. Test docs EXCEED the 512-char chunk
threshold so the multi-chunk path is actually covered."""
from core.embed import HashEmbedder
from core.pipeline import RAGPipeline
from core.retrieval import HybridRetriever, NoopReranker
from core.vector import InMemoryVectorStore
from core.ingest import document_from_text, chunk_document
from core.llm import MockLLM

TRANSFORMER = (
    "Transformer 是一种基于自注意力机制的神经网络架构，由 Vaswani 等人于 2017 年提出。"
    "它完全抛弃了循环结构，依靠多头注意力并行处理序列，大幅提升了训练效率。"
    "位置编码为模型注入顺序信息，BERT 与 GPT 等大语言模型都以其为基础。" * 8
)
FAISS = (
    "FAISS 是 Meta 开源的向量相似度搜索库，支持 IndexFlatIP 精确搜索与 IVF、HNSW 近似索引。"
    "在 CPU 上，IndexFlatIP 对归一化向量做内积即余弦相似度，结果精确可靠。" * 10
)
DISTRACTOR = "深圳是一座气候温暖的南方城市，以科技创新和制造业闻名。" * 15


def _retriever() -> HybridRetriever:
    r = HybridRetriever(HashEmbedder(), InMemoryVectorStore(dim=384))
    for title, text in [("t.md", TRANSFORMER), ("f.md", FAISS), ("s.md", DISTRACTOR)]:
        r.add_chunks(chunk_document(document_from_text(title, text)))
    return r


class TestHybridRetriever:
    def test_multi_chunk_indexed(self):
        r = _retriever()
        assert r.count() >= 6  # each doc spans multiple chunks

    def test_chinese_query_hits_right_doc(self):
        r = _retriever()
        hits = r.search("Transformer 的核心机制是什么？", k=3)
        assert isinstance(hits, list)
        assert hits[0].chunk.metadata["title"] == "t.md"

    def test_faiss_query_hits_faiss_doc(self):
        r = _retriever()
        hits = r.search("IndexFlatIP 是什么索引", k=3)
        assert hits[0].chunk.metadata["title"] == "f.md"

    def test_trace_exposes_rankings(self):
        r = _retriever()
        hits, trace = r.search("Transformer 注意力", k=3, trace=True)
        assert set(trace) == {"dense_order", "bm25_order", "rerank_order", "fused_order"}
        assert len(hits) == 3

    def test_noop_reranker_preserves_order(self):
        r = _retriever()
        plain, _ = r.search("Transformer 注意力", k=3, trace=True)
        r2 = HybridRetriever(
            HashEmbedder(), InMemoryVectorStore(dim=384), reranker=NoopReranker()
        )
        for title, text in [("t.md", TRANSFORMER), ("f.md", FAISS), ("s.md", DISTRACTOR)]:
            r2.add_chunks(chunk_document(document_from_text(title, text)))
        reranked, _ = r2.search("Transformer 注意力", k=3, trace=True)
        assert [h.chunk.id for h in plain] == [h.chunk.id for h in reranked]


class TestRAGPipeline:
    def test_ingest_and_query_with_citations(self):
        p = RAGPipeline(HashEmbedder(), InMemoryVectorStore(dim=384), MockLLM())
        doc_id, n = p.ingest_text("t.md", TRANSFORMER)
        assert n >= 2
        result = p.query("Transformer 的核心机制是什么？")
        assert result.answer
        assert len(result.citations) >= 1
        assert result.citations[0].doc_id == doc_id

    def test_empty_knowledge_base_answer(self):
        p = RAGPipeline(HashEmbedder(), InMemoryVectorStore(dim=384), MockLLM())
        result = p.query("任意问题")
        assert "未在知识库中找到" in result.answer
        assert result.citations == []

    def test_stats(self):
        p = RAGPipeline(HashEmbedder(), InMemoryVectorStore(dim=384), MockLLM())
        p.ingest_text("t.md", TRANSFORMER)
        s = p.stats()
        assert s["documents"] == 1 and s["chunks"] >= 2
