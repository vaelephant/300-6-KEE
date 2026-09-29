"use client";

import { useEffect, useState } from "react";
import { get } from "@/lib/api";

export default function Detail({ params }: { params: Promise<{ id: string }> }) {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    params.then((p) => get(`/knowledge/${p.id}`).then(setData));
  }, [params]);

  if (!data) {
    return (
      <section className="content">
        <p className="empty">Loading knowledge…</p>
      </section>
    );
  }

  const k = data.knowledge;
  return (
    <section className="content">
      <p className="eyebrow">KNOWLEDGE OBJECT</p>
      <h1 style={{ fontSize: 28, maxWidth: 900 }}>{k.content}</h1>
      <div className="meta">
        <span>{k.status}</span>
        <span>v{k.version}</span>
        <span>{Math.round(k.confidence * 100)}% confidence</span>
        <span>{k.source}</span>
      </div>
      <section className="detailgrid">
        <article className="panel">
          <small>ENTITIES</small>
          <h2>Semantic structure</h2>
          <div className="chips">
            {(k.entities || []).map((x: string) => (
              <span key={x}>{x}</span>
            ))}
          </div>
          <pre>{JSON.stringify(k.relations || [], null, 2)}</pre>
        </article>
        <article className="panel">
          <small>PROVENANCE</small>
          <h2>Evidence trail</h2>
          <pre>{JSON.stringify(data.provenance, null, 2)}</pre>
        </article>
        <article className="panel span2">
          <small>EVOLUTION</small>
          <h2>Version history</h2>
          <div className="versionline">
            {(data.history || []).map((v: any) => (
              <div key={`${v.version}-${v.created_at}`}>
                <b>v{v.version}</b>
                <span>{v.reason}</span>
                <small>
                  {v.status} · {Math.round(v.confidence * 100)}%
                </small>
              </div>
            ))}
          </div>
        </article>
      </section>
    </section>
  );
}
