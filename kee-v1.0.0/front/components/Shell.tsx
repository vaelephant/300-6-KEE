"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import {
  Cable,
  FileUp,
  GitBranch,
  Home,
  Library,
  Search,
  Sparkles,
} from "lucide-react";
import { get } from "@/lib/api";
import { ThemeToggle } from "@/components/theme-toggle";

type NavItem = {
  href: string;
  label: string;
  icon: typeof Home;
  match: (p: string) => boolean;
  badge?: "review";
};

type NavGroup = { title?: string; items: NavItem[] };

const GROUPS: NavGroup[] = [
  {
    items: [
      { href: "/", label: "工作台", icon: Home, match: (p) => p === "/" },
    ],
  },
  {
    title: "进料",
    items: [
      {
        href: "/ingest",
        label: "摄入",
        icon: FileUp,
        match: (p) => p.startsWith("/ingest"),
      },
      {
        href: "/search",
        label: "检索",
        icon: Search,
        match: (p) => p.startsWith("/search"),
      },
      {
        href: "/library",
        label: "知识库",
        icon: Library,
        match: (p) => p.startsWith("/library") || p.startsWith("/knowledge/"),
      },
    ],
  },
  {
    title: "治理",
    items: [
      {
        href: "/review",
        label: "审阅台",
        icon: GitBranch,
        match: (p) => p.startsWith("/review"),
        badge: "review",
      },
    ],
  },
  {
    title: "出口",
    items: [
      {
        href: "/runtime",
        label: "Agent 出口",
        icon: Sparkles,
        match: (p) => p.startsWith("/runtime"),
      },
      {
        href: "/system",
        label: "系统与模型",
        icon: Cable,
        match: (p) => p.startsWith("/system"),
      },
    ],
  },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "/";
  const [reviewCount, setReviewCount] = useState(0);
  const [ready, setReady] = useState<{
    ready?: boolean;
    database?: string;
    llm?: string;
    embedding_model?: string;
    embedding_provider?: string;
  } | null>(null);

  useEffect(() => {
    let alive = true;
    async function probe() {
      try {
        const [s, r] = await Promise.all([
          get("/system/stats"),
          get("/runtime/readiness"),
        ]);
        if (!alive) return;
        setReviewCount(s?.review_required ?? 0);
        setReady(r);
      } catch {
        if (alive) setReady(null);
      }
    }
    probe();
    const id = setInterval(probe, 20000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [pathname]);

  return (
    <div className="shell">
      <aside className="appside">
        <a className="brand" href="/" aria-label="KEE Evolution Engine">
          <span className="mark" aria-hidden>
            <span>K</span>
          </span>
          <div>
            <span className="brand-name">KEE科室版</span>
            <small>Evolution Engine</small>
          </div>
        </a>
        <nav className="groupednav">
          {GROUPS.map((g, gi) => (
            <div className="navgroup" key={gi}>
              {g.title && <p className="navlabel">{g.title}</p>}
              {g.items.map(({ href, label, icon: Icon, match, badge }) => (
                <a key={href} href={href} className={match(pathname) ? "active" : ""}>
                  <Icon size={16} />
                  {label}
                  {badge === "review" && reviewCount > 0 && (
                    <em className="navbadge">{reviewCount}</em>
                  )}
                </a>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidefoot">
          <ThemeToggle />
          <div className="sidefoot-status">
            <span className={`dot ${ready?.ready ? "" : "off"}`} />
            {ready?.ready ? "引擎就绪" : "离线 / 检测中"}
            <small>
              {ready?.database || "—"} · {ready?.llm || "—"} ·{" "}
              {ready?.embedding_model || ready?.embedding_provider || "—"}
            </small>
          </div>
        </div>
      </aside>
      <div className="shellmain">{children}</div>
    </div>
  );
}
