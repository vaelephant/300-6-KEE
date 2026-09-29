"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ArrowUpRight,
  Cable,
  CircleAlert,
  CircleCheck,
  CircleDashed,
  Database,
  HardDrive,
  Network,
  RefreshCw,
  Sparkles,
  Workflow,
} from "lucide-react";
import { get, put, post } from "@/lib/api";

type LinkStatus = {
  id: string;
  name: string;
  role: string;
  status: string;
  latency_ms: number | null;
  target: string;
  detail?: string;
  engine?: string | null;
  enabled?: boolean;
  wired?: boolean;
};

type Readiness = {
  ready: boolean;
  checked_at?: string;
  mode?: string;
  database?: string;
  redis?: string;
  llm?: string;
  neo4j?: string;
  embedding_provider?: string;
  queue?: string;
  links?: LinkStatus[];
};

type ModelsConfig = {
  llm: { base_url: string; api_key: string; model: string; api_key_set?: boolean };
  embedding: {
    provider: string;
    model: string;
    base_url: string;
    api_key: string;
    api_key_set?: boolean;
  };
  reranker: { model: string };
};

const ROLE_ICON: Record<string, typeof Database> = {
  runtime: Workflow,
  store: Database,
  graph: Network,
  cache: HardDrive,
  ai: Sparkles,
};

function statusKind(status: string) {
  if (["connected", "configured", "postgres", "sqlite"].includes(status)) return "ok";
  if (["fallback", "optional"].includes(status)) return "warn";
  if (status.startsWith("error")) return "error";
  return "warn";
}

function StatusGlyph({ kind }: { kind: string }) {
  if (kind === "ok") return <CircleCheck size={16} />;
  if (kind === "error") return <CircleAlert size={16} />;
  return <CircleDashed size={16} />;
}

export default function SystemLinksPage() {
  const [data, setData] = useState<Readiness | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [frontLatency, setFrontLatency] = useState<number | null>(null);
  const [models, setModels] = useState<ModelsConfig | null>(null);
  const [llmKey, setLlmKey] = useState("");
  const [embKey, setEmbKey] = useState("");
  const [modelMsg, setModelMsg] = useState("");
  const [modelBusy, setModelBusy] = useState(false);
  const [llmCatalog, setLlmCatalog] = useState<string[]>([]);
  const [embCatalog, setEmbCatalog] = useState<string[]>([]);

  const refresh = useCallback(async () => {
    setBusy(true);
    setError("");
    const t0 = performance.now();
    try {
      const r = (await get("/runtime/readiness")) as Readiness;
      setFrontLatency(Math.round(performance.now() - t0));
      setData(r);
    } catch (e: unknown) {
      setData(null);
      setError(e instanceof Error ? e.message : "Failed to reach API");
    } finally {
      setBusy(false);
    }
  }, []);

  const loadModels = useCallback(async () => {
    try {
      const m = (await get("/system/models")) as ModelsConfig;
      setModels(m);
      setLlmKey("");
      setEmbKey("");
    } catch (e: unknown) {
      setModelMsg(e instanceof Error ? e.message : "Failed to load models");
    }
  }, []);

  useEffect(() => {
    refresh();
    loadModels();
    const id = setInterval(refresh, 15000);
    return () => clearInterval(id);
  }, [refresh, loadModels]);

  async function saveModels() {
    if (!models) return;
    setModelBusy(true);
    setModelMsg("Saving…");
    try {
      const body: Record<string, unknown> = {
        llm: {
          base_url: models.llm.base_url,
          model: models.llm.model,
          ...(llmKey ? { api_key: llmKey } : {}),
        },
        embedding: {
          provider: models.embedding.provider,
          model: models.embedding.model,
          base_url: models.embedding.base_url,
          ...(embKey ? { api_key: embKey } : {}),
        },
        reranker: { model: models.reranker.model },
      };
      const m = (await put("/system/models", body)) as ModelsConfig;
      setModels(m);
      setLlmKey("");
      setEmbKey("");
      setModelMsg("Saved to data/model_settings.json");
      await refresh();
    } catch (e: unknown) {
      setModelMsg(e instanceof Error ? e.message : "Save failed");
    } finally {
      setModelBusy(false);
    }
  }

  async function testTarget(target: "llm" | "embedding") {
    setModelBusy(true);
    setModelMsg(`Testing ${target}…`);
    try {
      const r = await post("/system/models/test", { target });
      setModelMsg(
        r.ok
          ? `${target} ok` + (r.reply ? `: ${r.reply}` : r.dims ? ` · dims ${r.dims}` : "")
          : `${target} failed: ${r.error}`,
      );
    } catch (e: unknown) {
      setModelMsg(e instanceof Error ? e.message : "Test failed");
    } finally {
      setModelBusy(false);
    }
  }

  async function listRemote(target: "llm" | "embedding") {
    if (!models) return;
    setModelBusy(true);
    setModelMsg(`Listing ${target} models…`);
    try {
      const body =
        target === "llm"
          ? {
              target,
              base_url: models.llm.base_url,
              ...(llmKey ? { api_key: llmKey } : {}),
            }
          : {
              target,
              base_url: models.embedding.base_url || models.llm.base_url,
              ...(embKey || llmKey ? { api_key: embKey || llmKey } : {}),
            };
      const r = await post("/system/models/list", body);
      if (!r.ok) {
        setModelMsg(`${target} list failed: ${r.error}`);
        return;
      }
      const ids: string[] = r.models || [];
      if (target === "llm") {
        setLlmCatalog(ids);
        if (ids.length && !ids.includes(models.llm.model)) {
          setModels({ ...models, llm: { ...models.llm, model: ids[0] } });
        }
      } else {
        setEmbCatalog(ids);
        if (ids.length && !ids.includes(models.embedding.model)) {
          setModels({
            ...models,
            embedding: { ...models.embedding, model: ids[0], provider: "openai_compatible" },
          });
        }
      }
      setModelMsg(`${target}: ${ids.length} models from ${r.source || "provider"}`);
    } catch (e: unknown) {
      setModelMsg(e instanceof Error ? e.message : "List failed");
    } finally {
      setModelBusy(false);
    }
  }

  const links = data?.links ?? [];
  const okCount = links.filter((l) => statusKind(l.status) === "ok").length;
  const errCount = links.filter((l) => statusKind(l.status) === "error").length;
  const warnCount = links.filter((l) => statusKind(l.status) === "warn").length;

  return (
    <section className="content systempage">
        <header>
          <div>
            <p className="eyebrow">INFRASTRUCTURE</p>
            <h1>系统与模型</h1>
            <p>连通探测 · LLM / Embedding 配置 · 队列状态</p>
          </div>
          <div className="headeractions">
            <button className="outline" onClick={refresh} disabled={busy}>
              <RefreshCw size={14} className={busy ? "spin" : ""} /> Probe
            </button>
          </div>
        </header>
        <div className="redline" />

        <section className="cards statuscards">
          <article>
            <Cable size={17} />
            <span>Overall</span>
            <strong className={data?.ready ? "oktext" : "errtext"}>
              {error ? "DOWN" : data?.ready ? "READY" : "…"}
            </strong>
            <small>{data?.mode || "awaiting probe"}</small>
          </article>
          <article>
            <CircleCheck size={17} />
            <span>Healthy</span>
            <strong>{okCount}</strong>
            <small>connected / configured</small>
          </article>
          <article>
            <CircleDashed size={17} />
            <span>Degraded</span>
            <strong>{warnCount}</strong>
            <small>fallback / optional</small>
          </article>
          <article>
            <CircleAlert size={17} />
            <span>Failed</span>
            <strong className={errCount ? "errtext" : ""}>{errCount}</strong>
            <small>probe errors</small>
          </article>
        </section>

        {error && (
          <div className="linkbanner error">
            <CircleAlert size={16} />
            <div>
              <b>Frontend → API 失败</b>
              <span>{error}</span>
            </div>
          </div>
        )}

        <section className="topology">
          <div className="panelhead">
            <div>
              <small>TOPOLOGY</small>
              <h2>Request path</h2>
            </div>
            <span className="live">
              <i /> LIVE
            </span>
          </div>
          <div className="topline">
            {[
              { label: "Browser", sub: "localhost:3030" },
              { label: "Next rewrite", sub: "/api/v1 → :8306" },
              { label: "KEE API", sub: data?.ready ? "ok" : "…" },
              { label: "Queue", sub: data?.queue || "Redis/arq" },
            ].map((n, i) => (
              <div className="topnode" key={n.label}>
                <em>0{i + 1}</em>
                <b>{n.label}</b>
                <span>{n.sub}</span>
                {i < 3 && <i className="connector" />}
              </div>
            ))}
          </div>
          <div className="topmeta">
            <span>
              Front RTT <b>{frontLatency != null ? `${frontLatency} ms` : "—"}</b>
            </span>
            <span>
              Checked{" "}
              <b>
                {data?.checked_at
                  ? new Date(data.checked_at).toLocaleString()
                  : "—"}
              </b>
            </span>
          </div>
        </section>

        <section className="modelform panel">
          <div className="panelhead">
            <div>
              <small>MODELS</small>
              <h2>LLM & Embedding</h2>
            </div>
<span className="hint">{modelMsg || "填 Base URL + Key → List models → 下拉选择 → Save。"}</span>
          </div>
          {models ? (
            <div className="modelfields">
              <div className="modcol">
                <b>LLM (OpenAI-compatible)</b>
                <label>
                  Base URL
                  <input
                    value={models.llm.base_url}
                    onChange={(e) =>
                      setModels({ ...models, llm: { ...models.llm, base_url: e.target.value } })
                    }
                    placeholder="http://127.0.0.1:11434/v1"
                  />
                </label>
                <label>
                  API Key {models.llm.api_key_set ? `(set: ${models.llm.api_key})` : "(not set)"}
                  <input
                    type="password"
                    value={llmKey}
                    onChange={(e) => setLlmKey(e.target.value)}
                    placeholder="leave blank to keep saved key"
                  />
                </label>
                <div className="modrow">
                  <button
                    className="outline"
                    type="button"
                    disabled={modelBusy || !models.llm.base_url}
                    onClick={() => listRemote("llm")}
                  >
                    List models
                  </button>
                  <button className="outline" type="button" disabled={modelBusy} onClick={() => testTarget("llm")}>
                    Test LLM
                  </button>
                </div>
                <label>
                  Model
                  {llmCatalog.length > 0 ? (
                    <select
                      value={llmCatalog.includes(models.llm.model) ? models.llm.model : ""}
                      onChange={(e) =>
                        setModels({ ...models, llm: { ...models.llm, model: e.target.value } })
                      }
                    >
                      {!llmCatalog.includes(models.llm.model) && models.llm.model && (
                        <option value={models.llm.model}>{models.llm.model} (current)</option>
                      )}
                      {llmCatalog.map((id) => (
                        <option key={id} value={id}>
                          {id}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      value={models.llm.model}
                      onChange={(e) =>
                        setModels({ ...models, llm: { ...models.llm, model: e.target.value } })
                      }
                      placeholder="先填 URL/Key，点 List models"
                    />
                  )}
                </label>
                {llmCatalog.length > 0 && (
                  <label>
                    Or type model id
                    <input
                      value={models.llm.model}
                      onChange={(e) =>
                        setModels({ ...models, llm: { ...models.llm, model: e.target.value } })
                      }
                    />
                  </label>
                )}
              </div>
              <div className="modcol">
                <b>Embedding</b>
                <label>
                  Provider
                  <select
                    value={models.embedding.provider}
                    onChange={(e) =>
                      setModels({
                        ...models,
                        embedding: { ...models.embedding, provider: e.target.value },
                      })
                    }
                  >
                    <option value="local">local (hash)</option>
                    <option value="bge">bge (sentence-transformers)</option>
                    <option value="openai_compatible">openai_compatible</option>
                  </select>
                </label>
                <label>
                  Base URL (openai_compatible)
                  <input
                    value={models.embedding.base_url}
                    onChange={(e) =>
                      setModels({
                        ...models,
                        embedding: { ...models.embedding, base_url: e.target.value },
                      })
                    }
                    placeholder="空则用 LLM 的 URL"
                  />
                </label>
                <label>
                  API Key {models.embedding.api_key_set ? `(set: ${models.embedding.api_key})` : ""}
                  <input
                    type="password"
                    value={embKey}
                    onChange={(e) => setEmbKey(e.target.value)}
                    placeholder="leave blank to keep"
                  />
                </label>
                <div className="modrow">
                  <button
                    className="outline"
                    type="button"
                    disabled={modelBusy || !(models.embedding.base_url || models.llm.base_url)}
                    onClick={() => listRemote("embedding")}
                  >
                    List models
                  </button>
                  <button
                    className="outline"
                    type="button"
                    disabled={modelBusy}
                    onClick={() => testTarget("embedding")}
                  >
                    Test Embedding
                  </button>
                </div>
                <label>
                  Model
                  {embCatalog.length > 0 ? (
                    <select
                      value={embCatalog.includes(models.embedding.model) ? models.embedding.model : ""}
                      onChange={(e) =>
                        setModels({
                          ...models,
                          embedding: {
                            ...models.embedding,
                            model: e.target.value,
                            provider: "openai_compatible",
                          },
                        })
                      }
                    >
                      {!embCatalog.includes(models.embedding.model) && models.embedding.model && (
                        <option value={models.embedding.model}>
                          {models.embedding.model} (current)
                        </option>
                      )}
                      {embCatalog.map((id) => (
                        <option key={id} value={id}>
                          {id}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      value={models.embedding.model}
                      onChange={(e) =>
                        setModels({
                          ...models,
                          embedding: { ...models.embedding, model: e.target.value },
                        })
                      }
                      placeholder="BAAI/bge-m3 or nomic-embed-text"
                    />
                  )}
                </label>
                <label>
                  Reranker model (stored)
                  <input
                    value={models.reranker.model}
                    onChange={(e) =>
                      setModels({
                        ...models,
                        reranker: { ...models.reranker, model: e.target.value },
                      })
                    }
                  />
                </label>
              </div>
            </div>
          ) : (
            <div className="empty">Loading model settings…</div>
          )}
          <div className="modactions">
            <button className="primary" disabled={modelBusy || !models} onClick={saveModels}>
              Save models
            </button>
            <button className="outline" disabled={modelBusy} onClick={loadModels}>
              Reload
            </button>
          </div>
        </section>

        <section className="linkgrid">
          {links.map((link) => {
            const kind = statusKind(link.status);
            const Icon = ROLE_ICON[link.role] || Cable;
            return (
              <article key={link.id} className={`linkcard ${kind}`}>
                <div className="linkhead">
                  <div className="linktitle">
                    <Icon size={18} />
                    <div>
                      <b>{link.name}</b>
                      <small>{link.role}</small>
                    </div>
                  </div>
                  <span className={`pill ${kind}`}>
                    <StatusGlyph kind={kind} />
                    {link.status}
                  </span>
                </div>
                <dl>
                  <div>
                    <dt>Target</dt>
                    <dd>{link.target || "—"}</dd>
                  </div>
                  <div>
                    <dt>Detail</dt>
                    <dd>{link.detail || "—"}</dd>
                  </div>
                  <div>
                    <dt>Latency</dt>
                    <dd>
                      {link.latency_ms == null ? "—" : `${link.latency_ms} ms`}
                    </dd>
                  </div>
                </dl>
                {link.id === "redis" && link.wired && (
                  <p className="linknote">arq 文档摄入队列已接入；需另起 worker 进程消费。</p>
                )}
                {link.id === "redis" && link.wired === false && (
                  <p className="linknote">Redis 未连通；上传会返回 503。</p>
                )}
                {link.id === "embedding" && (link.engine === "local" || link.target === "local-hash") && (
                  <p className="linknote">本地 hash；可在上方改为 bge 或 openai_compatible。</p>
                )}
                {link.id === "embedding" && link.engine === "openai_compatible" && (
                  <p className="linknote">provider · openai_compatible</p>
                )}
              </article>
            );
          })}
          {!links.length && !error && (
            <div className="empty pad">Probing system links…</div>
          )}
        </section>
    </section>
  );
}
