"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Minus, Plus, RotateCcw } from "lucide-react";
import { GraphNode, type GraphNodeData } from "./GraphNode";

type Edge = { source: string; target: string; predicate?: string };
type Pos = { x: number; y: number };

const MAX_NODES = 48;
const MAX_EDGES = 72;
const ZOOM_MIN = 0.35;
const ZOOM_MAX = 3.2;
const ZOOM_STEP = 1.18;

function clamp(n: number, a: number, b: number) {
  return Math.min(b, Math.max(a, n));
}

function targetLayout(n: number, i: number, w: number, h: number): Pos {
  const cx = w / 2;
  const cy = h / 2;
  const ring = Math.floor(i / 12);
  const inRing = i % 12;
  const count = Math.min(12, n - ring * 12);
  const radius = Math.min(w, h) * (0.18 + ring * 0.16);
  const ang = (inRing / Math.max(count, 1)) * Math.PI * 2 - Math.PI / 2;
  return {
    x: cx + Math.cos(ang) * radius + ((i * 17) % 11) - 5,
    y: cy + Math.sin(ang) * radius * 0.88 + ((i * 13) % 9) - 4,
  };
}

export function KnowledgeGraph({
  nodes = [],
  edges = [],
  className = "",
}: {
  nodes?: GraphNodeData[];
  edges?: Edge[];
  className?: string;
}) {
  const boxRef = useRef<HTMLDivElement>(null);
  const baseRef = useRef<Record<string, Pos>>({});
  const zoomRef = useRef(1);
  const panRef = useRef({ x: 0, y: 0 });
  const [size, setSize] = useState({ w: 800, h: 480 });
  const [pos, setPos] = useState<Record<string, Pos>>({});
  const [appear, setAppear] = useState<Record<string, number>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [burstDone, setBurstDone] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const drag = useRef<{
    id: string;
    ox: number;
    oy: number;
    sx: number;
    sy: number;
    moved: boolean;
  } | null>(null);
  const panDrag = useRef<{
    sx: number;
    sy: number;
    ox: number;
    oy: number;
    moved: boolean;
  } | null>(null);
  const pinned = useRef<Set<string>>(new Set());
  const suppressClick = useRef(false);

  const ns = useMemo(() => nodes.slice(0, MAX_NODES), [nodes]);
  const es = useMemo(() => {
    const ids = new Set(ns.map((n) => n.id));
    return edges
      .filter((e) => ids.has(e.source) && ids.has(e.target))
      .slice(0, MAX_EDGES);
  }, [edges, ns]);

  const selectedNode = ns.find((n) => n.id === selected) || null;

  useEffect(() => {
    zoomRef.current = zoom;
  }, [zoom]);
  useEffect(() => {
    panRef.current = pan;
  }, [pan]);

  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      const r = el.getBoundingClientRect();
      setSize({ w: r.width, h: r.height });
    });
    ro.observe(el);
    const r = el.getBoundingClientRect();
    setSize({ w: r.width, h: r.height });
    return () => ro.disconnect();
  }, []);

  const applyZoomAt = useCallback((nextZoom: number, mx: number, my: number) => {
    const z0 = zoomRef.current;
    const z1 = clamp(nextZoom, ZOOM_MIN, ZOOM_MAX);
    if (Math.abs(z1 - z0) < 0.001) return;
    const p0 = panRef.current;
    const worldX = (mx - p0.x) / z0;
    const worldY = (my - p0.y) / z0;
    const nextPan = { x: mx - worldX * z1, y: my - worldY * z1 };
    zoomRef.current = z1;
    panRef.current = nextPan;
    setZoom(z1);
    setPan(nextPan);
  }, []);

  const zoomBy = useCallback(
    (factor: number) => {
      const el = boxRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      applyZoomAt(zoomRef.current * factor, r.width / 2, r.height / 2);
    },
    [applyZoomAt],
  );

  const resetView = useCallback(() => {
    zoomRef.current = 1;
    panRef.current = { x: 0, y: 0 };
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  // burst from center
  useEffect(() => {
    if (!ns.length || size.w < 40) return;
    setBurstDone(false);
    resetView();
    const cx = size.w / 2;
    const cy = size.h / 2;
    const init: Record<string, Pos> = {};
    const ap0: Record<string, number> = {};
    ns.forEach((n) => {
      init[n.id] = { x: cx, y: cy };
      ap0[n.id] = 0;
    });
    baseRef.current = { ...init };
    setPos(init);
    setAppear(ap0);
    pinned.current = new Set();

    const targets = ns.map((n, i) => ({
      id: n.id,
      t: targetLayout(ns.length, i, size.w, size.h),
    }));

    const start = performance.now();
    const DUR = 950;
    let raf = 0;
    const step = (now: number) => {
      const u = Math.min(1, (now - start) / DUR);
      const ease = 1 - Math.pow(1 - u, 3);
      const p: Record<string, Pos> = {};
      const a: Record<string, number> = {};
      targets.forEach(({ id, t }, i) => {
        const delay = Math.min(0.4, i * 0.016);
        const local = Math.max(0, Math.min(1, (ease - delay) / Math.max(0.01, 1 - delay)));
        const e2 = 1 - Math.pow(1 - local, 2);
        p[id] = { x: cx + (t.x - cx) * e2, y: cy + (t.y - cy) * e2 };
        a[id] = e2;
      });
      baseRef.current = p;
      setPos(p);
      setAppear(a);
      if (u < 1) raf = requestAnimationFrame(step);
      else setBurstDone(true);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [ns, size.w, size.h, resetView]);

  // drift around base positions
  useEffect(() => {
    if (!burstDone || !ns.length) return;
    let raf = 0;
    const t0 = performance.now();
    const loop = (now: number) => {
      const t = (now - t0) / 1000;
      const next: Record<string, Pos> = {};
      ns.forEach((n, i) => {
        const base = baseRef.current[n.id];
        if (!base) return;
        if (pinned.current.has(n.id) || drag.current?.id === n.id) {
          next[n.id] = base;
          return;
        }
        next[n.id] = {
          x: base.x + Math.sin(t * 0.65 + i * 0.85) * 3.2,
          y: base.y + Math.cos(t * 0.5 + i * 1.05) * 2.6,
        };
      });
      setPos(next);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [burstDone, ns]);

  // wheel zoom (non-passive so we can prevent page scroll)
  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const factor = e.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP;
      // finer with trackpad
      const fine = Math.abs(e.deltaY) < 40;
      const f = fine ? (e.deltaY < 0 ? 1.06 : 1 / 1.06) : factor;
      applyZoomAt(zoomRef.current * f, mx, my);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [applyZoomAt]);

  const screenToWorld = useCallback((clientX: number, clientY: number) => {
    const el = boxRef.current;
    if (!el) return { x: 0, y: 0 };
    const rect = el.getBoundingClientRect();
    const z = zoomRef.current;
    const p = panRef.current;
    return {
      x: (clientX - rect.left - p.x) / z,
      y: (clientY - rect.top - p.y) / z,
    };
  }, []);

  const onPointerDown = useCallback(
    (id: string, e: React.PointerEvent) => {
      e.preventDefault();
      e.stopPropagation();
      const p = baseRef.current[id] || pos[id];
      if (!p) return;
      const w = screenToWorld(e.clientX, e.clientY);
      drag.current = {
        id,
        ox: w.x - p.x,
        oy: w.y - p.y,
        sx: e.clientX,
        sy: e.clientY,
        moved: false,
      };
      pinned.current.add(id);
      suppressClick.current = false;
    },
    [pos, screenToWorld],
  );

  const onBackgroundPointerDown = useCallback((e: React.PointerEvent) => {
    if (e.button !== 0) return;
    // only empty canvas — nodes stopPropagation
    panDrag.current = {
      sx: e.clientX,
      sy: e.clientY,
      ox: panRef.current.x,
      oy: panRef.current.y,
      moved: false,
    };
    suppressClick.current = false;
  }, []);

  useEffect(() => {
    const move = (e: PointerEvent) => {
      const nd = drag.current;
      if (nd) {
        if (Math.hypot(e.clientX - nd.sx, e.clientY - nd.sy) > 4) nd.moved = true;
        const w = (() => {
          const el = boxRef.current;
          if (!el) return { x: 0, y: 0 };
          const rect = el.getBoundingClientRect();
          const z = zoomRef.current;
          const p = panRef.current;
          return {
            x: (e.clientX - rect.left - p.x) / z,
            y: (e.clientY - rect.top - p.y) / z,
          };
        })();
        const x = w.x - nd.ox;
        const y = w.y - nd.oy;
        baseRef.current[nd.id] = { x, y };
        setPos((prev) => ({ ...prev, [nd.id]: { x, y } }));
        return;
      }
      const pd = panDrag.current;
      if (pd) {
        const dx = e.clientX - pd.sx;
        const dy = e.clientY - pd.sy;
        if (Math.hypot(dx, dy) > 4) pd.moved = true;
        const next = { x: pd.ox + dx, y: pd.oy + dy };
        panRef.current = next;
        setPan(next);
      }
    };
    const up = () => {
      if (drag.current?.moved || panDrag.current?.moved) suppressClick.current = true;
      drag.current = null;
      panDrag.current = null;
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
  }, []);

  const zoomPct = Math.round(zoom * 100);

  return (
    <div className={`graphstage ${className}`}>
      <div
        className="graphbox living interactive"
        ref={boxRef}
        onPointerDown={onBackgroundPointerDown}
        onClick={() => {
          if (suppressClick.current) {
            suppressClick.current = false;
            return;
          }
          setSelected(null);
        }}
      >
        <div
          className="graphworld"
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: "0 0",
          }}
        >
          <svg className="glines" width={size.w} height={size.h}>
            {es.map((e, idx) => {
              const a = pos[e.source];
              const b = pos[e.target];
              if (!a || !b) return null;
              const hi =
                selected && (e.source === selected || e.target === selected);
              return (
                <line
                  key={idx}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  className={hi ? "gline-svg hi" : "gline-svg"}
                />
              );
            })}
          </svg>

          {ns.map((n) => {
            const p = pos[n.id];
            if (!p) return null;
            return (
              <GraphNode
                key={n.id}
                data={n}
                x={p.x}
                y={p.y}
                selected={selected === n.id}
                appearProgress={appear[n.id] ?? 1}
                drifting={burstDone && !pinned.current.has(n.id)}
                onPointerDown={onPointerDown}
                onClick={(id) => {
                  if (suppressClick.current) {
                    suppressClick.current = false;
                    return;
                  }
                  setSelected(id);
                }}
              />
            );
          })}
        </div>

        {!ns.length && (
          <div className="graphempty">引擎尚无生效知识。从「摄入」进料后，关系会在此展开。</div>
        )}

        <div className="graphzoom" onPointerDown={(e) => e.stopPropagation()} onClick={(e) => e.stopPropagation()}>
          <button type="button" aria-label="放大" onClick={() => zoomBy(ZOOM_STEP)}>
            <Plus size={14} />
          </button>
          <span>{zoomPct}%</span>
          <button type="button" aria-label="缩小" onClick={() => zoomBy(1 / ZOOM_STEP)}>
            <Minus size={14} />
          </button>
          <button type="button" aria-label="重置视图" onClick={resetView} title="重置">
            <RotateCcw size={13} />
          </button>
        </div>

        {selectedNode && (
          <aside
            className="gdetail"
            onClick={(e) => e.stopPropagation()}
            onPointerDown={(e) => e.stopPropagation()}
          >
            <header>
              <small>{selectedNode.kind === "entity" ? "节点 · 实体" : "知识对象"}</small>
              <button type="button" className="outline" onClick={() => setSelected(null)}>
                关闭
              </button>
            </header>
            <h3>{selectedNode.label}</h3>
            <dl>
              <div>
                <dt>ID</dt>
                <dd>{selectedNode.id}</dd>
              </div>
              {selectedNode.kind === "knowledge" && (
                <>
                  <div>
                    <dt>状态</dt>
                    <dd>{selectedNode.status || "—"}</dd>
                  </div>
                  <div>
                    <dt>置信</dt>
                    <dd>
                      {selectedNode.confidence != null
                        ? `${Math.round(selectedNode.confidence * 100)}%`
                        : "—"}
                    </dd>
                  </div>
                  <div>
                    <dt>版本</dt>
                    <dd>v{selectedNode.version ?? "—"}</dd>
                  </div>
                  <div>
                    <dt>来源</dt>
                    <dd>{selectedNode.source || "—"}</dd>
                  </div>
                  {!!selectedNode.entities?.length && (
                    <div>
                      <dt>实体</dt>
                      <dd>{selectedNode.entities.join(" · ")}</dd>
                    </div>
                  )}
                </>
              )}
              {selectedNode.kind === "entity" && (
                <div>
                  <dt>名称</dt>
                  <dd>{selectedNode.name || selectedNode.label}</dd>
                </div>
              )}
              <div>
                <dt>关联</dt>
                <dd>
                  {
                    es.filter(
                      (e) =>
                        e.source === selectedNode.id || e.target === selectedNode.id,
                    ).length
                  }{" "}
                  条边
                </dd>
              </div>
            </dl>
            <p className="gdetail-note">引擎产物切片 · 完整上下文走 Agent 出口</p>
            {selectedNode.knowledge_id && (
              <a className="primary" href={`/knowledge/${selectedNode.knowledge_id}`}>
                打开详情
              </a>
            )}
          </aside>
        )}
      </div>
      <div className="graphlegend">
        <span>
          {nodes.length} 节点 · {edges.length} 边
        </span>
        <span>滚轮缩放 · 拖空白平移 · 拖节点</span>
      </div>
    </div>
  );
}
