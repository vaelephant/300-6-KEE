import path from "node:path";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  plugins: [react(), tailwindcss()],
  server: {
    // 多会话并行开发：PORT 由启动器分配（5173 被占时换口），未设时保持默认
    port: process.env.PORT ? Number(process.env.PORT) : 5173,
    proxy: {
      // 后端端口可用 UTOPIA_DEV_API 覆盖（默认 1516，与 .env 的 UTOPIA_BIND_ADDR 一致）
      // 强制 x-forwarded-proto=http：若浏览器/环境带了 https，后端会给 cookie 打
      // Secure，HTTP 页面下 cookie 被静默丢弃，表现为登录成功又回到登录页且无报错。
      "/api": {
        target: process.env.UTOPIA_DEV_API ?? "http://127.0.0.1:1516",
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on("proxyReq", (proxyReq) => {
            proxyReq.setHeader("x-forwarded-proto", "http");
          });
        },
      },
    },
  },
  test: {
    // 纯逻辑单测，不起 DOM：queryDefaults 那张表、事件失效的合并
    include: ["src/**/*.test.ts"],
    environment: "node",
  },
});
