# Author: 晨星
"""Offline evaluation runner. ALWAYS builds a fresh pipeline per run
(determinism: no contamination from runtime-ingested data). Golden sets
must include distractor documents so recall is meaningful."""
from __future__ import annotations

from dataclasses import dataclass, field

from core.pipeline import build_pipeline

from .metrics import aggregate, keyword_coverage, recall_at_k, reciprocal_rank


@dataclass
class GoldenQuery:
    question: str
    relevant_doc_ids: set[str]
    answer_keywords: list[str] = field(default_factory=list)


@dataclass
class GoldenSet:
    """docs: list of (title, text). queries carry relevant doc titles."""

    docs: list[tuple[str, str]]
    queries: list[GoldenQuery]


def run_eval(golden: GoldenSet, top_k: int = 3) -> dict[str, object]:
    """Run the golden set on a FRESH offline pipeline."""
    pipeline = build_pipeline()  # all-offline defaults
    title_to_id: dict[str, str] = {}
    for title, text in golden.docs:
        doc_id, _ = pipeline.ingest_text(title, text)
        title_to_id[title] = doc_id

    per_query: list[dict[str, float]] = []
    details: list[dict[str, object]] = []
    for gq in golden.queries:
        result = pipeline.query(gq.question, top_k=top_k)
        ranked_doc_ids = [c.doc_id for c in result.citations]
        relevant = {title_to_id[t] for t in gq.relevant_doc_ids if t in title_to_id}
        row = {
            "recall@1": recall_at_k(ranked_doc_ids, relevant, 1),
            f"recall@{top_k}": recall_at_k(ranked_doc_ids, relevant, top_k),
            "mrr": reciprocal_rank(ranked_doc_ids, relevant),
            "keyword_coverage": keyword_coverage(result.answer, gq.answer_keywords),
        }
        per_query.append(row)
        details.append(
            {
                "question": gq.question,
                "answer": result.answer,
                "ranked_doc_ids": ranked_doc_ids,
                "metrics": row,
            }
        )
    return {"aggregate": aggregate(per_query), "details": details}


def default_golden_set() -> GoldenSet:
    """Built-in demo golden set (Chinese, with distractors)."""
    transformer_doc = (
        "Transformer 是一种基于自注意力机制的神经网络架构，由 Vaswani 等人于 2017 年提出。"
        "它完全抛弃了循环结构，依靠多头注意力并行处理序列，大幅提升了训练效率。"
        "Transformer 由编码器和解码器组成，编码器将输入序列映射为上下文表示，"
        "解码器自回归地生成输出。位置编码为模型注入顺序信息，常用正弦余弦函数。"
        "如今 BERT、GPT 等大语言模型都以 Transformer 为基础架构。" * 6
    )
    faiss_doc = (
        "FAISS 是 Meta 开源的向量相似度搜索库，专为稠密向量的高效检索设计。"
        "它支持精确搜索的 IndexFlatIP 与近似搜索的 IVF、HNSW 等索引结构。"
        "在 CPU 上，IndexFlatIP 对归一化向量做内积等价于余弦相似度，结果精确。"
        "FAISS 广泛应用于语义搜索、推荐系统与检索增强生成等场景。" * 6
    )
    distractor_doc = (
        "深圳是一座位于中国南方的现代化城市，以科技创新著称。"
        "这里聚集了大量硬件与软件企业，气候温暖湿润，全年绿意盎然。" * 6
    )
    return GoldenSet(
        docs=[
            ("transformer.txt", transformer_doc),
            ("faiss.txt", faiss_doc),
            ("shenzhen.txt", distractor_doc),
        ],
        queries=[
            GoldenQuery(
                question="Transformer 的核心机制是什么？",
                relevant_doc_ids={"transformer.txt"},
                answer_keywords=["注意力"],
            ),
            GoldenQuery(
                question="FAISS 的精确搜索索引叫什么？",
                relevant_doc_ids={"faiss.txt"},
                answer_keywords=["IndexFlatIP"],
            ),
        ],
    )
