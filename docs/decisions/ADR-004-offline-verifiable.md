# ADR-004: 离线默认可验证是硬需求（Protocol + 注入 + mock 默认）

## Status: Accepted (2026-09-24)

## Background
「单测全绿但系统从未真跑过」是交付事故的高发根因；依赖外部服务（API Key、模型文件、数据库）的测试在 CI / 受限环境里必然 flaky。

## Decision
每个外部依赖抽象为 Protocol（LLMProvider / Embedder / VectorStore / Reranker），运行时工厂按环境变量注入。默认注入零依赖实现：MockLLM（确定性抽取式回答）+ HashEmbedder（字符 bigram，中文可用）+ InMemoryVectorStore。E2E 用自包含 Python 脚本真实拉起 uvicorn 进程，轮询 /health，跑核心成功流 + 每条错误流，finally taskkill 防端口泄漏。verify 一条命令串起 单测 -> E2E -> P0 扫描。

## Consequences
- 正面：无网无 Key 全绿；README 里的「一键命令」真的能证明系统跑起来
- 负面：mock 路径不覆盖真实模型行为 —— 生产切换需另行基准测试（文档已声明）

## Related ADRs
ADR-006（评测确定性）
