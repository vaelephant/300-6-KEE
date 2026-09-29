"use client";

import { useRef, useState } from "react";
import { Loader2, Search } from "lucide-react";
import { post } from "@/lib/api";

type Hit = {
  score: number;
  knowledge: {
    id: string;
    content: string;
    source: string;
    version: number;
    confidence: number;
  };
};

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [result, setResult] = useState<Hit[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);
  const [shake, setShake] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function query() {
    const question = q.trim();
    if (!question) {
      setShake(false);
      requestAnimationFrame(() => setShake(true));
      inputRef.current?.focus();
      return;
    }
    setBusy(true);
    setError("");
    setSearched(true);
    try {
      const x = await post("/knowledge/query", { question, top_k: 12 });
      setResult(x.results || []);
    } catch (e: unknown) {
      setResult([]);
      setError(e instanceof Error ? e.message : "检索失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="content narrow searchpage">
      <header>
        <div>
          <p className="eyebrow">ENGINE QUERY</p>
          <h1>检索</h1>
          <p>在引擎生效知识中验证内容。需要带引用的上下文包，请用 Agent 出口。</p>
        </div>
      </header>
      <div className="redline" />

      <div
        className={`searchbar${busy ? " is-busy" : ""}${shake ? " is-shake" : ""}`}
        onAnimationEnd={() => setShake(false)}
      >
        <Search size={17} className="searchbar-icon" />
        <input
          ref={inputRef}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && query()}
          placeholder="向知识库提问…"
          disabled={busy}
          aria-label="检索问题"
        />
        <button type="button" className="searchbar-go" onClick={query} disabled={busy}>
          {busy ? (
            <>
              <Loader2 size={14} className="spin" />
              检索中
            </>
          ) : (
            "检索"
          )}
        </button>
        {busy && <span className="searchbar-progress" aria-hidden />}
      </div>

      <div className="searchmeta" aria-live="polite">
        {busy && <span className="searchmeta-busy">正在匹配知识…</span>}
        {!busy && error && <span className="searchmeta-err">{error}</span>}
        {!busy && !error && searched && (
          <span>
            {result.length ? `${result.length} 条相关结果` : "没有匹配到知识"}
          </span>
        )}
      </div>

      <div className={`results${busy ? " is-loading" : ""}`}>
        {busy && (
          <div className="searchskel" aria-hidden>
            {[0, 1, 2].map((i) => (
              <div key={i} className="searchskel-row" style={{ animationDelay: `${i * 80}ms` }}>
                <i />
                <div>
                  <b />
                  <small />
                </div>
              </div>
            ))}
          </div>
        )}

        {!busy &&
          result.map((r, i) => (
            <a
              className="result reveal"
              key={r.knowledge.id}
              href={`/knowledge/${r.knowledge.id}`}
              style={{ animationDelay: `${i * 55}ms` }}
            >
              <span className="score">{Math.round(r.score * 100)}</span>
              <div>
                <b>{r.knowledge.content}</b>
                <small>
                  {r.knowledge.source} · v{r.knowledge.version} ·{" "}
                  {Math.round(r.knowledge.confidence * 100)}%
                </small>
              </div>
            </a>
          ))}

        {!busy && !result.length && !error && (
          <div className={`empty${searched ? " empty-done" : ""}`}>
            {searched ? "换个问法，或先去「摄入」写入知识。" : "输入问题后检索。结果按相关度排序。"}
          </div>
        )}
      </div>
    </section>
  );
}
