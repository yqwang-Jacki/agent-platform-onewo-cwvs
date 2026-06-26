"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getProfile, logout, type UserProfile } from "@/lib/api";

export default function ProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProfile()
      .then(setProfile)
      .catch(() => router.push("/login"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading-screen">加载中...</div>;
  if (!profile) return <div className="loading-screen">未登录</div>;

  return (
    <div style={{ maxWidth: 560, margin: "0 auto", padding: "60px 16px" }}>
      <button
        onClick={() => router.push("/")}
        style={{
          background: "none", border: "none", color: "#666",
          fontSize: 13, cursor: "pointer", marginBottom: 32,
          display: "flex", alignItems: "center", gap: 6,
        }}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="15 18 9 12 15 6" />
        </svg>
        返回
      </button>

      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8, letterSpacing: "-0.5px" }}>
        个人中心
      </h1>
      <p style={{ color: "#999", fontSize: 13, marginBottom: 32 }}>
        管理你的账号信息
      </p>

      <div style={{ background: "#fff", border: "1px solid #e5e5e5", borderRadius: 10, padding: "4px 20px" }}>
        <div className="profile-field">
          <span className="label">姓名</span>
          <span className="value">{profile.name}</span>
        </div>
        <div className="profile-field">
          <span className="label">部门</span>
          <span className="value">{profile.department}</span>
        </div>
        <div className="profile-field">
          <span className="label">SAP 工号</span>
          <span className="value">{profile.sap_id}</span>
        </div>
        <div className="profile-field">
          <span className="label">手机号</span>
          <span className="value">{profile.phone}</span>
        </div>
        <div className="profile-field">
          <span className="label">邮箱</span>
          <span className="value">{profile.email}</span>
        </div>
      </div>

      <div style={{ marginTop: 32, textAlign: "center" }}>
        <button
          onClick={() => logout()}
          style={{
            color: "#ef4444", background: "none", border: "1px solid #fecaca",
            padding: "10px 32px", borderRadius: 8, fontSize: 14, cursor: "pointer",
          }}
        >
          退出登录
        </button>
      </div>
    </div>
  );
}
