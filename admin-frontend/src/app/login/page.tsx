"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { loginPublisher, isLoggedIn } from "@/lib/api";

export default function AdminLoginPage() {
  const router = useRouter();
  const [account, setAccount] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isLoggedIn()) router.replace("/agents");
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    if (!account || !password) return setErr("请填写手机号和密码");
    setLoading(true);
    try {
      await loginPublisher(account, password);
      router.replace("/agents");
    } catch (e: unknown) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="admin-login-page">
      <div className="admin-login-card">
        <h1>Agent Hub</h1>
        <p className="subtitle">管理后台 · 发布者登录</p>

        <form onSubmit={handleSubmit}>
          <div className="admin-login-group">
            <label>手机号</label>
            <input
              className="admin-login-input"
              type="text"
              value={account}
              onChange={(e) => setAccount(e.target.value)}
              placeholder="13900000000"
            />
          </div>
          <div className="admin-login-group">
            <label>密码</label>
            <input
              className="admin-login-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="输入密码"
            />
          </div>
          {err && <p style={{ color: "#ef4444", fontSize: 13, marginBottom: 12 }}>{err}</p>}
          <button className="admin-login-btn" type="submit" disabled={loading}>
            {loading ? "登录中..." : "登录"}
          </button>
        </form>
      </div>
    </div>
  );
}
