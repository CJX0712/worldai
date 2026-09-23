# ADR-006: 评测永远在全新管道上运行

## Status: Accepted (2026-09-24)

## Background
评估端点若复用运行期单例管道，用户已摄入的文档会进入候选集，doc_id 冲突与语料漂移导致指标忽高忽低、不可复现。

## Decision
eval.runner.run_eval 每次调用都通过 build_pipeline() 构建全新管道，只摄入黄金集自带文档（含 1 篇干扰文档）。黄金集文档必须超过 512 字符分块阈值，确保多块路径被真实覆盖。单测锁定两次运行结果完全一致。

## Consequences
- 正面：指标确定、可回归；/eval 可作为 CI 质量信号
- 负面：无法直接评测「当前运行实例」的检索质量 —— 用 /trace 替代

## Related ADRs
ADR-004（离线可验证）
