// Author: 晨星
import { useState } from "react";
import { Send, Bot, Search, Wrench } from "lucide-react";
import { api, AgentResult } from "../api";

export default function ChatPage() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AgentResult | null>(null);

  async function ask() {
    const q = question.trim();
    if (!q || loading) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await api.agent(q));
    } catch (e) {
      setError(e instanceof Error ? e.message : "请求失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <section className="card">
        <h2 className="card-title">
          <Bot size={18} color="var(--color-primary)" />
          智能问答（Agent）
        </h2>
        <div className="field">
          <label htmlFor="question">问题（支持知识库问答与算术计算）</label>
          <input
            id="question"
            className="input"
            placeholder="例如：FAISS 的精确搜索索引叫什么？ / 计算 128 * 46"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask()}
          />
        </div>
        <div style={{ marginTop: "var(--space-3)", display: "flex", gap: "var(--space-2)" }}>
          <button className="btn btn-primary" onClick={ask} disabled={loading || !question.trim()}>
            <Send size={16} />
            {loading ? "思考中…" : "发送"}
          </button>
        </div>
        {error && <p className="error-text">{error}</p>}
      </section>

      {result && (
        <section className="card">
          <h2 className="card-title">
            <Search size={18} color="var(--color-accent)" />
            回答
          </h2>
          <p className="chat-answer">{result.answer}</p>
          <ul className="steps-list">
            {result.steps.map((s, i) => (
              <li key={i}>
                <Wrench size={12} />
                <span>
                  <span className="badge">{s.action}</span>{" "}
                  <span className="mono">{s.action_input.slice(0, 80)}</span>
                  {" -> "}
                  {s.observation.slice(0, 80)}
                </span>
              </li>
            ))}
          </ul>
          <p className="muted" style={{ marginTop: "var(--space-3)" }}>
            工具调用 {result.tool_calls} 次
          </p>
        </section>
      )}
    </>
  );
}
