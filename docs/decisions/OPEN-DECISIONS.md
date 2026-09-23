# OPEN-DECISIONS - WorldAI

> Author: 晨星 · 规则：只追加 + 就地关闭（OPEN -> RESOLVED 补 Resolution）

| Date | Source | Open Item | Related Constraints | Current Leaning | Blocked By | Resolves When | Status |
|------|--------|-----------|---------------------|-----------------|------------|---------------|--------|
| 2026-09-24 | Phase 1 | 元数据持久化（SQLite vs JSON 快照） | MVP 进程内存储，重启即失 | 倾向 SQLite（架构师方案） | 不影响 verify 全绿 | v0.2 排期 | OPEN |
| 2026-09-24 | Phase 1 | 生产重排器（fastembed cross-encoder）接入 | 需先在黄金集证明 recall@1 不退化（ADR-005） | 倾向接入但保持 w=0.5 | 权重缓存需联网 | 缓存可用时 | OPEN |
| 2026-09-24 | Phase 3 | Docker 镜像 | pip freeze 需剔除 Windows-only 包（pywin32 等） | 已剔除，镜像未建 | 本机无可用 Docker 守护进程验证 | 有 CI 环境时 | OPEN |
