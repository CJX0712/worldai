# ADR-005: 重排只作第三路加权信号（w=0.5），noop 为默认

## Status: Accepted (2026-09-24)

## Background
把交叉编码器重排顺序直接当作最终排序时，一个在查询语言上力不从心的重排器（最常见：英文 reranker + 中文查询）会无人制衡地压掉正确答案 —— 实测中文查询 top-1 命中率可从 11/12 掉到 4/12。

## Decision
重排仅在 RRF shortlist 内参与，作为第三路信号按权重 0.5 加权进入融合分：`fused[c] += 0.5 * 1/(60 + rerank_rank)`。默认注入 NoopReranker（返回全零，融合序不变）。生产重排器（fastembed cross-encoder）上线前必须先在 /eval 黄金集上证明 recall@1 不退化。

## Consequences
- 正面：重排器失效时系统质量有底线；noop 不改变结果（有单测锁定）
- 负面：强重排器的增益被部分稀释 —— 可接受的稳健性代价

## Related ADRs
ADR-002（RRF 融合）
