"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { get } from "@/lib/api";
import { KnowledgeGraph } from "@/components/graph";

type View = "graph" | "store" | "vector" | "files";

type StoreItem = {
  id: string;
  content: string;
  source: string;
  status: string;
  confidence: number;
  version: number;
};

type FileItem = {
  id: string;
  filename: string;
  content_type: string;
  status: string;
  chunks: number;
  claims: number;
  job_id?: string;
  error?: string;
  created_at?: string;
};

type Assets = {
  store: {
    total: number;
    active: number;
    review_required: number;
    events: number;
    items: StoreItem[];
  };
  vector: {
    provider: string;
    model: string;
    base_url?: string | null;
    indexable: number;
    mode: string;
    note: string;
  };
  files: {
    total: number;
    done: number;
    failed: number;
    busy: number;
    items: FileItem[];
  };
  summary: {
    knowledge: number;
    active: number;
    review_required: number;
    documents: number;
    vector_indexable: number;
    embedding_provider: string;
  };
};

const VIEWS: { id: View; label: string }[] = [
  { id: "graph", label: "关系" },
  { id: "store", label: "库" },
  { id: "vector", label: "向量" },
  { id: "files", label: "文件" },
];

export default function Home() {
  const [view, setView] = useState<View>("graph");
  const [graph, setGraph] = useState<{ nodes: any[]; edges: any[] }>({
    nodes: [],
    edges: [],
  });
  const [assets, setAssets] = useState<Assets | null>(null);
  const [ready, setReady] = useState<{ ready?: boolean } | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setBusy(true);
    try {
      const [g, a, r] = await Promise.all([
        get("/graph?limit=100"),
        get("/system/assets?limit=12"),
        get("/runtime/readiness").catch(() => null),
      ]);
      setGraph({ nodes: g.nodes || [], edges: g.edges || [] });
      setAssets(a);
      setReady(r);
    } catch {
      /* ignore partial */
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 20000);
    return () => clearInterval(id);
  }, [refresh]);

  const s = assets?.summary;
  const engineOk = ready?.ready;

  return (
    <section className={`enginepage${view === "graph" ? " is-immersive" : ""}`}>
      <header className="enginehead">
        <h1>知识资产</h1>
        <div className="enginemetrics" aria-label="知识资产摘要">
          <button type="button" onClick={() => setView("store")}>
            <em>库</em>
            <strong>{s?.knowledge ?? "—"}</strong>
            <span>{s?.active ?? "—"} 生效</span>
          </button>
          <button type="button" onClick={() => setView("vector")}>
            <em>向量</em>
            <strong>{s?.vector_indexable ?? "—"}</strong>
            <span>{s?.embedding_provider || "—"}</span>
          </button>
          <button type="button" onClick={() => setView("files")}>
            <em>文件</em>
            <strong>{s?.documents ?? "—"}</strong>
            <span>
              {assets?.files.busy
                ? `${assets.files.busy} 处理中`
                : `${assets?.files.done ?? 0} 完成`}
            </span>
          </button>
          <a href="/review" className={s?.review_required ? "is-warn" : ""}>
            <em>待审</em>
            <strong>{s?.review_required ?? "—"}</strong>
            <span>{engineOk === false ? "异常" : engineOk ? "就绪" : "…"}</span>
          </a>
        </div>
        <div className="enginehead-actions">
          <nav className="engineviews" role="tablist">
            {VIEWS.map((v) => (
              <button
                key={v.id}
                type="button"
                role="tab"
                aria-selected={view === v.id}
                className={view === v.id ? "on" : ""}
                onClick={() => setView(v.id)}
              >
                {v.label}
              </button>
            ))}
          </nav>
          <button
            className="engine-refresh"
            type="button"
            onClick={refresh}
            disabled={busy}
            aria-label="刷新知识资产"
          >
            <RefreshCw size={13} className={busy ? "spin" : ""} />
          </button>
        </div>
      </header>

      <div className="enginestage">
        {view === "graph" && (
          <KnowledgeGraph nodes={graph.nodes} edges={graph.edges} className="enginegraph" />
        )}

        {view === "store" && (
          <div className="enginepanel">
            <div className="enginestats" aria-label="库统计">
              <div>
                <em>总计</em>
                <strong>{assets?.store.total ?? "—"}</strong>
              </div>
              <div>
                <em>生效</em>
                <strong>{assets?.store.active ?? "—"}</strong>
              </div>
              <div>
                <em>待审</em>
                <strong className={assets?.store.review_required ? "is-warn" : ""}>
                  {assets?.store.review_required ?? "—"}
                </strong>
              </div>
              <div>
                <em>演化事件</em>
                <strong>{assets?.store.events ?? "—"}</strong>
              </div>
            </div>
            <header>
              <h2>库</h2>
              <a href="/library">全部</a>
            </header>
            <ul className="assetlist">
              {(assets?.store.items || []).map((k) => (
                <li key={k.id}>
                  <a href={`/knowledge/${k.id}`}>
                    <b>{k.content}</b>
                    <span>
                      {k.status} · v{k.version} · {Math.round(k.confidence * 100)}%
                    </span>
                  </a>
                </li>
              ))}
              {!assets?.store.items?.length && (
                <li className="empty">库中尚无对象。从「摄入」进料。</li>
              )}
            </ul>
          </div>
        )}

        {view === "vector" && (
          <div className="enginepanel">
            <div className="enginestats" aria-label="向量统计">
              <div>
                <em>可检索</em>
                <strong>{assets?.vector.indexable ?? "—"}</strong>
              </div>
              <div>
                <em>Provider</em>
                <strong className="is-text">{assets?.vector.provider || "—"}</strong>
              </div>
              <div>
                <em>Model</em>
                <strong className="is-text">{assets?.vector.model || "—"}</strong>
              </div>
              <div>
                <em>模式</em>
                <strong className="is-text">
                  {assets?.vector.mode === "on_query" ? "即时嵌入" : assets?.vector.mode || "—"}
                </strong>
              </div>
            </div>
            <header>
              <h2>向量</h2>
              <a href="/system">配置</a>
            </header>
            <p className="engine-note">
              {assets?.vector.note} · 验效果走{" "}
              <a href="/search">检索</a> / <a href="/runtime">Agent 出口</a>
            </p>
          </div>
        )}

        {view === "files" && (
          <div className="enginepanel">
            <div className="enginestats" aria-label="文件统计">
              <div>
                <em>总计</em>
                <strong>{assets?.files.total ?? "—"}</strong>
              </div>
              <div>
                <em>完成</em>
                <strong>{assets?.files.done ?? "—"}</strong>
              </div>
              <div>
                <em>处理中</em>
                <strong>{assets?.files.busy ?? "—"}</strong>
              </div>
              <div>
                <em>失败</em>
                <strong className={assets?.files.failed ? "is-warn" : ""}>
                  {assets?.files.failed ?? "—"}
                </strong>
              </div>
            </div>
            <header>
              <h2>文件</h2>
              <a href="/ingest">摄入</a>
            </header>
            <ul className="assetlist">
              {(assets?.files.items || []).map((f) => (
                <li key={f.id}>
                  <div className="filerow">
                    <b>{f.filename}</b>
                    <em className={`filestatus status-${f.status}`}>{f.status}</em>
                    <span>
                      {f.chunks ? `${f.chunks} 块` : "—"}
                      {f.claims ? ` · ${f.claims} claims` : ""}
                    </span>
                    <time>
                      {f.created_at
                        ? new Date(f.created_at).toLocaleString("zh-CN", {
                            month: "2-digit",
                            day: "2-digit",
                            hour: "2-digit",
                            minute: "2-digit",
                            hour12: false,
                          })
                        : "—"}
                    </time>
                  </div>
                </li>
              ))}
              {!assets?.files.items?.length && (
                <li className="empty">尚无文件。PDF / DOCX / TXT / MD 从「摄入」进入。</li>
              )}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}
