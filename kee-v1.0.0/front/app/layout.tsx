import type { Metadata } from "next";
import "./globals.css";
import { Shell } from "@/components/Shell";
import { ThemeProvider } from "@/components/theme-provider";

const siteName = "KEE科室版";
const title = "KEE科室版 · Evolution Engine";
const description = "可演化、可信任、可被 Agent 调用的知识引擎";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000"),
  title,
  description,
  applicationName: siteName,
  openGraph: {
    type: "website",
    locale: "zh_CN",
    siteName,
    title,
    description,
  },
  twitter: {
    card: "summary_large_image",
    title,
    description,
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <Shell>{children}</Shell>
        </ThemeProvider>
      </body>
    </html>
  );
}
