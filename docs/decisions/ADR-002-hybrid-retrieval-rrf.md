# ADR-002: 混合检索 = dense + BM25 + RRF(k=60) 融合

## Status: Accepted (2026-09-24)

## Background
纯向量检索对专有名词、型号、缩写（如 IndexFlatIP）召回不稳；纯 BM25 对语义改写召回差。加权分数融合需要两路分数可比（量纲不同），调参脆弱。

## Decision
dense（向量 top 2k）与 sparse（BM25 top 2k）只做名次融合：Reciprocal Rank Fusion，score = Σ 1/(60 + rank)。排名融合对分数量纲天然免疫。检索过程通过 /trace 暴露 dense_order / bm25_order / rerank_order / fused_order 四路排序供调优。

## Consequences
- 正面：中文查询 top1 命中稳定（黄金集 recall@1 = 1.0）；零调参；可观测
- 负面：RRF 对两路都错的查询无能为力（需重排或查询改写，v0.2）

## Related ADRs
ADR-005（重排降权）
