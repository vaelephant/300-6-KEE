"use client";

import { useEffect, useState } from "react";
import { get, post } from "@/lib/api";

type ReviewItem = {
  id: string;
  content: string;
  source: string;
  confidence: number;
  version: number;
  status: string;
  created_at?: string;
  updated_at?: string;
};

function formatTime(value?: string) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function statusLabel(status: string) {
  if (status === "review_required") return "待审阅";
  if (status === "active") return "已生效";
  if (status === "rejected") return "已拒绝";
  return status.replaceAll("_", " ");
}

export default function Review() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  async function load() {
    const x = await get("/reviews");
    setItems(x.items || []);
  }
  useEffect(() => {
    load();
  }, []);
  async function act(id: string, action: string) {
    await post(`/knowledge/${id}/review`, { action });
    await load();
  }

  return (
    <section className="content">
      <header>
        <div>
          <p className="eyebrow">GOVERNANCE</p>
          <h1>审阅台</h1>
          <p>冲突或不确定的知识，确认后才会进入生效库。</p>
        </div>
      </header>
      <div className="redline" />
      <div className="reviewgrid">
        {items.map((x) => (
          <article className="panel reviewcard" key={x.id}>
            <div className="reviewcard-top">
              <span className="reviewcard-status">{statusLabel(x.status)}</span>
              <span className="reviewcard-ver">版本 v{x.version}</span>
            </div>

            <div className="reviewcard-block">
              <span className="reviewcard-label">知识内容</span>
              <h2>{x.content}</h2>
            </div>

            <dl className="reviewcard-meta">
              <div>
                <dt>来自文件</dt>
                <dd>{x.source || "—"}</dd>
              </div>
              <div>
                <dt>机器把握</dt>
                <dd>{Math.round(x.confidence * 100)}%</dd>
              </div>
              <div>
                <dt>生成时间</dt>
                <dd>{formatTime(x.created_at)}</dd>
              </div>
              <div>
                <dt>最近更新</dt>
                <dd>{formatTime(x.updated_at)}</dd>
              </div>
            </dl>

            <div className="actions">
              <button className="outline" type="button" onClick={() => act(x.id, "reject")}>
                拒绝
              </button>
              <button className="primary" type="button" onClick={() => act(x.id, "approve")}>
                通过
              </button>
            </div>
          </article>
        ))}
        {!items.length && (
          <article className="panel">
            <h2>队列清空</h2>
            <p>当前没有需要人工确认的知识。</p>
          </article>
        )}
      </div>
    </section>
  );
}
