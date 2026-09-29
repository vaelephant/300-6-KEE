"use client";

export type GraphNodeData = {
  id: string;
  label: string;
  kind?: string;
  status?: string;
  confidence?: number;
  version?: number;
  source?: string;
  content?: string;
  knowledge_id?: string;
  name?: string;
  entities?: string[];
};

type Props = {
  data: GraphNodeData;
  x: number;
  y: number;
  selected?: boolean;
  appearProgress: number;
  drifting?: boolean;
  onPointerDown: (id: string, e: React.PointerEvent) => void;
  onClick: (id: string) => void;
};

/** Independent graph node: burst-in scale, drag handle, click for details. */
export function GraphNode({
  data,
  x,
  y,
  selected,
  appearProgress,
  drifting,
  onPointerDown,
  onClick,
}: Props) {
  const kind = data.kind || "knowledge";
  const short =
    data.label.length > 18 ? data.label.slice(0, 16) + "…" : data.label;

  return (
    <button
      type="button"
      className={[
        "gn",
        `gn-${kind}`,
        selected ? "is-selected" : "",
        drifting ? "is-drift" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      style={{
        left: x,
        top: y,
        opacity: Math.min(1, appearProgress * 1.2),
        transform: `translate(-50%, -50%) scale(${0.35 + appearProgress * 0.65})`,
      }}
      onPointerDown={(e) => onPointerDown(data.id, e)}
      onClick={(e) => {
        e.stopPropagation();
        onClick(data.id);
      }}
      title={data.label}
    >
      <span className="gn-dot" />
      <span className="gn-label">{short}</span>
    </button>
  );
}
