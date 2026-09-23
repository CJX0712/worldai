# ADR-001: CPU-only 免编译 AI 栈（faiss-cpu + fastembed + llama-cpp-python）

## Status: Accepted (2026-09-24)

## Background
目标环境无 GPU、无 MSVC 编译器、HuggingFace 可能不可达。任何 sdist-only 或需本地编译的依赖都会破坏「干净环境一键复现」。torch 体量（数百 MB）在 CPU 场景投入产出比极低。

## Decision
锁定全 win_amd64 轮子组合：faiss-cpu 1.15.0（向量）+ fastembed 0.8.0（ONNX 嵌入，免 torch）+ rank-bm25 0.2.2（纯 Python）+ llama-cpp-python 0.3.19（GGUF 推理）+ pypdf 6.18.1。分词弃用 jieba（sdist-only），自写 15 行 CJK 分词（单字 + 二元组）。

## Consequences
- 正面：全部 pip 轮子即装即用；离线默认管道零外部依赖；lock 清单天然已验证可安装
- 负面：fastembed 模型权重仍需一次联网缓存（HuggingFace 不可达时需手动放置缓存目录）
- 负面：hash embedder 只有字面相似度，无语义 —— 仅作离线兜底，生产切 fastembed

## Related ADRs
ADR-002（混合检索）、ADR-003（线程策略）
