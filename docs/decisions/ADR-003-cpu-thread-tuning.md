# ADR-003: llama.cpp 线程锁 2-4（内存带宽瓶颈）

## Status: Accepted (2026-09-24)

## Background
小型化模型（7B Q4_K_M 约 4GB）在 CPU 上推理的瓶颈是内存带宽而非算力。llama.cpp 默认 cpu_count-1 线程会造成内存控制器争抢，实测小量化模型慢约 4 倍。

## Decision
WORLDAI_LLM_THREADS 默认 4，建议区间 2-4；文档明确禁止设为 cpu_count-1。线程数可在运行时环境变量覆盖，便于不同机型调优。

## Consequences
- 正面：16 核机型上 7B Q4_K_M 吞吐约 4 倍提升
- 负面：对更大模型（70B）最优线程数可能不同 —— 需要按机型基准测试

## Related ADRs
ADR-001（CPU 栈）
