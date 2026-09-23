# WorldAI 架构设计

> Author: 晨星 · v0.1.0 · 2026-09-24

## 设计原则

1. **单一职责**：每个模块只做一件事（摄入 / 检索 / 生成 / 评测互不掺和）
2. **依赖倒置（DIP）**：模块只依赖 Protocol，运行时注入实现 —— 这是「离线默认可跑 + 生产可切换」的根基
3. **入口零业务**：server/app.py 只装配，web/src/main.tsx 只挂载
4. **可独立验证**：每个模块有专属单测；跨模块有 E2E；质量有门禁
5. **规格即契约**：docs/SPEC.md 锁定范围/API/Token/验收，开发不越界

## 分层与调用关系

```
+---------------------------+
| web (React 控制台)         |  问答 / 文档库 / 评测
+------------+--------------+
             | HTTP /api/v1 {code,data,message}
+------------v--------------+
| server (FastAPI)           |  app.py: 装配  routes.py: 校验+转发
+------------+--------------+
             | 构造时注入
+------------v--------------+
| core.pipeline (RAGPipeline)|  编排：ingest_* -> retriever -> llm
+--+---------+---------+----+
   |         |         |
+--v--+   +--v-----+  +-v---+
|ingest|  |retrieval|  | llm |
|分块  |  |RRF 融合 |  |生成 |
+--+--+  +--+--+--+  +--+--+
   |        |  |        |
   |     +--v--+  +-----v----+
   |     |vector|  |embed     |
   |     |近邻  |  |向量化    |
   |     +-----+  +----------+
+--v-------------------------+
| core.agent (ReAct)          |  工具：search_knowledge / calculator
+----------------------------+
| eval.runner                 |  全新 pipeline 跑黄金集
+----------------------------+
```

## 模块接口定义

| 模块 | 对外接口 | 输入 -> 输出 | 依赖（注入） |
|------|----------|--------------|--------------|
| core.llm | `LLMProvider.generate(prompt, max_tokens, temperature) -> str` | prompt -> 文本 | 无（协议） |
| core.embed | `Embedder.embed(texts) -> list[list[float]]`，属性 `dim` | 文本 -> L2 归一向量 | 无 |
| core.vector | `VectorStore.add(ids, vectors)` / `.search(vector, k) -> [(id, score)]` / `.count()` | 向量 -> top-k | numpy |
| core.tokenizer | `tokenize(text) -> list[str]` | 中英混合文本 -> 词项 | 无 |
| core.retrieval | `HybridRetriever.add_chunks(chunks)` / `.search(query, k, mode, trace)` | 查询 -> SearchHit[] | Embedder + VectorStore + Reranker |
| core.ingest | `load_document(path)` / `document_from_text(title, text)` / `chunk_document(doc)` | 文件/文本 -> Chunk[] | pypdf（延迟导入） |
| core.pipeline | `RAGPipeline.ingest_path/ingest_text/query/stats/retrieval_trace` | 文档/问题 -> QueryAnswer | 上述全部 |
| core.agent | `Agent.run(question) -> AgentResult` | 问题 -> 答案 + 步骤 | RAGPipeline + LLMProvider |
| eval.runner | `run_eval(golden, top_k) -> {aggregate, details}` | 黄金集 -> 指标 | build_pipeline |

## 关键机制

### 混合检索（RRF k=60，重排降权）
- dense：Embedder 向量 + VectorStore 近邻，取 top 2k
- sparse：BM25Okapi（自写 CJK 分词：单字 + 二元组；jieba 仅 sdist 需编译，弃用），取 top 2k
- 融合：`score(c) = Σ 1/(60 + rank)`；重排仅在 shortlist 内作第三路信号，权重 0.5
- **设计动机**：一个对查询语言力不从心的重排器（如英文 reranker + 中文查询）若独断最终序，会无人制衡地压掉正确答案 —— 见 docs/decisions/ADR-005.md

### 生产/离线双模
- 默认离线：MockLLM（确定性抽取式回答）+ HashEmbedder（字符 bigram 哈希，中文可用）+ InMemoryVectorStore（numpy 余弦）
- 生产：llama.cpp GGUF / OpenAI 兼容端点 + fastembed ONNX + faiss-cpu IndexFlatIP
- 工厂函数 `get_llm/get_embedder/get_vector_store` 读环境变量，server 启动时装配

### CPU 线程策略（ADR-003）
小型化模型的 CPU 瓶颈是内存带宽不是算力：llama.cpp 默认 cpu_count-1 线程会慢 4 倍。
WORLDAI_LLM_THREADS 默认 4，建议区间 2-4。

### 评测确定性（ADR-006）
/eval 每次在**全新管道**上跑黄金集（含 1 篇干扰文档），杜绝运行期已摄入数据的污染；
黄金集文档均超 512 字符分块阈值，确保多块路径被真实覆盖。

### Agent（MVP 务实方案）
- 数学意图（正则识别算术表达式）-> calculator（AST 白名单求值，禁用 eval）
- 知识意图 -> search_knowledge -> summarize
- mock LLM 下走确定性启发式计划；真实 LLM 下用 REACT_PROMPT 协议（Thought/Action 两行式，最多 6 步）

## 错误处理分层

| 层 | 策略 |
|----|------|
| schemas | pydantic 校验 -> 422 |
| routes | 业务冲突 -> 409；空块 -> 400 |
| core | ValueError 带语义消息；llamacpp 缺 WORLDAI_GGUF 明确报 RuntimeError |
| agent | calculator 异常不炸流程，返回「无法计算该表达式」 |

## 性能目标与实测

| 指标 | 目标 | 实测（Ryzen 7 H 255 / 16GB，离线管道） |
|------|------|----------------------------------------|
| 单 query 延迟 | < 2s | 毫秒级（44 单测含多次 query 共 0.8s） |
| 服务冷启动 | < 5s | 约 2s（E2E 健康等待实测） |
| verify 全程 | < 60s | 约 15s（单测 + E2E + 扫描） |

## 已知边界（MVP）
- 元数据进程内存储，重启即失（SQLite 持久化见 docs/decisions/OPEN-DECISIONS.md）
- CORS allow_origins=*（本地优先；公网部署前收紧）
- 无鉴权（本地单机定位）
- 重排器协议已定义，生产实现（fastembed cross-encoder）列为 v0.2
