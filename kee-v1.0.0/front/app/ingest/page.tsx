"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUpRight, FileUp, Loader2, Terminal } from "lucide-react";
import { get, post, upload, pollJob, type JobLog, type JobStatus } from "@/lib/api";

type LocalLog = JobLog & { id: string };

function nowIso() {
  return new Date().toISOString();
}

function fmtTime(ts?: string) {
  if (!ts) return "--:--:--";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts.slice(11, 19) || ts;
  return d.toLocaleTimeString("zh-CN", { hour12: false });
}

function phaseLabel(phase?: string | null, status?: string) {
  if (status === "failed") return "失败";
  if (status === "done") return "完成";
  switch (phase) {
    case "queued":
      return "排队";
    case "running":
      return "启动";
    case "extract":
      return "抽取";
    case "understand":
      return "理解";
    case "evolve":
      return "演化";
    case "done":
      return "完成";
    case "failed":
      return "失败";
    default:
      return status || "待命";
  }
}

export default function IngestPage() {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [filename, setFilename] = useState("");
  const [jobId, setJobId] = useState("");
  const [status, setStatus] = useState("idle");
  const [phase, setPhase] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [total, setTotal] = useState(0);
  const [logs, setLogs] = useState<LocalLog[]>([]);
  const [recent, setRecent] = useState<JobStatus[]>([]);
  const logEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function pushLocal(message: string, level: string = "info", p?: string) {
    setLogs((prev) => [
      ...prev,
      { id: `${Date.now()}-${prev.length}`, ts: nowIso(), level, phase: p, message },
    ]);
  }

  function applyJob(job: JobStatus) {
    setStatus(job.status);
    setPhase(job.phase ?? (job.detail?.phase as string) ?? null);
    setProgress(job.progress || 0);
    setTotal(job.total || 0);
    const remote = (job.logs || (job.detail?.logs as JobLog[]) || []).map((l, i) => ({
      ...l,
      id: `r-${l.ts || i}-${i}-${l.message.slice(0, 24)}`,
    }));
    if (remote.length) setLogs(remote);
  }

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  useEffect(() => {
    get("/jobs/?limit=8")
      .then((x) => setRecent(x.items || []))
      .catch(() => {});
  }, [status]);

  async function runUpload(file: File | null) {
    if (!file || busy) return;
    setBusy(true);
    setFilename(file.name);
    setJobId("");
    setStatus("uploading");
    setPhase("upload");
    setProgress(0);
    setTotal(0);
    setLogs([]);
    pushLocal(`选择文件 ${file.name}（${(file.size / 1024).toFixed(1)} KB）`, "info", "upload");
    try {
      const f = new FormData();
      f.append("file", file);
      f.append("domain", "general");
      pushLocal("上传到服务器…", "info", "upload");
      const x = await upload("/documents/upload", f);
      setJobId(x.job_id);
      setStatus("queued");
      setPhase("queued");
      pushLocal(`已入队 · job ${String(x.job_id).slice(0, 8)}…`, "info", "queued");
      const job = await pollJob(x.job_id, applyJob);
      applyJob(job);
      if (job.status === "failed" && job.error) {
        // remote log may already include the error; ensure UI ends on failed
        setStatus("failed");
        setPhase("failed");
      }
    } catch (e: unknown) {
      setStatus("failed");
      setPhase("failed");
      pushLocal(e instanceof Error ? e.message : "Upload failed", "error", "failed");
    } finally {
      setBusy(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function evolve() {
    if (!text.trim() || busy) return;
    setBusy(true);
    setFilename("quick-fact");
    setJobId("");
    setStatus("running");
    setPhase("understand");
    setProgress(0);
    setTotal(1);
    setLogs([]);
    pushLocal("提交单条事实…", "info", "upload");
    try {
      pushLocal("抽取实体与候选声明…", "info", "understand");
      const x = await post("/knowledge/evolve", {
        content: text,
        source: "kee-console",
        domain: "general",
      });
      setProgress(1);
      setTotal(1);
      setStatus("done");
      setPhase("done");
      const results = x.results || [];
      pushLocal(`理解完成 · ${results.length} 条候选`, "info", "understand");
      for (const r of results) {
        const decision = r.decision || "?";
        const conflicts = (r.conflicts || []).length;
        pushLocal(
          `演化 → ${decision}${conflicts ? ` · ${conflicts} 冲突` : ""}`,
          decision === "review_required" ? "warn" : "info",
          "evolve",
        );
      }
      pushLocal("已写入。可到工作台看知识资产，或审阅台处理冲突。", "info", "done");
      setText("");
    } catch (e: unknown) {
      setStatus("failed");
      setPhase("failed");
      pushLocal(e instanceof Error ? e.message : "Failed", "error", "failed");
    } finally {
      setBusy(false);
    }
  }

  const pct = total > 0 ? Math.min(100, Math.round((progress / total) * 100)) : busy ? 8 : 0;
  const live = busy || status === "queued" || status === "running" || status === "uploading";

  return (
    <section className="content narrow ingestpage">
      <header>
        <div>
          <p className="eyebrow">ENGINE FEED</p>
          <h1>摄入</h1>
          <p>多模态材料进入引擎：抽取 → 理解 → 演化，冲突进审阅台。</p>
        </div>
      </header>
      <div className="redline" />

      <div className="ingestgrid">
        <article className="panel">
          <small>DOCUMENT</small>
          <h2>上传材料</h2>
          <label
            className={`drop tall${dragOver ? " is-drag" : ""}${busy ? " is-busy" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              runUpload(e.dataTransfer.files?.[0] || null);
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.md,.pdf,.docx"
              disabled={busy}
              onChange={(e) => runUpload(e.target.files?.[0] || null)}
            />
            {busy && status !== "idle" && filename !== "quick-fact" ? (
              <>
                <Loader2 size={22} className="spin" />
                <b>{phaseLabel(phase, status)}中…</b>
                <small>{filename || "处理中"}</small>
              </>
            ) : (
              <>
                <FileUp size={22} />
                <b>{dragOver ? "松开即可上传" : "拖入或选择文件"}</b>
                <small>PDF · DOCX · TXT · MD · 20MB</small>
              </>
            )}
          </label>
        </article>
        <article className="panel">
          <small>QUICK FACT</small>
          <h2>粘贴事实</h2>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="一条可独立成立的陈述…"
            disabled={busy}
          />
          <button className="primary" type="button" onClick={evolve} disabled={busy || !text.trim()}>
            {busy && filename === "quick-fact" ? (
              <>
                <Loader2 size={14} className="spin" /> 写入中
              </>
            ) : (
              <>
                写入知识库 <ArrowUpRight size={14} />
              </>
            )}
          </button>
        </article>
      </div>

      <article className={`ingestconsole${live ? " is-live" : ""}`}>
        <header className="ingestconsole-head">
          <div>
            <Terminal size={14} />
            <b>处理过程</b>
            <span className={`ingest-pill status-${status}`}>{phaseLabel(phase, status)}</span>
          </div>
          <div className="ingestconsole-meta">
            {filename && <span>{filename}</span>}
            {jobId && <span title={jobId}>job {jobId.slice(0, 8)}</span>}
            {total > 0 && (
              <span>
                {progress}/{total}
              </span>
            )}
          </div>
        </header>

        <div className="ingestprogress" aria-hidden={!live && status === "idle"}>
          <div
            className={`ingestprogress-bar${live ? " is-active" : ""}${status === "failed" ? " is-fail" : ""}${status === "done" ? " is-done" : ""}`}
            style={{ width: `${status === "done" ? 100 : pct}%` }}
          />
        </div>

        <div className="ingestlog" role="log" aria-live="polite">
          {!logs.length && (
            <div className="ingestlog-empty">上传或写入后，这里会实时打印抽取 → 理解 → 演化各步状态。</div>
          )}
          {logs.map((l) => (
            <div key={l.id} className={`ingestlog-line level-${l.level || "info"}`}>
              <time>{fmtTime(l.ts)}</time>
              {l.phase && <em>{l.phase}</em>}
              <span>{l.message}</span>
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      </article>

      {recent.length > 0 && (
        <div className="ingestrecent">
          <small>RECENT JOBS</small>
          <ul>
            {recent.map((j) => (
              <li key={j.id || String(j.detail?.filename)}>
                <span className={`ingest-pill status-${j.status}`}>{j.status}</span>
                <b>{String(j.detail?.filename || j.kind || "job")}</b>
                <span>
                  {j.progress}/{j.total || "—"}
                </span>
                <span className="muted">{(j.detail?.claims as number) != null ? `${j.detail?.claims} claims` : j.phase || ""}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="hint" style={{ marginTop: 14 }}>
        完成后打开 <a href="/">工作台</a> 看知识资产，或去 <a href="/review">审阅台</a> 处理冲突。
      </p>
    </section>
  );
}
