// Author: 晨星
// Typed API client for the WorldAI backend. Uniform envelope {code,data,message}.
const BASE = "/api/v1";

export interface Envelope<T> {
  code: number;
  data: T;
  message: string;
}

export interface Health {
  status: string;
}
export interface Stats {
  documents: number;
  chunks: number;
}
export interface DocInfo {
  id: string;
  title: string;
  chars: string;
}
export interface DocCreated {
  doc_id: string;
  title: string;
  chunks: number;
}
export interface Citation {
  chunk_id: string;
  doc_id: string;
  snippet: string;
  score: number;
}
export interface QueryResult {
  question: string;
  answer: string;
  provider: string;
  retrieval_mode: string;
  citations: Citation[];
}
export interface AgentStep {
  thought: string;
  action: string;
  action_input: string;
  observation: string;
}
export interface AgentResult {
  question: string;
  answer: string;
  steps: AgentStep[];
  tool_calls: number;
}
export interface EvalReport {
  aggregate: Record<string, number>;
  details: Array<{
    question: string;
    answer: string;
    ranked_doc_ids: string[];
    metrics: Record<string, number>;
  }>;
}
export interface Trace {
  dense_order: string[];
  bm25_order: string[];
  rerank_order: string[];
  fused_order: string[];
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      detail = body.detail ?? detail;
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }
  const env = (await resp.json()) as Envelope<T>;
  if (env.code !== 0) throw new Error(env.message);
  return env.data;
}

export const api = {
  health: () => req<Health>("/health"),
  stats: () => req<Stats>("/stats"),
  listDocs: () => req<DocInfo[]>("/documents"),
  uploadDoc: (title: string, text: string) =>
    req<DocCreated>("/documents", {
      method: "POST",
      body: JSON.stringify({ title, text }),
    }),
  query: (question: string, topK = 5) =>
    req<QueryResult>("/query", {
      method: "POST",
      body: JSON.stringify({ question, top_k: topK }),
    }),
  agent: (question: string) =>
    req<AgentResult>("/agent", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
  evaluate: (topK = 3) =>
    req<EvalReport>("/eval", {
      method: "POST",
      body: JSON.stringify({ top_k: topK }),
    }),
  trace: (question: string) =>
    req<Trace>(`/trace?question=${encodeURIComponent(question)}`),
};
