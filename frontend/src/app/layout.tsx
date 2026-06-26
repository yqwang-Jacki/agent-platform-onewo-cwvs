import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agent Hub",
  description: "AI Agent 对话平台",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
