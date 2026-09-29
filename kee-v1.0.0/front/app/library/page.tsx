"use client";

import { useEffect, useState } from "react";
import { get } from "@/lib/api";

type K = {
  id: string;
  content: string;
  source: string;
  confidence: number;
  version: number;
  status: string;
};

export default function LibraryPage() {
  const [items, setItems] = useState<K[]>([]);
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    Promise.all([get("/knowledge?limit=50"), get("/system/stats")]).then(([k, s]) => {
      setItems(k.items || []);
      setStats(s);
    });
  }, []);

  return (
    <section className="content">
      <header>
        <div>
          <p className="eyebrow">LIBRARY</p>
          <h1>知识库</h1>
          <p>
            最近对象 · 共 {stats?.total ?? "—"} 条 · 生效 {stats?.active ?? "—"} · 待审{" "}
            {stats?.review_required ?? "—"}
          </p>
        </div>
      </header>
      <div className="redline" />
      <div className="knowledge" style={{ marginTop: 0 }}>
        <div className="table">
          <div className="tr head">
            <span>KNOWLEDGE</span>
            <span>STATUS</span>
            <span>VERSION</span>
            <span>CONFIDENCE</span>
          </div>
          {items.map((k) => (
            <div className="tr" key={k.id}>
              <span>
                <a href={`/knowledge/${k.id}`}>
                  <b>{k.content}</b>
                </a>
                <small>{k.source}</small>
              </span>
              <span>
                <i className={`status ${k.status}`} />
                {k.status}
                {k.status === "review_required" && (
                  <a className="reviewlink" href="/review">
                    Review
                  </a>
                )}
              </span>
              <span>v{k.version}</span>
              <span>{Math.round(k.confidence * 100)}%</span>
            </div>
          ))}
          {!items.length && <div className="empty pad">还没有知识。先去「摄入」。</div>}
        </div>
      </div>
    </section>
  );
}
