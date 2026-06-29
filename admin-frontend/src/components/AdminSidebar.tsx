"use client";

import React, { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { logout, getUserRole } from "@/lib/api";

type NavItem = {
  label: string;
  href: string;
  icon: React.ReactNode;
  minRole?: string;   // 需要的最小角色
};

const ALL_NAV_ITEMS: NavItem[] = [
  {
    label: "Agent 管理",
    href: "/agents",
    minRole: "developer",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <line x1="9" y1="9" x2="15" y2="9" />
        <line x1="9" y1="13" x2="15" y2="13" />
        <line x1="9" y1="17" x2="12" y2="17" />
      </svg>
    ),
  },
  {
    label: "用量统计",
    href: "/usage",
    minRole: "developer",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <line x1="18" y1="20" x2="18" y2="10" />
        <line x1="12" y1="20" x2="12" y2="4" />
        <line x1="6" y1="20" x2="6" y2="14" />
      </svg>
    ),
  },
  {
    label: "用户管理",
    href: "/users",
    minRole: "admin",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
  {
    label: "角色管理",
    href: "/roles",
    minRole: "admin",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </svg>
    ),
  },
];

const ROLE_LABEL: Record<string, string> = {
  admin: "管理员",
  developer: "开发者",
  user: "普通用户",
};

export default function AdminSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [role, setRole] = useState<string>("user");
  const [userName, setUserName] = useState<string>("");

  useEffect(() => {
    setRole(getUserRole());
    setUserName(localStorage.getItem("admin_user_name") || "");
  }, []);

  // Filter nav items by role
  const navItems = ALL_NAV_ITEMS.filter((item) => {
    if (!item.minRole) return true;
    const hierarchy: Record<string, number> = { user: 0, developer: 1, admin: 2 };
    return (hierarchy[role] || 0) >= (hierarchy[item.minRole] || 0);
  });

  function isActive(href: string) {
    if (href === "/agents") return pathname?.startsWith("/agents");
    if (href === "/users") return pathname?.startsWith("/users");
    return pathname === href;
  }

  return (
    <aside className="admin-sidebar">
      <div className="admin-sidebar-brand">Agent Hub</div>

      <nav className="admin-sidebar-nav">
        {navItems.map((item) => (
          <a
            key={item.href}
            href={item.href}
            className={`admin-nav-item ${isActive(item.href) ? "active" : ""}`}
            onClick={(e) => {
              e.preventDefault();
              router.push(item.href);
            }}
          >
            <span className="admin-nav-icon">{item.icon}</span>
            {item.label}
          </a>
        ))}
      </nav>

      <div className="admin-sidebar-footer">
        {userName && (
          <div style={{ fontSize: 13, marginBottom: 6, opacity: 0.8 }}>
            {userName} · {ROLE_LABEL[role] || role}
          </div>
        )}
        <button onClick={() => logout()}>退出登录</button>
      </div>
    </aside>
  );
}
