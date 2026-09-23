// Author: 晨星
import { useState } from "react";
import { BarChart3, Play } from "lucide-react";
import { api, EvalReport } from "../api";

export default function EvalPage() {
  const [report, setReport] = useState<EvalReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      setReport(await api.evaluate(3));
    } catch (e) {
      setError(e instanceof Error ? e.message : "评测失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <section className="card">
        <h2 className="card-title">
          <BarChart3 size={18} color="var(--color-primary)" />
          离线评测
        </h2>
        <p className="muted">
          在全新管道上运行内置黄金集（含干扰文档），指标：recall@1 / recall@3 / MRR / 关键词覆盖率。每次运行相互独立，结果确定。
        </p>
        <button className="btn btn-primary" onClick={run} disabled={busy}>
          <Play size={16} />
          {busy ? "评测中…" : "运行评测"}
        </button>
        {error && <p className="error-text">{error}</p>}
      </section>

      {report && (
        <>
          <section className="card">
            <h2 className="card-title">聚合指标</h2>
            <div className="metric-grid">
              {Object.entries(report.aggregate).map(([k, v]) => (
                <div className="metric-card" key={k}>
                  <div className="value">{(v * 100).toFixed(0)}%</div>
                  <div className="label">{k}</div>
                </div>
              ))}
            </div>
          </section>
          <section className="card">
            <h2 className="card-title">逐题明细</h2>
            <table className="data-table">
              <thead>
                <tr>
                  <th>问题</th>
                  <th>命中文档</th>
                  <th>指标</th>
                </tr>
              </thead>
              <tbody>
                {report.details.map((d, i) => (
                  <tr key={i}>
                    <td>{d.question}</td>
                    <td className="mono">{d.ranked_doc_ids.slice(0, 3).join(", ") || "-"}</td>
                    <td className="mono">
                      {Object.entries(d.metrics)
                        .map(([k, v]) => `${k}=${v}`)
                        .join(" ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </>
  );
}
