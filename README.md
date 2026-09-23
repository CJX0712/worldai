# WorldAI

> Author: 晨星 · License: MIT · Repo: https://github.com/CJX0712/worldai

**本地优先、CPU 可跑、一键可复现的 RAG + Agent 平台。**
文档摄入 -> 混合检索（向量 + BM25 + RRF）-> LLM 生成（本地 GGUF / 远端 API 可切换）-> 离线评测闭环。

区别于重型框架：默认全离线管道（mock LLM + hash embedder + 内存向量库），
`python scripts/verify.py` 在**无网络、无 API Key、无模型文件**下即可证明系统真实可用。

---

## 特性

- **混合检索**：dense（FAISS / 内存余弦）+ sparse（BM25 + 自写 CJK 分词）经 RRF（k=60）融合；重排只作第三路加权信号（w=0.5），永不独断
- **CPU 友好**：全部依赖有 win_amd64 免编译轮子；llama.cpp 线程锁 2-4（小模型内存带宽瓶颈）
- **生产/离线双模**：所有外部依赖是 Protocol + 运行时注入，环境变量一键切换
- **可观测**：/trace 暴露 dense/bm25/rerank/fused 四路排序；/eval 黄金集评测（含干扰文档），每次全新管道保证确定
- **工程门禁**：单测 44 + E2E 15（真进程启动，成功流 + 错误流）+ emoji P0 扫描，一条命令全绿

## 架构

```
web/  React + Vite + TS 控制台（问答 / 文档库 / 评测）
  |  HTTP /api/v1（统一信封 {code,data,message}）
server/  FastAPI 装配层（app.py 只装配，routes.py 只转发）
  |
core/  领域层（单一职责，依赖注入）
  pipeline  编排：摄入 -> 检索 -> 生成
  ingest    txt/md/pdf 加载 + 512/64 滑窗分块
  retrieval dense + BM25 + RRF + 重排信号
  vector    VectorStore Protocol（memory | faiss）
  embed     Embedder Protocol（hash | fastembed）
  llm       LLMProvider Protocol（mock | llamacpp | openai）
  agent     ReAct 工具调用（search_knowledge / calculator）
  tokenizer 零依赖 CJK 分词（单字 + 二元组）
eval/  黄金集评测（recall@k / MRR / 关键词覆盖，全新管道）
tools/ scan_emoji.py（P0 门禁）
scripts/ e2e.py + verify.py（一键验证）
docs/  SPEC.md / openapi.yaml / decisions/ADR-*
```

详细模块接口与调用关系见 [ARCHITECTURE.md](ARCHITECTURE.md)；规格契约见 [docs/SPEC.md](docs/SPEC.md)。

## 快速开始（部署指南）

```bash
# 1. 环境：Python 3.11+（后端）+ Node 20+（前端，可选）
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# 2. 安装（可复现：锁版清单）
pip install -r requirements.lock.txt    # 精确版本
# 或 pip install -r requirements-dev.txt（范围版本 + pytest）

# 3. 一键验证（全离线，约 10 秒）
python scripts/verify.py
# 期望输出：verify: ALL GREEN

# 4. 启动 API（默认 127.0.0.1:8765，WORLDAI_PORT 可改）
python -m server.app
# 交互文档：http://127.0.0.1:8765/api/docs

# 5. 前端（可选）
cd web
npm ci
npm run dev        # http://127.0.0.1:5173（已配 /api 代理）
npm run build      # 产物 web/dist/
```

## 使用指南

### 摄入文档
```bash
curl -X POST http://127.0.0.1:8765/api/v1/documents \
  -H "Content-Type: application/json" \
  -d '{"title":"faiss.md","text":"FAISS 是 Meta 开源的向量相似度搜索库……"}'
# 201 -> {"code":0,"data":{"doc_id":"...","chunks":3}}
```

### 问答（含引用溯源）
```bash
curl -X POST http://127.0.0.1:8765/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question":"IndexFlatIP 是什么？","top_k":5}'
# stream=true 时返回 SSE（token 事件流 + done）
```

### Agent（工具调用）
```bash
curl -X POST http://127.0.0.1:8765/api/v1/agent \
  -H "Content-Type: application/json" \
  -d '{"question":"计算 128 * 46"}'        # -> 5888
curl -X POST http://127.0.0.1:8765/api/v1/agent \
  -H "Content-Type: application/json" \
  -d '{"question":"FAISS 支持哪些索引？"}'  # -> 先 search_knowledge 再作答
```

### 评测与追踪
```bash
curl -X POST http://127.0.0.1:8765/api/v1/eval -d '{"top_k":3}' -H "Content-Type: application/json"
curl "http://127.0.0.1:8765/api/v1/trace?question=FAISS"
```

## 生产模式（切换真实 AI 组件）

全部通过环境变量，无需改代码：

| 变量 | 取值 | 说明 |
|------|------|------|
| WORLDAI_LLM_PROVIDER | mock(默认) / llamacpp / openai | LLM 提供方 |
| WORLDAI_GGUF | 路径 | llamacpp 的 GGUF 模型文件（推荐 Q4_K_M） |
| WORLDAI_LLM_THREADS | 4(默认) | llama.cpp 线程数（锁 2-4） |
| WORLDAI_LLM_BASE / KEY / MODEL | - | openai 兼容端点（vLLM/Ollama/托管 API） |
| WORLDAI_EMBEDDER | hash(默认) / fastembed | 嵌入器（fastembed 默认 bge-small-zh-v1.5） |
| WORLDAI_FASTEMBED_MODEL | 模型名 | 需提前缓存权重 |
| WORLDAI_VECTOR | memory(默认) / faiss | 向量库 |
| WORLDAI_PORT | 8765(默认) | API 端口 |

示例（本地 GGUF + fastembed + faiss 全生产链路）：
```bash
set WORLDAI_LLM_PROVIDER=llamacpp
set WORLDAI_GGUF=models\qwen2.5-7b-instruct-q4_k_m.gguf
set WORLDAI_EMBEDDER=fastembed
set WORLDAI_VECTOR=faiss
python -m server.app
```

## 项目结构

```
worldai/
  core/ server/ web/ eval/ tests/ tools/ scripts/ docs/
  requirements.txt          范围依赖
  requirements-dev.txt      开发依赖（含 pytest）
  requirements.lock.txt     精确锁版（干净环境一键复现）
  web/package-lock.json     前端锁版（npm ci）
```

## 质量状态

| 门禁 | 状态 |
|------|------|
| pytest（44 用例） | PASS |
| E2E（15 断言，真进程） | PASS |
| tsc --noEmit + vite build | PASS |
| P0 emoji 扫描 | PASS（0 违规） |
