# Author: 晨星
"""Agent & eval tests. Assertions target EXTERNAL SEMANTICS (non-empty
answer / contains result value), never internal protocol markers."""
from core.agent import Agent, safe_calc
from core.embed import HashEmbedder
from core.llm import MockLLM
from core.pipeline import RAGPipeline
from core.vector import InMemoryVectorStore
from eval.metrics import keyword_coverage, recall_at_k, reciprocal_rank
from eval.runner import default_golden_set, run_eval

KB = (
    "检索增强生成（RAG）先检索相关文档片段，再让大模型基于片段生成答案，"
    "它能显著减少幻觉并支持知识热更新。混合检索融合向量与关键词两路结果。" * 8
)


def _agent_with_kb() -> Agent:
    p = RAGPipeline(HashEmbedder(), InMemoryVectorStore(dim=384), MockLLM())
    p.ingest_text("rag.md", KB)
    return Agent(p, MockLLM())


class TestSafeCalc:
    def test_basic_arithmetic(self):
        assert safe_calc("1 + 2 * 3") == 7.0
        assert safe_calc("2 ** 10") == 1024.0

    def test_rejects_non_arithmetic(self):
        try:
            safe_calc("__import__('os')")
            assert False, "should raise"
        except ValueError:
            pass


class TestAgent:
    def test_math_question_returns_computed_value(self):
        agent = _agent_with_kb()
        result = agent.run("帮我计算 128 * 46 等于多少")
        assert result.answer  # external semantics: non-empty
        assert "5888" in result.answer  # 128 * 46 = 5888
        assert result.steps[0].action == "calculator"

    def test_knowledge_question_searches_then_answers(self):
        agent = _agent_with_kb()
        result = agent.run("什么是检索增强生成？")
        assert result.answer
        actions = [s.action for s in result.steps]
        assert "search_knowledge" in actions
        assert "summarize" in actions

    def test_math_error_handled(self):
        agent = _agent_with_kb()
        result = agent.run("计算 1/0 等于多少")
        assert "无法计算" in result.answer


class TestMetrics:
    def test_recall_at_k(self):
        assert recall_at_k(["a", "b", "c"], {"a", "c"}, 3) == 1.0
        assert recall_at_k(["a", "b", "c"], {"a", "c"}, 1) == 0.5

    def test_mrr(self):
        assert reciprocal_rank(["x", "y", "z"], {"z"}) == 1.0 / 3
        assert reciprocal_rank(["x"], {"nope"}) == 0.0

    def test_keyword_coverage(self):
        assert keyword_coverage("注意力机制", ["注意力", "缺失词"]) == 0.5


class TestEvalRunner:
    def test_default_golden_set_high_quality(self):
        report = run_eval(default_golden_set(), top_k=3)
        agg = report["aggregate"]
        # Offline hash-embedder baseline must clear a strict bar:
        assert agg["recall@1"] == 1.0
        assert agg["mrr"] == 1.0

    def test_fresh_pipeline_per_run_deterministic(self):
        r1 = run_eval(default_golden_set(), top_k=3)["aggregate"]
        r2 = run_eval(default_golden_set(), top_k=3)["aggregate"]
        assert r1 == r2
