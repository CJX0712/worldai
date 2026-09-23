// Author: 晨星
import { useCallback, useEffect, useState } from "react";
import { FileText, Upload, RefreshCw, Database } from "lucide-react";
import { api, DocInfo, Stats } from "../api";

export default function DocsPage() {
  const [docs, setDocs] = useState<DocInfo[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [d, s] = await Promise.all([api.listDocs(), api.stats()]);
      setDocs(d);
      setStats(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败（后端是否已启动？）");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function upload() {
    if (!title.trim() || !text.trim() || busy) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const created = await api.uploadDoc(title.trim(), text.trim());
      setNotice(`已摄入「${created.title}」，切分 ${created.chunks} 块`);
      setTitle("");
      setText("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "上传失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <section className="card">
        <h2 className="card-title">
          <Upload size={18} color="var(--color-primary)" />
          摄入文档
        </h2>
        <div className="field">
          <label htmlFor="doc-title">标题</label>
          <input
            id="doc-title"
            className="input"
            placeholder="例如：transformer.md"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="doc-text">正文（自动按 512 字符滑动窗口切块）</label>
          <textarea
            id="doc-text"
            className="textarea"
            placeholder="粘贴文档正文…"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </div>
        <div style={{ marginTop: "var(--space-3)" }}>
          <button className="btn btn-primary" onClick={upload} disabled={busy || !title.trim() || !text.trim()}>
            <Upload size={16} />
            {busy ? "摄入中…" : "摄入"}
          </button>
        </div>
        {error && <p className="error-text">{error}</p>}
        {notice && <p className="muted">{notice}</p>}
      </section>

      <section className="card">
        <h2 className="card-title">
          <Database size={18} color="var(--color-accent)" />
          文档库
          {stats && (
            <span className="badge badge-primary">
              {stats.documents} 篇 / {stats.chunks} 块
            </span>
          )}
          <button className="btn btn-ghost" onClick={refresh} style={{ marginLeft: "auto" }}>
            <RefreshCw size={14} />
            刷新
          </button>
        </h2>
        {docs.length === 0 ? (
          <p className="muted">暂无文档，先在上方摄入一篇。</p>
        ) : (
          <ul className="doc-list">
            {docs.map((d) => (
              <li className="doc-item" key={d.id}>
                <FileText size={18} color="var(--color-text-tertiary)" />
                <div className="meta">
                  <div className="title">{d.title}</div>
                  <div className="muted mono">{d.id}</div>
                </div>
                <span className="badge">{d.chars} 字符</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
