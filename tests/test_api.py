# Author: 晨星
"""API contract tests via FastAPI TestClient (offline, in-process)."""
from fastapi.testclient import TestClient

from server.app import create_app

DOC = (
    "FAISS 是 Meta 开源的向量相似度搜索库，IndexFlatIP 提供精确内积搜索，"
    "对归一化向量等价于余弦相似度，广泛用于语义检索与 RAG 场景。" * 8
)


def _client() -> TestClient:
    return TestClient(create_app())


class TestHealthAndDocs:
    def test_health(self):
        r = _client().get("/api/v1/health")
        assert r.status_code == 200
        assert r.json()["code"] == 0
        assert r.json()["data"]["status"] == "up"

    def test_create_document_201(self):
        c = _client()
        r = c.post("/api/v1/documents", json={"title": "faiss.md", "text": DOC})
        assert r.status_code == 201
        data = r.json()["data"]
        assert data["doc_id"] and data["chunks"] >= 2

    def test_duplicate_document_409(self):
        c = _client()
        c.post("/api/v1/documents", json={"title": "faiss.md", "text": DOC})
        r = c.post("/api/v1/documents", json={"title": "faiss.md", "text": DOC})
        assert r.status_code == 409

    def test_empty_title_422(self):
        r = _client().post("/api/v1/documents", json={"title": "", "text": DOC})
        assert r.status_code == 422

    def test_list_documents(self):
        c = _client()
        c.post("/api/v1/documents", json={"title": "faiss.md", "text": DOC})
        docs = c.get("/api/v1/documents").json()["data"]
        assert len(docs) == 1 and docs[0]["title"] == "faiss.md"


class TestQueryAndAgent:
    def test_query_success_with_citations(self):
        c = _client()
        c.post("/api/v1/documents", json={"title": "faiss.md", "text": DOC})
        r = c.post("/api/v1/query", json={"question": "IndexFlatIP 是什么？"})
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["answer"]
        assert len(data["citations"]) >= 1
        assert data["provider"] == "mock"

    def test_query_empty_question_422(self):
        r = _client().post("/api/v1/query", json={"question": ""})
        assert r.status_code == 422

    def test_query_stream_sse(self):
        c = _client()
        c.post("/api/v1/documents", json={"title": "faiss.md", "text": DOC})
        r = c.post(
            "/api/v1/query", json={"question": "FAISS 是什么？", "stream": True}
        )
        assert r.status_code == 200
        assert "event: token" in r.text
        assert "event: done" in r.text

    def test_agent_calculation(self):
        r = _client().post("/api/v1/agent", json={"question": "计算 128 * 46"})
        assert r.status_code == 200
        data = r.json()["data"]
        assert "5888" in data["answer"]

    def test_agent_knowledge_flow(self):
        c = _client()
        c.post("/api/v1/documents", json={"title": "faiss.md", "text": DOC})
        r = c.post("/api/v1/agent", json={"question": "FAISS 支持哪些索引？"})
        data = r.json()["data"]
        assert data["answer"]
        assert any(s["action"] == "search_knowledge" for s in data["steps"])


class TestEvalAndTrace:
    def test_eval_endpoint(self):
        r = _client().post("/api/v1/eval", json={"top_k": 3})
        assert r.status_code == 200
        agg = r.json()["data"]["aggregate"]
        assert agg["recall@1"] == 1.0

    def test_trace_endpoint(self):
        c = _client()
        c.post("/api/v1/documents", json={"title": "faiss.md", "text": DOC})
        r = c.get("/api/v1/trace", params={"question": "FAISS 索引"})
        trace = r.json()["data"]
        assert "dense_order" in trace and "fused_order" in trace
