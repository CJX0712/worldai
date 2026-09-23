# Author: 晨星
"""Unit tests for core modules: tokenizer / embed / vector / ingest."""
import math

from core.embed import HashEmbedder
from core.ingest import chunk_text, document_from_text, chunk_document
from core.tokenizer import tokenize
from core.vector import InMemoryVectorStore


class TestTokenizer:
    def test_cjk_unigram_and_bigram(self):
        toks = tokenize("自然语言")
        assert "自" in toks and "言" in toks
        assert "自然" in toks and "语言" in toks

    def test_latin_words_lowercased(self):
        assert tokenize("FAISS Index") == ["faiss", "index"]

    def test_mixed(self):
        toks = tokenize("使用 faiss 检索")
        assert "faiss" in toks and "使用" in toks

    def test_empty(self):
        assert tokenize("   ！！！") == []


class TestHashEmbedder:
    def test_dim_and_normalized(self):
        emb = HashEmbedder(dim=128)
        vec = emb.embed(["测试文本"])[0]
        assert len(vec) == 128
        assert math.isclose(math.sqrt(sum(v * v for v in vec)), 1.0, rel_tol=1e-6)

    def test_deterministic(self):
        emb = HashEmbedder()
        assert emb.embed(["相同输入"]) == emb.embed(["相同输入"])

    def test_similar_texts_closer_than_dissimilar(self):
        emb = HashEmbedder()
        a, b, c = emb.embed(["向量检索增强生成", "向量检索增强技术", "今天天气很好"])
        import numpy as np

        sim_ab = float(np.dot(a, b))
        sim_ac = float(np.dot(a, c))
        assert sim_ab > sim_ac


class TestInMemoryVectorStore:
    def test_add_search_top1_is_self(self):
        store = InMemoryVectorStore(dim=4)
        store.add(["a", "b"], [[1, 0, 0, 0], [0, 1, 0, 0]])
        hits = store.search([1, 0, 0, 0], k=2)
        assert hits[0][0] == "a"
        assert hits[0][1] > hits[1][1]

    def test_empty_store(self):
        store = InMemoryVectorStore(dim=4)
        assert store.search([1, 0, 0, 0], k=3) == []
        assert store.count() == 0

    def test_dim_mismatch_rejected(self):
        store = InMemoryVectorStore(dim=4)
        try:
            store.add(["x"], [[1, 2, 3]])
            assert False, "should raise"
        except ValueError:
            pass


class TestIngest:
    LONG = "检索增强生成将外部知识注入大模型。" * 60  # > 512 chars -> multi-chunk

    def test_short_text_single_chunk(self):
        assert chunk_text("短文本") == ["短文本"]

    def test_long_text_multi_chunk_with_overlap(self):
        chunks = chunk_text(self.LONG, size=512, overlap=64)
        assert len(chunks) >= 2
        for c in chunks:
            assert len(c) <= 512

    def test_chunk_document_stable_ids(self):
        doc = document_from_text("t.md", self.LONG)
        chunks = chunk_document(doc)
        assert chunks[0].id == f"{doc.id}:0"
        assert all(c.doc_id == doc.id for c in chunks)

    def test_document_id_deterministic(self):
        d1 = document_from_text("a.txt", "内容")
        d2 = document_from_text("a.txt", "内容")
        assert d1.id == d2.id
