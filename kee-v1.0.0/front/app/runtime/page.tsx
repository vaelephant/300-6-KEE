"use client";

import { useMemo, useState } from "react";
import { post } from "@/lib/api";

const MCP_SNIPPET = `{
  "mcpServers": {
    "kee": {
      "command": "/ABS/PATH/kee-v1.0.0/back/.venv/bin/python",
      "args": ["-m", "app.mcp"],
      "cwd": "/ABS/PATH/kee-v1.0.0/back",
      "env": {
        "DATABASE_URL": "sqlite+pysqlite:///./data/kee.db"
      }
    }
  }
}`;

const CURL_SNIPPET = `curl -sS http://127.0.0.1:8306/api/v1/runtime/agent \\
  -H 'Content-Type: application/json' \\
  -d '{"question":"…","top_k":6,"min_trust":0.45,"include_guarded":true}'`;

export default function Runtime() {
  const [q, setQ] = useState("");
  const [data, setData] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState<"mcp" | "curl" | null>(null);

  const pack = useMemo(() => data?.context_pack ?? data, [data]);

  async function run() {
    if (!q) return;
    setBusy(true);
    try {
      setData(
        await post("/runtime/agent", {
          question: q,
          top_k: 6,
          min_trust: 0.45,
          include_guarded: true,
        }),
      );
    } finally {
      setBusy(false);
    }
  }

  async function copy(kind: "mcp" | "curl", text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(kind);
      setTimeout(() => setCopied(null), 1600);
    } catch {
      /* ignore */
    }
  }

  return (
    <section className="content">
      <header>
        <div>
          <p className="eyebrow">ENGINE EGRESS</p>
          <h1>Agent 出口</h1>
          <p>MCP 插件 / HTTP 协议返回带引用、信任过滤的上下文包，供外部模型与 Agent 调用（不代答）。</p>
        </div>
      </header>
      <div className="redline" />

      <div className="egress-grid">
        <article className="panel egress-card">
          <div className="egress-card-head">
            <div>
              <small>MCP PLUGIN</small>
              <h2>kee_get_context</h2>
            </div>
            <button type="button" className="ghost" onClick={() => copy("mcp", MCP_SNIPPET)}>
              {copied === "mcp" ? "已复制" : "复制 mcp.json"}
            </button>
          </div>
          <p className="hint">挂到 Cursor / Claude Desktop 后，Agent 可直接调工具取 grounded pack。</p>
          <pre className="egress-code">{MCP_SNIPPET}</pre>
          <p className="hint">启动：<code>cd back && python -m app.mcp</code>（stdio）</p>
        </article>

        <article className="panel egress-card">
          <div className="egress-card-head">
            <div>
              <small>HTTP · kee-agent-context/1.0</small>
              <h2>POST /runtime/agent</h2>
            </div>
            <button type="button" className="ghost" onClick={() => copy("curl", CURL_SNIPPET)}>
              {copied === "curl" ? "已复制" : "复制 curl"}
            </button>
          </div>
          <p className="hint">返回 <code>protocol</code> + <code>instructions</code> + <code>context_pack</code>。</p>
          <pre className="egress-code">{CURL_SNIPPET}</pre>
        </article>
      </div>

      <h2 className="egress-demo-title">试用 Build Context</h2>
      <div className="search big" style={{ maxWidth: 720, border: "1px solid #e3e3e1", padding: "4px 4px 4px 12px", background: "#fafaf9" }}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder="Ask KEE…"
          style={{ flex: 1, border: 0, outline: "none", padding: 14, background: "transparent", fontSize: 14 }}
        />
        <button type="button" className="primary" onClick={run} disabled={busy}>
          Build Context
        </button>
      </div>
      {busy && <p className="hint" style={{ marginTop: 12 }}>Building grounded context…</p>}
      {pack && (
        <section style={{ marginTop: 28 }}>
          <article className="panel">
            <small>
              {data?.protocol ? `${data.protocol} · ` : ""}
              CONTEXT PACK · {pack.policy?.name}
              {pack.grounded === false ? " · insufficient evidence" : ""}
            </small>
            <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit", lineHeight: 1.7, marginTop: 12 }}>
              {pack.context || "No trusted context found."}
            </pre>
          </article>
          <h2 style={{ marginTop: 28, fontSize: 16 }}>Evidence & citations</h2>
          {(pack.citations || []).map((c: any) => (
            <div
              key={c.id}
              style={{
                display: "grid",
                gridTemplateColumns: "70px 1fr 100px",
                gap: 16,
                padding: "14px 0",
                borderBottom: "1px solid #eee",
                fontSize: 12,
              }}
            >
              <b style={{ color: "#a41414" }}>{c.id}</b>
              <span>
                {c.source} · v{c.version}
              </span>
              <span>{Math.round(c.trust_score * 100)} trust</span>
            </div>
          ))}
        </section>
      )}
    </section>
  );
}
