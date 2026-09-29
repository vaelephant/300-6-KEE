"use client";

import { useEffect, useState } from "react";
import { get, post } from "@/lib/api";

export default function Review() {
  const [items, setItems] = useState<any[]>([]);
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
        {items.map((x: any) => (
          <article className="panel" key={x.id}>
            <small>
              REVIEW REQUIRED · v{x.version}
            </small>
            <h2>{x.content}</h2>
            <p>
              {x.source} · confidence {Math.round(x.confidence * 100)}%
            </p>
            <div className="actions">
              <button className="outline" type="button" onClick={() => act(x.id, "reject")}>
                Reject
              </button>
              <button className="primary" type="button" onClick={() => act(x.id, "approve")}>
                Approve
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
