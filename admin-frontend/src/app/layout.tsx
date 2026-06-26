"use client";

import { usePathname } from "next/navigation";
import AdminSidebar from "@/components/AdminSidebar";
import "./globals.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLoginPage = pathname === "/login";

  return (
    <html lang="zh-CN">
      <body>
        {isLoginPage ? (
          children
        ) : (
          <div style={{ display: "flex", width: "100%", height: "100vh" }}>
            <AdminSidebar />
            <main className="admin-main">{children}</main>
          </div>
        )}
      </body>
    </html>
  );
}
