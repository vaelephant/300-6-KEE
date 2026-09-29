"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Switch } from "@/components/ui/switch";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  const dark = mounted && resolvedTheme === "dark";

  return (
    <label className="theme-toggle">
      <Sun size={13} aria-hidden />
      <Switch
        checked={dark}
        onCheckedChange={(on) => setTheme(on ? "dark" : "light")}
        disabled={!mounted}
        aria-label="切换深色模式"
      />
      <Moon size={13} aria-hidden />
      <span>{dark ? "深色" : "浅色"}</span>
    </label>
  );
}
