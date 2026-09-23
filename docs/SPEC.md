# Spec - WorldAI v0.1.0

> Author: 晨星
> 生成日期：2026-09-24
> 基于：Phase 1 调研（PM 许清楚 / 架构师 高见远 / 设计师 颜好看，三方 verdict: pass）
> 状态：已确认

---

## 1. 产品定义
- **一句话描述**：本地优先、CPU 可跑、一键可复现的 RAG + Agent 平台
- **目标用户**：AI 工程师 / 独立开发者 / 初创技术负责人；次级为技术决策者（用评测信号做技术尽调）
- **核心问题**：主流 RAG 框架（LangChain/LlamaIndex/Dify/RAGFlow）重型、容器臃肿、离线不可验证，在受限 Windows 环境（无 GPU、无编译器、无外网）难以一键复现

## 2. MVP 范围（锁定）

| 优先级 | 功能 | 验收标准摘要 | RICE 思路 |
|--------|------|-------------|-----------|
| P0 | 文档摄入（txt/md/pdf，512/64 滑窗分块） | POST /documents 返回 doc_id + chunk 数，≥800 字符文档必多分块 | 一切功能的前提 |
| P0 | 混合检索（dense + BM25 + RRF k=60） | 中文查询 top1 命中正确文档，trace 可见三路排序 | 差异化卖点 |
| P0 | RAG 问答（引用溯源） | 回答附 citations（chunk_id/doc_id/snippet/score） | 核心价值 |
| P0 | 评测闭环（黄金集 + recall@k/MRR/关键词覆盖） | /eval 在全新管道跑，结果确定 | 开发者选购信号 |
| P0 | 离线可验证（mock LLM + hash embedder + 内存向量库） | `python scripts/verify.py` 无网无 Key 全绿 | 核心差异化 |
| P1 | Agent（search_knowledge/calculator，ReAct） | 数学问题返回计算值，知识问题先检索再答 | 打开后续想象空间 |
| P1 | SSE 流式问答 | stream=true 时逐 token 推送 + done 事件 | 体验 |
| P1 | 重排作为第三路加权信号（w=0.5） | noop 重排器不改变融合序 | 质量上限 |

## 3. 明确不做（Out-of-Scope — 锁定）

| 不做的功能 | 原因 | 何时考虑 |
|------------|------|----------|
| 账号/登录/多租户 | 本地单机工具定位，避免虚假「全栈感」 | 云端版 |
| Docker 一体化 | 本机 Python 即可运行；重型 compose 违背「一键复现」定位 | v0.2（可选镜像） |
| OCR / 复杂版面解析 | 依赖重、无 GPU 收益低 | 有用户需求后 |
| GPU 适配 | 定位即为 CPU 友好 | 另开项目 |
| WebSocket 双向流 | MVP 用 SSE 够用 | v0.2 |
| 联网搜索工具 | 离线可验证优先 | v0.2 |

## 4. 技术架构（锁定 — 版本锚定）

| 层 | 技术 | 实际版本 | 锁定原因 |
|----|------|----------|----------|
| 运行时 | Python | 3.13 | 已验证 |
| 后端 | FastAPI | 0.141.1 | 异步 + 自动 OpenAPI |
| ASGI | uvicorn | 0.53.0 | FastAPI 标准搭配 |
| 向量库 | faiss-cpu（生产）/ 内存（离线） | 1.15.0 | 免编译 win 轮子，IndexFlatIP 精确 |
| 嵌入 | fastembed（生产）/ hash bigram（离线） | 0.8.0 | ONNX CPU 免 torch；默认模型 bge-small-zh-v1.5（512 dim） |
| BM25 | rank-bm25 | 0.2.2 | 纯 Python，配自写 CJK 分词（jieba 仅 sdist 需编译，弃用） |
| LLM | llama-cpp-python（生产）/ mock（离线） | 0.3.19 | GGUF CPU 推理；Q4_K_M 推荐；n_threads 锁 2-4（内存带宽瓶颈，ADR-003） |
| PDF | pypdf | 6.18.1 | 纯 Python 免编译 |
| 校验 | pydantic | 2.13.5 | FastAPI 依赖链一致 |
| 前端框架 | React | 18.3.x | 生态成熟 |
| 构建 | Vite | 5.4.x | 快速、win 兼容（esbuild/rollup 原生包需平台轮子） |
| 语言 | TypeScript | 5.6.x | noEmitOnError 显式开启 |
| 图标 | lucide-react | 0.454.x | **Spec 锁定唯一图标库**，16/20/24px |
| 部署 | 本机进程（uvicorn + vite preview） | - | MVP 本地优先 |

## 5. API 端点清单（锁定）

> 机器可读契约见 docs/openapi.yaml。统一信封 `{code, data, message}`。

| Method | Path | 功能 | 请求体 | 响应体 |
|--------|------|------|--------|--------|
| GET | /api/v1/health | 健康检查 | - | {status:"up"} |
| GET | /api/v1/stats | 文档/块统计 | - | {documents, chunks} |
| POST | /api/v1/documents | 摄入文档 | {title, text} | 201 {doc_id, title, chunks}；409 重复；422 校验失败 |
| GET | /api/v1/documents | 文档列表 | - | [{id, title, chars}] |
| POST | /api/v1/query | RAG 问答 | {question, top_k, mode, stream} | {answer, citations[], provider} 或 SSE |
| POST | /api/v1/agent | Agent 工具调用 | {question} | {answer, steps[], tool_calls} |
| POST | /api/v1/eval | 离线评测 | {top_k} | {aggregate, details[]} |
| GET | /api/v1/trace | 检索排序追踪 | ?question=&top_k= | {dense_order, bm25_order, rerank_order, fused_order} |

## 6. 数据模型（锁定）

| 实体 | 核心字段 | 说明 |
|------|----------|------|
| Document | id(sha256[:16]), title, text, metadata | id 确定性，重复上传判 409 |
| Chunk | id(doc_id:idx), doc_id, text, metadata | 512 字符 / 64 重叠滑窗 |
| SearchHit | chunk, score, source | RRF 融合分 |
| Citation | chunk_id, doc_id, snippet, score | 回答溯源 |
| GoldenQuery | question, relevant_doc_ids, answer_keywords | 评测黄金集（含干扰文档） |

存储：MVP 进程内（向量 + 元数据）。SQLite 持久化见 docs/decisions/OPEN-DECISIONS.md。

## 7. 页面清单（锁定）

| 页面 | 路由 | 核心组件 | 对应 API | 主题 |
|------|------|----------|----------|------|
| 问答 | / (tab=chat) | 输入框 / 回答卡 / 工具步骤列表 | /agent | 浅色 |
| 文档库 | / (tab=docs) | 上传表单 / 文档列表 / 统计徽标 | /documents, /stats | 浅色 |
| 评测 | / (tab=eval) | 指标卡网格 / 明细表 | /eval | 浅色 |

## 8. 设计 Token（锁定）

> 来源：web/src/tokens.css（设计师颜好看产出，P0 门禁通过）
- **主色**：--color-primary: #2563EB（Indigo 纯色，允许；禁紫粉渐变）
- **强调色**：--color-accent: #14B8A6（仅图表/高亮）
- **中性**：#FFFFFF / #F9FAFB / #F3F4F6 / #E5E7EB / #D1D5DB
- **文字**：#111827 / #4B5563 / #9CA3AF
- **字体**：Inter + Noto Sans SC；代码 JetBrains Mono
- **间距**：4px 网格（4/8/12/16/24/32）；**圆角**：4/8/12；**阴影**：三级哑光（无发光无玻璃）
- **图标库**：lucide-react（唯一，禁止混用）
- **主题**：浅色
- **对标**：Linear 的克制 + Stripe 的精致 + Vercel 的锐利

## 9. 验收标准（锁定 — EARS）

| 编号 | 功能 | EARS 格式验收标准 | 优先级 |
|------|------|-------------------|--------|
| AC-01 | 摄入 | When 用户 POST 合法文档，系统**必须**返回 201 + doc_id + chunks≥1 | P0 |
| AC-02 | 摄入 | If 文档内容重复（确定性 id 命中），系统**必须**返回 409 | P0 |
| AC-03 | 摄入 | If title/text 为空，系统**必须**返回 422 | P0 |
| AC-04 | 摄入 | While 文档超过 512 字符，系统**必须**切出 ≥2 个块 | P0 |
| AC-05 | 问答 | When 知识库已有相关文档，系统**必须**返回非空回答 + ≥1 条引用 | P0 |
| AC-06 | 问答 | If 知识库为空，系统**必须**返回「未在知识库中找到相关内容」而非编造 | P0 |
| AC-07 | 问答 | If question 为空或 top_k 越界，系统**必须**返回 422 | P0 |
| AC-08 | 流式 | When stream=true，系统**必须**以 SSE 推送 token 事件并以 done 结束 | P1 |
| AC-09 | Agent | When 问题含算术表达式，系统**必须**调用 calculator 并返回正确数值 | P1 |
| AC-10 | Agent | When 问题为知识型，系统**必须**先 search_knowledge 再作答 | P1 |
| AC-11 | 评测 | When POST /eval，系统**必须**在全新管道上运行且两次结果一致 | P0 |
| AC-12 | 评测 | While 黄金集含干扰文档，系统**必须**达到 recall@1 = 1.0（离线管道） | P0 |
| AC-13 | 追踪 | When GET /trace，系统**必须**返回 dense/bm25/rerank/fused 四路排序 | P1 |
| AC-14 | 质量门 | While 交付前，`python scripts/verify.py` **必须**全绿（单测+E2E+emoji 扫描） | P0 |

## 10. 边界与约束
- 仅支持 64 位 Windows / Linux / macOS，Python 3.11+，Node 20+
- 不支持 IE；前端断点 ≥1024px 桌面优先
- 性能目标：离线管道单 query < 2s（CPU，384 dim，千块级语料）
- llama-cpp 线程锁 2-4（小模型内存带宽瓶颈，ADR-003）
- 评估必须全新管道（防运行期污染，ADR-006）

## 11. 内嵌已知坑（项目记忆 pitfalls.jsonl）

| 坑 | 技术栈指纹 | 根因 | 修法 |
|----|------------|------|------|
| pytest 按旧逻辑跑 | python/sandbox | 沙箱 mtime 异常，__pycache__ 未失效 | 跑测试加 `-B -p no:cacheprovider` 并先清 __pycache__ |
| MockLLM 误吞指令文本 | prompt-design | 指令中出现字面量 `<context>` 与分隔符冲突 | 分隔符用唯一名 `<kb-context>` |
| FastAPI 联合返回类型报错 | fastapi | `Envelope \| StreamingResponse` 注解非法 | 装饰器加 `response_model=None`，去注解 |
| 重排器压掉正确结果 | rerank | 重排序直接当最终序 | 重排只作第三路加权信号（w=0.5），noop 默认 |
| esbuild/rollup 原生包缺失 | vite/windows | 沙箱禁 postinstall 派生 node | --ignore-scripts + 同条命令显式装平台轮子 |
| pip 空格串变量被当单个 argv | powershell | `$pkgs` 整体作为一个参数 | 依赖逐个传参 |

## 12. 端到端验证步骤

```bash
# 1. 安装（干净环境）
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements-dev.txt

# 2. 一键验证（单测 44 + E2E 15 + emoji 门禁，全离线）
python scripts/verify.py
# 断言：verify: ALL GREEN，exit 0

# 3. 启动服务
python -m server.app   # 默认 127.0.0.1:8765

# 4. 核心成功流
curl -X POST http://127.0.0.1:8765/api/v1/documents -H "Content-Type: application/json" -d '{"title":"a.md","text":"..."}'
# 断言：201 + doc_id + chunks>=1
curl -X POST http://127.0.0.1:8765/api/v1/query -H "Content-Type: application/json" -d '{"question":"..."}'
# 断言：200 + answer 非空 + citations>=1

# 5. 关键错误流
curl -X POST http://127.0.0.1:8765/api/v1/documents -H "Content-Type: application/json" -d '{"title":"","text":"x"}'
# 断言：422
# 重复上传同一文档
# 断言：409
```

## 13. 变更记录
| 日期 | 变更内容 | 原因 | 影响范围 |
|------|----------|------|----------|
| 2026-09-24 | v0.1.0 初版锁定 | - | 全部 |
