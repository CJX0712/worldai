// Author: 晨星
import { useState } from "react";
import { Database, FileText, BarChart3, MessageSquare } from "lucide-react";
import ChatPage from "./pages/ChatPage";
import DocsPage from "./pages/DocsPage";
import EvalPage from "./pages/EvalPage";

type Tab = "chat" | "docs" | "eval";

const TABS: Array<{ id: Tab; label: string; icon: typeof MessageSquare }> = [
  { id: "chat", label: "问答", icon: MessageSquare },
  { id: "docs", label: "文档库", icon: FileText },
  { id: "eval", label: "评测", icon: BarChart3 },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("chat");
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <Database size={20} color="var(--color-primary)" />
          WorldAI
        </div>
        <span className="tagline">本地优先 RAG 与 Agent 平台</span>
        <nav className="nav-tabs">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={`nav-tab ${tab === id ? "active" : ""}`}
              onClick={() => setTab(id)}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </nav>
      </header>
      <main className="page">
        {tab === "chat" && <ChatPage />}
        {tab === "docs" && <DocsPage />}
        {tab === "eval" && <EvalPage />}
      </main>
    </div>
  );
}
